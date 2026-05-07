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

1. The CLI starts the FastAPI backend (`services/uiplan-studio-api`) and the
   Vite dev server (`apps/uiplan-studio`).
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
