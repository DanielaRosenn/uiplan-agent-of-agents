# UiPlan template kit (`docs/uiplan/kit`)

Normalized copies of the UiPlan document templates used with the **generate-docs → review → scaffold** flow.

## How to use

1. Run **`uv run python -m tools.uiplan generate-docs <slug>`** (or your project’s equivalent) to materialize `spec.md`, `plan.md`, and `tasks.md` from these templates.
2. **Human approval** — review the generated docs for accuracy, scope, and constitution checks before any implementation work.
3. Run **`uv run python -m tools.uiplan scaffold-code <slug> --max-loops N`** to drive implementation against the approved plan.

## Framework reference

- Human overview: [../README.md](../README.md)
- Step-by-step: [../HOW_TO_USE.md](../HOW_TO_USE.md)
- Tooling matrix: [UiPlan framework](../../plans/2026-04-21-uiplan-framework.md)

## Files

| File | Role |
| --- | --- |
| `_spec-template.md` | Feature specification skeleton |
| `_plan-template.md` | Implementation plan skeleton |
| `_tasks-template.md` | Executable task list skeleton |
| `_diagram-patterns.md` | Ready-to-copy Pro Standard Mermaid blocks |

Templates include **Pro Standard** Mermaid (`classDef`; `linkStyle` on flowcharts) per [`.cursor/skills/mermaid-diagram-builder/SKILL.md`](../../../.cursor/skills/mermaid-diagram-builder/SKILL.md).
