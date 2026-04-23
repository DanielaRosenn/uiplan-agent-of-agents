# UiPlan template kit (`_uiplan-kit`)

Normalized copies of the UiPlan document templates used with the **generate-docs → review → scaffold** flow.

## How to use

1. Run **`uiplan generate-docs`** (or your project’s equivalent) to materialize `spec.md`, `plan.md`, and `tasks.md` from grounded inputs, starting from these templates as needed.
2. **Human approval** — review the generated docs for accuracy, scope, and constitution checks before any implementation work.
3. Run **`uiplan scaffold-code --max-loops N`** to drive implementation against the approved plan, capping agent/tool loops with `N`.

## Framework reference

See [UiPlan framework](../2026-04-21-uiplan-framework.md) for roles of `spec.md` / `plan.md` / `tasks.md`, folder conventions, and tooling integration.

## Files

| File | Role |
| --- | --- |
| `_spec-template.md` | Feature specification skeleton |
| `_plan-template.md` | Implementation plan skeleton |
| `_tasks-template.md` | Executable task list skeleton |

Each template includes an **Architecture diagram** section with a Mermaid diagram in **Pro Standard** form (`classDef` + `linkStyle`) per repository diagram rules.
