# Using UiPlan Studio Explorer in a New Project

A practical, end-to-end guide for adopting the UiPlan Studio Explorer in a
fresh UiPath project (RPA, coded agent, Maestro, Coded App, or Solution).

For the conceptual overview see [EXPLORER.md](EXPLORER.md). For day-to-day
project flows (`spec.md` -> `plan.md` -> `tasks.md`), see
[HOW_TO_USE.md](HOW_TO_USE.md).

---

## What you get

The Explorer is a 3-panel local web app that maps your project across the
UiPath layers (UI / API / Agent / RPA / Maestro / App / Orchestrator / Test
/ External / Skills) and lets a BA, an architect, and an implementer share
one view:

- **Left rail (`LeftRail.tsx`)** — layered outline, filters (layer, path,
  issues-only), search, skills coverage toggle.
- **Center canvas (`Canvas.tsx`)** — interactive layered graph with
  drill-down into child sub-graphs.
- **Right rail (`Inspector.tsx`)** — per-node Overview / Code / Knowledge
  (live skills + library citations) / Links tabs.
- **Top strip + Breadcrumb** — worktree picker, project metadata, drill
  trail.

Two services power it:

| Component | Path | Purpose |
|---|---|---|
| Vite + React UI | `studio/web/` | Renders the explorer |
| FastAPI service | `studio/api/` | Indexes the project, serves graph + knowledge |
| CLI launcher | `framework/uipath_claude/cli/explore.py` | `uipath-claude explore` boots both, opens browser |

---

## Prerequisites

The explorer ships with this template repo. To use it from a new project,
that project must be reachable from a checkout of `uipath-builder-agent`
(this repo). Two adoption modes:

1. **Same-repo project** — your project lives inside this repo (e.g. under
   `projects/<your-project>/`). This is the simplest path; the CLI is
   already on your PATH (`uv tool install` step in §0a of `CLAUDE.md`).
2. **External project** — your project lives in a separate repo. Either
   clone this repo alongside it, or install the CLI from this checkout
   (`uv pip install -e framework/`), then point the CLI at your project
   directory.

Either way you need:

- Python 3.11+, `uv`, Node 18+ (`npm` for the Vite app).
- This repo's `studio/api` Python deps installed (`uv sync` from `studio/api/`).
- This repo's `studio/web` JS deps installed (`npm install` from `studio/web/`).
- The `skills/` submodule initialized and the submodule guard passing
  (see `CLAUDE.md` §0a).

---

## Step 1 - Drop a config into the new project

From your project root run:

```bash
uipath-claude explore --init
```

This writes `.uiplan/explorer.yaml` with paradigm-appropriate defaults
inferred from your project type (presence of `langgraph.json`,
`agent_framework.json`, `solution.uipx`, `*.uiproj`, `project.json`,
`*.bpmn`, `caseplan.json`, etc.).

Open it and fill in the BA-facing fields - these are what makes the
Explorer useful to non-developers.

```yaml
project:
  name: "Renewal Commitment"          # human-readable process name
  type: mixed                          # rpa | coded-agent | langgraph | maestro | solution | mixed
  owner: "Sales Operations"
  pdd: docs/PDD-RENEWAL-01.md          # link back to the PDD

overview:
  summary: |
    Two-three sentences. What does this process do, in BA terms.
  stakeholders: ["Sales Ops", "Finance", "Legal"]
  triggers:
    - { kind: http,      description: "POST /commitments from Checkout UI" }
    - { kind: scheduled, description: "Nightly reconciliation 02:00 UTC" }
  actors:
    - { name: "Sales Rep",        role: submitter }
    - { name: "Approver Manager", role: human-in-the-loop }
  kpis:
    - { label: volume,  value: "120 / day" }
    - { label: p95 SLA, value: "8 minutes" }

indexing:
  scan:
    ui:    ["src/**/*.tsx", "src/**/*.ts"]
    api:   ["backend/**/*.py"]
    agent: ["agent/**/*.py"]
    rpa:   ["**/*.xaml"]
    maestro: ["**/*.flow", "**/*.bpmn"]
    test:  ["tests/**/*.py"]
  exclude:
    - ".venv/**"
    - "node_modules/**"
    - "dist/**"
```

If `indexing.scan` is omitted, defaults from
`studio/api/app/explorer_config.py::DEFAULT_SCAN_GLOBS`
are applied per `project.type`.

> **Tip.** Commit `.uiplan/explorer.yaml` to the project repo. It is
> source of truth for the Explorer view; reviewers and future agents
> read it.

---

## Step 2 - Sanity-check the index (no UI)

Before booting the studio, confirm the indexer can actually see the
project:

```bash
uipath-claude explore --check
```

Output is a one-screen summary:

- files scanned per layer,
- nodes and edges produced,
- warnings (parse failures, missing globs, file-size truncations).

If a layer reports zero files but you expected some, fix the
`indexing.scan` globs in `.uiplan/explorer.yaml` and rerun. Common gotchas:

- glob is relative to project root, not absolute,
- `**` requires `Path.glob` semantics (no `git ls-files`-style globs),
- excluded by `.uiplan/explorer.yaml::indexing.exclude` or hard caps
  (`max_files_per_layer`, `max_file_bytes`) - bump them deliberately.

---

## Step 3 - Boot the studio

```bash
uipath-claude explore                # opens browser at http://127.0.0.1:5173/?worktree=<your-project-path>
uipath-claude explore --no-browser   # boot without opening a browser
uipath-claude explore --port 5180    # custom Vite port
uipath-claude explore --project-dir /abs/path/to/other/project
uipath-claude explore --no-auto-init # skip auto-creating .uiplan/explorer.yaml
```

Under the hood the CLI:

1. Picks a free port for the Vite dev server (default 5173, falls back).
2. Starts the FastAPI backend on `127.0.0.1:8000` (single instance per
   user; if 8000 is taken it shifts up).
3. Opens the browser with `?worktree=<absolute-path>` so the studio loads
   the right project on first paint.
4. Holds the foreground until Ctrl-C, then SIGTERMs both subprocesses.

> **Local-only.** Both servers bind `127.0.0.1` and have no auth. Don't
> expose them. Don't run the studio against an untrusted project (the
> indexer reads file contents - keep it inside repos you trust).

---

## Step 4 - Annotate (optional, BA-friendly)

Per-node business overlays live in `.uiplan/annotations.yaml`. Keys are
node ids (visible in the Explorer Inspector header, or via
`uipath-claude explore --check --json`); values are partial node payloads
that get merged onto the indexer output.

```yaml
rpa:Main.xaml:
  business_status: live              # drafted | approved | in-build | live | retired
  roles: [hitl]                      # hitl | approval | entrypoint | exit | trigger | actor
  business_meta:
    owner: "Sales Operations"
    sla:   "p95 8 min"
    risk:  medium                    # low | medium | high
    volume: "120 / day"
  pdd_anchor:
    doc_id: "PDD-RENEWAL-01"
    section: "§3 Process Steps"

agent:dispatcher.py:
  desc: "Classifies the incoming commitment and routes it."
  business_status: in-build
```

This file is the BA's "marker pen" on top of the developer's source. It
is non-destructive - delete it and the graph still renders.

---

## Step 5 - Wire it into your project's onboarding

For a new project you maintain, wire onboarding so the next person gets the
Explorer flow/code view on day one:

1. Add this block to the project's top-level `README.md`:

````markdown
## Visual project map

This project ships a UiPlan Studio Explorer config. To open the visual
map, from the project root run:

```bash
uipath-claude explore
```

Source of truth for the BA overview is `.uiplan/explorer.yaml`. Per-node
overlays live in `.uiplan/annotations.yaml`. See
[docs/uiplan/EXPLORER_NEW_PROJECT.md](https://github.com/<org>/uipath-builder-agent/blob/main/docs/uiplan/EXPLORER_NEW_PROJECT.md)
for details.
````

2. Add an optional setup hook/script in project bootstrap docs that runs
`uipath-claude explore` at least once. This ensures `.uiplan/explorer.yaml`
exists and the visual map is immediately available.

3. Keep planning artifacts in explorer-indexed locations:
   - `.cursor/plans/<slug>/spec.md`, `plan.md`, `tasks.md` for active bundles,
   - `docs/plans/` for published planning artifacts,
   - `docs/superpowers/plans/` for implementation-plan overlays when used.

If your project uses one of this repo's scaffolds (`dispatcher`,
`performer`, `long-running`), the `.uiplan/explorer.yaml` file is already
generated for you - no `--init` step needed.

---

## Endpoints (for tooling and CI)

The backend exposes a small REST surface that other tools (CI checks,
docs generators, MCP servers) can call directly. See
`studio/api/app/explorer.py` for the source-of-truth
schemas.

| Method | Path | Purpose |
|---|---|---|
| GET | `/explorer/worktrees` | List indexed worktrees (git worktrees + repo root) |
| GET | `/explorer/graph?worktree=<id-or-path>` | Full project graph |
| GET | `/explorer/knowledge?worktree=&node=&q=` | Live skills + library citations for a node |
| GET | `/explorer/library/section?book=&chapter=&section=` | Full body of one library section |
| GET | `/explorer/skill?id=<skill-id>` | Full `SKILL.md` body for one aggregated skill |
| POST | `/explorer/init` | Drop `.uiplan/explorer.yaml` into a project |

Schemas: `ExplorerGraphResponse`, `ExplorerKnowledgeResponse`,
`ExplorerLibrarySectionResponse`, `ExplorerSkillDetailResponse` in
`studio/api/app/explorer.py`.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Browser opens to a fixture (`demo` / `solution` / `empty`) | URL had no `?worktree=` and you clicked a fixture in the project source picker | Reload with `?worktree=<absolute-path>` or pick your project from the project source picker |
| Empty canvas, no errors | All `indexing.scan` globs matched zero files | Run `uipath-claude explore --check`, adjust globs |
| Knowledge tab shows no skills | Skills submodule not initialized or `skills-approved.sha` mismatch | `git submodule update --init skills && python -m uipath_claude.skills.submodule_guard` |
| Knowledge tab shows no library citations | `data/library/` not present (fresh clone of a leaner template) | Pull library data or accept that knowledge is skill-only |
| Indexer warning `<file>: <error>` | Per-file parse failure (heuristic AST/regex parser) | Open the file - usually a syntax error or oversize file. Bump `max_file_bytes` or add to `indexing.exclude`. |
| `EADDRINUSE` on port 5173 / 8000 | Another studio instance running | `uipath-claude explore --port 5180` or kill the other instance |
| Studio shows the right files but no edges | Edge inference is import/InvokeWorkflowFile-based; cross-language edges aren't inferred | Add explicit edges via `.uiplan/annotations.yaml` (planned) or accept the limitation |

---

## Limits (be honest with stakeholders)

- The indexer is **heuristic**. It nails Python imports, TypeScript
  relative imports, and `<InvokeWorkflowFile>` invocations. Maestro
  `.flow` / `.bpmn` graphs, LangGraph compile output, and Orchestrator
  REST resources currently render as **file-level nodes only**.
- Annotations are **file-only** today. Editing them from inside the
  studio is on the roadmap.
- The studio is **local-only**. Both servers bind `127.0.0.1`, no auth.
  Don't expose; don't run against untrusted projects.
- Generation / apply paths from the older "graph workspace v2" iteration
  (`/graph/*` endpoints) still exist in the backend but are not consumed
  by the current UI. Treat them as deprecated; do not build on them.
  See `docs/uiplan/_internal/EXPLORER_REVIEW_2026-05-07.md` for the full cleanup
  list.

---

## Where to go next

- **Configure deeper** - tune `indexing.scan`, exclude globs, and
  per-layer hints in `.uiplan/explorer.yaml`. Schema: see
  `studio/api/app/explorer_config.py`.
- **Annotate for BAs** - fill `.uiplan/annotations.yaml` with status,
  KPIs, HITL roles, PDD anchors per node.
- **Plug into UiPlan** - the same `.cursor/plans/<slug>/` bundles used
  by `/uiplan-*` slash commands surface in the Explorer's Inspector
  Knowledge tab when relevant.
- **Extend the layers** - to add a layer (e.g. a custom integration
  type), edit `SUPPORTED_LAYERS` in
  `studio/api/app/explorer_indexer.py` and add the corresponding column to
  `studio/web/src/theme.ts::LAYERS`.
