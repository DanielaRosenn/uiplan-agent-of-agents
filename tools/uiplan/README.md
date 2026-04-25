# UiPlan Runtime (`tools/uiplan`)

This package is runtime code for UiPlan. It is not the template kit.

| Area | Purpose |
| --- | --- |
| `cli.py` | Typer entry point for `generate-docs`, `scaffold-code`, and `validate-mermaid` |
| `generators/` | Materializes `spec.md`, `plan.md`, and `tasks.md` from `templates/uiplan/` |
| `scaffold/` | Project-kind detection and scaffold/validation loop adapters |
| `validators/` | Mermaid extraction, optional `mmdc` checks, and visual-density validation |
| `integrations/` | Hooks for skill-driven execution |

Human-facing usage docs live in `docs/uiplan/`. Reusable markdown templates live in
`templates/uiplan/`. Runtime tests live in `framework/tests/uiplan/` so they are
collected by the repository's single pytest root.
