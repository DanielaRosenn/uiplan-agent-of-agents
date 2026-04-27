# How to use UiPlan

## Canonical paths

- **Kit:** `templates/uiplan/` at repo root (MCP and `generate-docs` resolve here).
- **Runtime:** `tools/uiplan/` for local CLI entry points and scaffold/adaptor support.
- **Cursor skills:** `.cursor/skills/uiplan*/SKILL.md` for slash command behavior.
- **MCP tools:** `framework/mcp_server/tools/plan_uiplan*.py`.
- **Pytest (UiPlan):** `framework/tests/uiplan/`. Example: `uv run pytest framework/tests/uiplan/ -q`.
- **Task authoring:** [TASK_AUTHORING.md](TASK_AUTHORING.md) for workflow design,
  capability routing, examples, and the implementation loop.

## Decision table

| I want to… | Use |
| --- | --- |
| Chat-native flow with grounding and review | MCP `uipath_plan_ground`, `uipath_plan_spec_new`, `uipath_plan_plan_new`, `uipath_plan_tasks_new`, `uipath_plan_review` (or `uipath_plan_uiplan_new` for the bundled path). |
| A file-first bundle from templates with local validation | From repo root: `uv run python -m tools.uiplan generate-docs <slug>` (optional `--out`, `--kit`, `--strict`, `--paradigm`). |
| Slash commands in Cursor | Separate skill commands: `/uiplan-full`, `/uiplan-ground`, `/uiplan-spec`, `/uiplan-plan`, `/uiplan-tasks`, `/uiplan-review`, and `/uiplan-implement`. |
| CLI parity with chat | `uipath-claude plan uiplan …` (see [USER_GUIDE.md](../USER_GUIDE.md)). |

## Paths (folder convention)

- **Drafts (default):** `.cursor/plans/<slug>/` with `spec.md`, `plan.md`, `tasks.md`, `.meta.yaml` (`plan_kind: uiplan`). Draft trees are gitignored like other `.cursor/plans` work.
- **Published:** `docs/plans/<slug>/` after `uipath_plan_accept` + `uipath_plan_publish`.
- **Templates (kit):** [`templates/uiplan/`](../../templates/uiplan/) at the repo root.

## Slug and lifecycle rules

UiPlan has two names that are easy to confuse:

- **Folder slug**: the draft folder under `.cursor/plans/`, often date-prefixed
  like `.cursor/plans/2026-04-27-my-feature/`.
- **Metadata slug**: `.meta.yaml` field `slug`, used by review/accept/publish
  tools as the stable logical plan id.

When in doubt, read `.meta.yaml` and pass the metadata slug to MCP/CLI review
commands. The status flow is:

1. **Draft**: generated or edited under `.cursor/plans/<folder>/`.
2. **Review**: run `uipath_plan_review` or `/uiplan-review <slug>` until no
   error-severity findings remain.
3. **Accept**: use `uipath_plan_accept` or
   `uipath-claude plan uiplan accept <slug>` after human approval.
4. **Implement**: use `/uiplan-implement <slug>`; it re-runs review, checks
   `.meta.yaml` status, and executes from `tasks.md`.
5. **Publish**: use `uipath_plan_publish` or
   `uipath-claude plan uiplan publish <slug>` when the accepted bundle should be
   copied to `docs/plans/<slug>/`.

Never publish by manually copying files to `docs/plans/`, and never treat a draft
as implementation-approved only because it exists on disk.

## Human approval gate

Do **not** treat `generate-docs` output as approved scope by default.

1. Read the three files for real grounding text (replace `_…_` placeholders).
2. Confirm `spec.md` includes **Development Handoff**, `plan.md` includes
   **Development execution contract**, and `tasks.md` includes
   **Build, Verify, and Handoff**.
3. Run `uipath_plan_review` until `"ok": true` when using MCP.
4. Only then accept the bundle and start implementation with
   `/uiplan-implement <slug>`. Use `scaffold-code` only when you specifically
   need the local runtime/adaptor checks described in [SCAFFOLD_CODE.md](SCAFFOLD_CODE.md).

## Numbered quickstarts

### A) Cursor skill / slash

1. Open the repo in Cursor with skills installed ([INSTALL.md](../INSTALL.md)).
2. Use `/uiplan-full <title>` for the bundled path, or staged commands:
   `/uiplan-ground`, `/uiplan-spec`, `/uiplan-plan`, `/uiplan-tasks`, and
   `/uiplan-review`.
3. After review passes and you approve the build, use `/uiplan-implement <slug>`
   to execute from `tasks.md` with the relevant skills, MCP tools, subagents,
   library/AskAI lookup, CLI commands, tests, and build gates.
4. The command wrappers point back to `.cursor/skills/uiplan/SKILL.md`, map to
   the same `uipath_plan_*` MCP tools as the CLI/chat surface, and keep
   implementation behind review plus human approval.

5. Generated docs are visual-first, but detail increases by stage. Expect:
   - `spec.md`: simple business-scope and story-journey diagrams only. It should
     stay readable beside the formal PDD / SDD and should not copy their prose.
   - `plan.md`: story visual map, capability/ownership map, data-contract map,
     architecture, and build-loop diagrams for Solution Engineer planning.
   - `tasks.md`: execution map, story workflow/task map(s), and build/diagnostics
     loop diagram for LLM/executor implementation.

**Implementation validation:** `/uiplan-implement` must prove behavior with
**runtime evidence**, not only static checks. Expect a **validation evidence ledger**
in the session summary: commands run (or MCP tools used), exit codes, changed
paths, and observed pass/fail. For this repo (Python / LangGraph), that should
normally include `uv run pytest …` on affected tests or an equivalent run named
in `tasks.md`. If proof needs the Cursor UI (slash picker, reload), the agent
should ask for **human confirmation** and record it in the ledger instead of
claiming end-to-end proof without it.

### B) Local Typer CLI (`tools/uiplan`)

```bash
cd <repo-root>
uv sync
uv run python -m tools.uiplan generate-docs 2026-04-23-my-feature
# optional: --out path/to/folder --kit path/to/kit --no-strict --paradigm coded-agent
# optional runtime/adaptor support, not a replacement for /uiplan-implement:
uv run python -m tools.uiplan scaffold-code 2026-04-23-my-feature --max-loops 5
```

### C) MCP (`uipath_plan_*`)

Use when the agent session already has MCP enabled ([MCP_TOOLS.md](../MCP_TOOLS.md)). Prefer `uipath_plan_ground` first, then the `spec` / `plan` / `tasks` stages, then `uipath_plan_review`.

The grounding pack is workspace-aware: it includes the `uipath-planner` route,
the `uipath-project-discovery-agent` handoff, matched specialist skill excerpts,
local library search, and the library → AskAI lookup path when available.
`uipath_plan_plan_new` writes those inputs into `plan.md` so later task
generation, implementation, and review can cite them.

`uipath_plan_tasks_new` is the build handoff. Its final phase should drive the
accepted implementation loop. In Cursor, `/uiplan-implement <slug>` reads the
planner/specialist handoff, reviews first, asks before building, executes tasks
in order, runs restore -> analyze -> test -> pack, and stops before any
approval-required deploy.

`/uiplan-tasks` assumes discovery is done. If project discovery, template
decisions, workflow surfaces, and capability routing are missing in `plan.md`,
stop and rerun `/uiplan-plan` before task generation.

`uipath_plan_review` now includes feasibility checks for declared paradigm,
code-structure descriptors, CLI-family consistency, artifact-rich tasks, and
deploy gates.

## Document personas (BA / Dev / Solution Engineer)

Each UiPlan document targets a different audience. Keep content in the right
document; review flags persona leakage.

| Document | Audience | Owns | Avoids |
| --- | --- | --- | --- |
| `spec.md` | BA <-> Developer | Lightweight business intent, user stories, acceptance criteria, NFRs, SME items, PDD / SDD traceability | `.xaml` / `.cs` / `.py` filenames, CLI verbs, `[skill:...]`, activity wiring, copied PDD / SDD prose |
| `plan.md` | Developer <-> Solution Engineer | Architecture, paradigm, project topology, workflow catalog, activity inventory, bindings, capability routing, stack policy, coded-surface justification | Per-activity micro-instructions, per-line CLI recipes |
| `tasks.md` | Solution Engineer -> Developer / Executor | Artifact paths, exact CLI commands, evidence paths, `[skill:]`/`[agent:]`/`[subagent:]`/`[library:]`/`[askai:]` tags, acceptance gates, build/verify/diagnose/fix loop | Re-opening architectural decisions |

When any persona hits a knowledge gap, run the **AskAI / Library ladder**
before asking the user: `uipath_library_search` / `uipath_library_lookup` ->
`uipath_doc_get_activity` -> `query_uipath_docs` -> specialist skill or
`[agent:uipath-project-discovery-agent]` -> user.

The plan/tasks generator routes the HITL surface to the org Custom HITL skill
(`[skill:uipath-custom-hitl]` + `HITL_Application` Adaptive Cards/Slack +
Action Center External Tasks). Do **not** use UiPath Flow as the HITL canvas.
The stack policy is **Modern Studio + activity-first** (latest Studio, C#,
Windows, .NET 8); coded `.cs` workflows are allowed only when justified in
`plan.md` -> `## Coded Surface Justification`.

## Capability and persona routing

Before accepting a non-trivial bundle, inventory the active capabilities and show
how `plan.md` / `tasks.md` will use them:

- **Planning/design skills**: `uiplan-*`, `uipath-planner`,
  `uipath-solution-design`, `writing-uipath-plans`, `mermaid-diagram-builder`.
- **Product/build skills**: `uipath-rpa`, `uipath-rpa-legacy`,
  `uipath-agents`, `uipath-platform`, `uipath-coded-apps`,
  `uipath-maestro-flow`, `uipath-case-management`, `uipath-data-fabric`,
  `uipath-human-in-the-loop`, `uipath-gov-aops-policy`, `uipath-test`,
  `uipath-diagnostics`, `uipath-interact`.
- **Submodule agents**: `skills/agents/uipath-project-discovery-agent.md` when
  project context is missing or stale.
- **Diagnostic agent personas**: triage, scope-checker, hypothesis-generator,
  hypothesis-tester, and presenter for failed analyzer/test/tooling loops.
- **MCP/library/docs**: `uipath_library_search`, `uipath_library_lookup`,
  `uipath_doc_get_activity`, `uipath_doc_list_packages`, and
  `query_uipath_docs` / `[askai:...]` only when local/library coverage is not
  enough.
- **CLI/tooling**: `uipcli`, `uipath`, `uip`, and live `--help` before uncertain
  flags.
- **Focused subagents**: discovery, implementation, shell/test execution,
  browser/UI verification, documentation, and code review when work can be split
  safely.

Run non-trivial plans through BA / SA / Dev / QA lenses before acceptance:

- **BA**: process, actors, inputs/outputs, acceptance criteria, SME gaps.
- **SA**: topology, project split, workflow shape, queues/assets/connections,
  deployment gates.
- **Dev**: artifacts, activities/SDK calls, package dependencies, implementation
  order, local build loop.
- **QA/Test**: fixtures, analyze/test commands, runtime evidence, failure-path
  validation, smoke criteria.

Any unresolved design choice should name its owning persona, skill, or blocker
so `/uiplan-implement` does not make architecture decisions while coding.

## Task quality gate

Use [TASK_AUTHORING.md](TASK_AUTHORING.md) when drafting or reviewing `tasks.md`.
At minimum, each implementation task must name:

- project or package;
- workflow / sequence / graph node / CLI step;
- artifact path;
- UiPath construct;
- skill/library/docs/AskAI/CLI/subagent grounding;
- exact verification command;
- runtime evidence.

The implementation loop is always: develop -> analyze/test -> parse output ->
compare against plan/tasks -> fix safely -> rerun -> record evidence.
