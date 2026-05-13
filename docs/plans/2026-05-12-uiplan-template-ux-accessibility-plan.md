# UiPlan Template UX and Accessibility Upgrade Plan

## Goal

Make all UiPlan templates easier to use in new projects by improving readability,
navigation, accessibility, and completion clarity without breaking generator
compatibility.

## In Scope

- `templates/uiplan/README.md`
- `templates/uiplan/_spec-template.md`
- `templates/uiplan/_plan-template.md`
- `templates/uiplan/_tasks-template.md`
- `templates/uiplan/_workflow-catalog.md`
- `templates/uiplan/_diagram-patterns.md`

## Outcomes

- Faster first draft creation for new projects.
- Better heading structure and scanability.
- Clear plain-language instructions near high-friction sections.
- Accessibility checklist for template maintainers.
- No generator-breaking placeholder or anchor changes.

## Guardrails

- Keep existing placeholder tokens.
- Preserve required anchor headings where Studio views/generators depend on them.
- Improve structure and wording, not template logic.
- Keep changes small and reviewable per file.

## Validation

1. Verify changed templates still retain required placeholders and headings.
2. Run template-related tests:
   - `uv run pytest framework/tests/uiplan -q`
3. Spot-check generated docs for readability and section flow.
