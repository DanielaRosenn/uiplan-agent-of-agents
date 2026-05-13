# UiPlan Studio Explorer

The Explorer is a project-wide map of a UiPath solution: UI ↔ API ↔ Agent ↔
RPA ↔ Maestro ↔ App ↔ Orchestrator ↔ Test, with drill-down into individual
workflows, business overview for BAs, and a knowledge tab that surfaces
matching skills + library citations per node.

It runs locally against the project you point it at.

## Quick start

From inside any UiPath project (RPA, coded agent, Maestro, solution, or
mixed):

```
uipath-claude explore --init       # writes .uiplan/explorer.yaml
# edit .uiplan/explorer.yaml — fill in name, owner, triggers, actors, KPIs
uipath-claude explore --check      # see what the indexer found
uipath-claude explore              # boot the studio + open browser
```

The studio opens at `http://127.0.0.1:5173/?worktree=<your-project-path>`,
indexes the project, and renders:

- **Project overview** (BA shell): name, owner, triggers, actors, KPIs,
  PDD link — straight from `.uiplan/explorer.yaml`.
- **Layered canvas**: nodes grouped into UI / API / Agent / RPA / Maestro /
  App / Orchestrator / Test / External / Skills columns. Layers with no
  nodes are hidden automatically.
- **Skills layer**: project-wide skill nodes explain which UiPath authoring
  skills apply to the project. Each skill links to its top 3 covered nodes so
  the canvas stays readable.
- **Inspector**: per-node Overview, Code, Knowledge (live skill+library
  search), and Links tabs.

## How it works

1. The CLI starts the FastAPI backend (`studio/api`) and the Vite dev server
   (`studio/web`).
2. The frontend asks the backend for `/explorer/graph?worktree=<path>`.
3. The backend reads `.uiplan/explorer.yaml` (project overview + indexer
   hints), runs the cross-layer indexer, merges per-node overrides from
   `.uiplan/annotations.yaml` if present, aggregates matching skills, and
   returns the graph.
4. Knowledge requests (`/explorer/knowledge`) bridge to
   `uipath_claude.skills.registry` and the library catalog so the studio
   shows the same skills + sections an MCP client would surface.

## Skills layer

The Skills layer is an aggregated context layer. It answers:

- What skills explain this project?
- Which nodes does each skill primarily cover?
- What does the skill actually do?
- When should the skill be used?

The backend loads skills through `uipath_claude.skills.registry`, scores each
skill against indexed node context (`label`, `kind`, `layer`, descriptions,
paths, and snippets), then adds:

- one synthetic `skill:*` node per matching skill
- up to three `covers` edges from that skill to its highest-scoring nodes
- coverage metadata for the LeftRail summary and Inspector

In the UI:

- Use **Skills → show coverage** to toggle `covers` edges on/off.
- Click a skill in the LeftRail to jump to the skill node.
- The skill Inspector shows Overview, full `SKILL.md` body, and covered nodes.

## `.uiplan/explorer.yaml`

The single source of truth for project-level metadata and indexer hints.
The schema is permissive — missing keys yield empty defaults.

```yaml
project:
  name: "Renewal Commitment"
  type: mixed                     # rpa | coded-agent | langgraph | maestro | solution | mixed
  owner: "Sales Operations"
  pdd: docs/PDD-RENEWAL-01.md

overview:
  summary: |
    What the process does, two-three sentences. BA-facing.
  stakeholders: ["Sales Ops", "Finance", "Legal"]
  triggers:
    - { kind: http, description: "POST /commitments from the Checkout UI" }
  actors:
    - { name: "Sales Rep",        role: submitter }
    - { name: "Approver Manager", role: human-in-the-loop }
  kpis:
    - { label: volume,   value: "120 / day" }
    - { label: p95 SLA,  value: "8 minutes" }

indexing:
  scan:
    ui:    ["src/**/*.tsx", "src/**/*.ts"]
    api:   ["backend/**/*.py"]
    agent: ["agent/**/*.py"]
    rpa:   ["**/*.xaml"]
    test:  ["tests/**/*.py"]
  exclude: [".venv/**", "node_modules/**"]
```

If `indexing.scan` is omitted, the indexer applies sensible defaults based
on `project.type`. See `app/explorer_config.py::DEFAULT_SCAN_GLOBS` for the
full table.

## `views` — AS-IS / TO-BE canvases

The `views` block defines two stakeholder-facing process visualizations that complement the technical project graph:

- **AS-IS**: How work happens today, manually — swim-lanes showing actors, handoffs, channels, SLA, and pain points.
- **TO-BE**: The automated solution architecture — triggers, workflows, integrations, Orchestrator resources, HITL surfaces, runtimes, and evidence sinks.

Both views are optional and driven by declarative configuration. When absent, the canvas shows an empty state with authoring hints.

```yaml
views:
  docs_root: docs/                      # base folder for relative drill-down links

  as_is:
    summary_from: docs/process/as-is.md            # markdown narrative (optional)
    diagram_from: spec.md#business-process-flow    # mermaid block anchor
    actors_from: explorer.actors                   # reuse overview.actors
    swimlanes:                                     # explicit actor ordering
      - "Sales Rep"
      - "Approval Manager"
      - "Finance"
    handoffs:                                      # explicit fallback (no mermaid)
      - { from: "Sales Rep", to: "Approval Manager", channel: email, artifact: "PDF quote", sla: "2d", pain: "manual chase" }
      - { from: "Approval Manager", to: "Finance", channel: meeting, artifact: "decision", sla: "1d", pain: "rework loop" }
    pain_points: docs/process/pain-points.md       # optional callouts file

  to_be:
    architecture_from:                             # mermaid anchors, priority order
      - spec.md#solution-architecture
      - plan.md#solution-architecture
    runtime_sequence_from: plan.md#runtime-sequence
    workflow_catalog_from: plan.md#workflow-catalog
    integrations_from: indexed                     # use live XAML/.flow scan
    drill_docs:                                    # per-node markdown deep-dives
      "Main-Queue.xaml": docs/workflows/main-queue.md
      "ApprovalFlow_SalesRep.xaml": docs/workflows/approval-sales-rep.md
      Salesforce: docs/integrations/salesforce.md
      Queue: docs/orchestrator/queue.md
```

### Resolution rules

1. If `diagram_from` or `architecture_from` points at a real Mermaid block (`file.md#anchor`), parse it.
2. Else fall back to structured YAML (`handoffs`, `swimlanes`, `drill_docs`).
3. Else (TO-BE only) fall back to inferred defaults from the indexed graph — integrations from live XAML scan, workflows from the technical canvas.
4. AS-IS without authoring shows a "needs spec" empty state with one-click editor links.

### Channel types (AS-IS handoffs)

- `email` — email-based handoff
- `phone` — phone/voice handoff
- `excel` — Excel/CSV file exchange
- `paper` — physical document
- `meeting` — synchronous meeting

### TO-BE buckets

The TO-BE canvas groups nodes into vertical swim-lanes:

- **Triggers** — entry points (queue, HTTP, scheduled)
- **Intake/Orchestration** — dispatcher workflows, state stores
- **Processing** — worker workflows, agent hosts
- **Integrations** — external connectors (Salesforce, Slack, HTTP)
- **HITL** — human review surfaces (Action Center, Maestro, custom)
- **Evidence** — audit sinks (logs, queue audits, storage buckets)

### Drill-down docs

Each node in TO-BE can link to a markdown deep-dive via `drill_docs`. The panel renders:

1. The linked markdown file (if present).
2. Else, workflow internal-step Mermaid from `plan.md`/`tasks.md` for that workflow.
3. Else, integration details from indexed XAML.
4. Else, "no doc — link to author one" with a one-click editor link.

### Drill levels and compare flow

The UiPlan view now exposes progressive drill levels aligned to the redesign contract:

- `L0 System` — full AS-IS/TO-BE map.
- `L1 Lane` — actor lane (AS-IS) or architecture bucket (TO-BE).
- `L2 Work item` — selected handoff/stage.
- `L3 Raw metadata` — collapsed by default, expanded on demand from the drill panel.

The `COMPARE` tab provides an AS-IS vs TO-BE delta board for player-level decomposition and
preserves lane/bucket selection context when returning to AS-IS or TO-BE tabs.

### Template adoption

When using the UiPlan templates (`templates/uiplan/`), the required Mermaid anchors are pre-seeded:

- `spec.md#business-process-flow` (AS-IS)
- `spec.md#solution-architecture` (TO-BE)
- `plan.md#runtime-sequence` (TO-BE)
- `plan.md#workflow-catalog` (TO-BE)

See [`templates/uiplan/_diagram-patterns.md`](../../templates/uiplan/_diagram-patterns.md) for the canonical patterns.

## `.uiplan/annotations.yaml` (optional)

Per-node overrides merged onto the indexer's output. Keys are node ids
(visible via `uipath-claude explore --check`); values are partial node
payloads:

```yaml
rpa:Main.xaml:
  business_status: live
  business_meta:
    owner: Sales Operations
    sla: "p95 8 min"
    risk: medium
  pdd_anchor: { doc_id: "PDD-RENEWAL-01", section: "§3 Process Steps" }
```

Annotations let a BA mark up the graph (status, KPIs per node, PDD
anchors, HITL roles) without editing source.

## Wiring into a new project

The `uipath-claude` scaffolds (`dispatcher`, `performer`, `long-running`)
already drop a `.uiplan/explorer.yaml` with paradigm-appropriate defaults
into each new project. For an existing project that doesn't have one yet,
run `uipath-claude explore --init` from the project root.

For a step-by-step adoption guide (config, annotations, CI hooks,
troubleshooting) see [EXPLORER_NEW_PROJECT.md](EXPLORER_NEW_PROJECT.md).

## Endpoints (for tooling)

| Method | Path                              | Purpose |
|--------|-----------------------------------|---------|
| GET    | `/explorer/worktrees`             | List indexed worktrees |
| GET    | `/explorer/graph?worktree=<id-or-path>` | Project graph |
| GET    | `/explorer/knowledge?worktree=&node=&q=` | Live skills + library citations |
| GET    | `/explorer/library/section?book=&chapter=&section=` | Full library section body |
| POST   | `/explorer/init`                  | Drop `.uiplan/explorer.yaml` into a project |

## Scope and limits

- The indexer is heuristic. It nails Python imports, TS relative imports,
  and XAML `<InvokeWorkflowFile>` invocations. It does not (yet) parse
  Maestro `.flow` graphs, LangGraph compile output, or Orchestrator
  REST resources — those layers show file-level nodes only.
- Annotations are file-only today. Editing annotations from inside the
  studio is on the roadmap.
- Local-only: the API binds 127.0.0.1, no auth. Don't expose it.
