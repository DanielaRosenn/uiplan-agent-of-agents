---
name: uiplan-plan
description: Create or update plan.md for an existing UiPlan draft. Generates a fully-built Solution-Engineer-grade plan in one shot, asking up to 3 targeted questions only when information cannot be inferred.
disable-model-invocation: true
---

# UiPlan Plan

Use `.cursor/skills/uiplan/SKILL.md` as the canonical contract.

Treat the user's text after `/uiplan-plan` as a UiPlan reference. It may be:

- the metadata slug from `.meta.yaml` (for example `zip-email-automation`);
- the dated draft folder name (for example `2026-04-27-zip-email-automation`);
- the full path to the draft folder.

Run `uipath_plan_plan_new` directly with that reference. Do **not** hand-copy
`templates/uiplan/_plan-template.md`, do **not** paste the generated plan into
chat, and do **not** ask the user to copy files or commands. The MCP tool writes
`plan.md`.

If an MCP status file says the server is errored, treat it as advisory only.
Call the tool once; only surface the problem if the tool call itself returns an
error.

## Audience

`plan.md` is the **Developer <-> Solution Engineer** contract. Use it to
elaborate architecture, project topology, paradigm decisions, integrations,
bindings, dependencies, and capability routing. Do **not** expand into per-line
activity wiring (that's `tasks.md`) and do **not** restate business outcomes
(that's `spec.md`).

## Generation contract

Generate the plan in one shot with all sections filled. Only ask the user
**up to 3 targeted questions** when information is genuinely missing AND
cannot be resolved through the AskAI / Library ladder below.

Successful output is terse: report only that `plan.md` was created, the resolved
Plan id, and the path. Do not add caveats, manual follow-up options, or
"copy/paste next" instructions after a successful generation. Unresolved facts
belong in `## Open Grounding Questions` inside `plan.md`, not in chat.

### AskAI / Library ladder (run before asking the user)

1. `uipath_library_search` / `uipath_library_lookup` for project-context,
   paradigm patterns, package coverage.
2. `uipath_doc_get_activity` / `uipath_doc_list_packages` for activity
   semantics.
3. `query_uipath_docs` (AskAI) for runtime / CLI fallback.
4. Specialist skill (`uipath-rpa`, `uipath-agents`, `uipath-custom-hitl`,
   `uipath-platform`, `uipath-diagnostics`, `uipath-test`, `uipath-coded-apps`,
   `uipath-data-fabric`, `uipath-maestro-flow`).
5. `[agent:uipath-project-discovery-agent]` for project-local context.
6. Only then ask the user, naming what was already attempted.

Record any remaining gaps under `## Open Grounding Questions` in `plan.md` as
`[NEEDS CLARIFICATION: <topic>]`.

## Required sections (must be present after generation)

- `## Audience and Scope` (Dev <-> SE)
- `## Stack Policy` (Modern Studio + activity-first)
- `## Coded Surface Justification` (empty unless any `.cs` workflow is in scope)
- `## Project Inventory` (one row per project)
- `## Workflow Catalog` (one row per workflow file; cross-link
  `templates/uiplan/_workflow-catalog.md`)
- `## Activity Inventory` (only entries resolved via `uipath_doc_get_activity`
  or library lookup)
- `## Code Module Inventory` (agents / apps)
- `## Bindings and Environment` (queues, assets, connections, folders)
- `## Dependency Matrix`
- `## CLI Command Matrix`
- `## Skill and Subagent Routing` (project x phase -> capability)
- `## Capability Routing Map` (Mermaid)
- `## AskAI / Library Escalation Ladder`
- `## Open Grounding Questions`
- `## Planner Route & Specialist Handoff`
- `## Story visual map`, `## Capability and ownership map`,
  `## Data and queue contract map`
- `## Project Structure`, `### Source Code (repository root)`,
  `### Paradigm build loop`
- `## Development execution contract`
- `## Build and verify gates` (Mermaid)
- `## Deployment policy`

## Stack Policy enforcement

- Default: latest UiPath Studio + Studio Web; **no Legacy / Windows-Legacy /
  VB.Net / Classic**; do not route through `uipath-rpa-legacy`.
- Prefer **UiPath activities** (resolved via `uipath_doc_get_activity`) over
  coded `.cs` workflows.
- Coded `.cs` workflow surfaces are allowed only when `## Coded Surface
  Justification` has a row naming the activity-doc / library-search lookup
  that proved activities cannot cover the case. Prompt the user before
  introducing a coded surface and record their justification.

## Custom HITL routing

When the plan needs a human approval / data-enrichment / write-back gate,
default to `[skill:uipath-custom-hitl]` (Action Center External Tasks +
HITL_Application Adaptive Cards / Slack). Do **not** plan around UiPath Flow
as the HITL canvas.

## Do / Don't

**Do**:

- Name every project, workflow file, workflow type, queue, asset, dependency,
  CLI verb, skill, subagent, agent, and MCP tool.
- Embed Pro Standard Mermaid diagrams (story visual, capability map, data /
  queue map, build loop) using `classDef` / `linkStyle` from
  `templates/uiplan/_diagram-patterns.md`.
- Cross-link `templates/uiplan/_workflow-catalog.md` for chosen patterns.

**Don't**:

- Expand into per-activity property tables or CLI flag recipes (that's
  `tasks.md`).
- Restate business stories from `spec.md`.
- Invent activities, packages, or CLI verbs without library / activity-doc
  lookup citations.
- Plan a coded `.cs` workflow without filling `## Coded Surface Justification`.

## Returning clarifying questions

When the generator detects ambiguity that cannot be resolved by the ladder,
emit at most **3** clarifying questions in the response payload's
`clarifying_questions` field. After the user replies, re-run with the answers
threaded into the bundle.
