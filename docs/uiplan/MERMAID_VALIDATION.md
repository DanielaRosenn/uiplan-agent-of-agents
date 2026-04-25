# Optional Mermaid syntax check (`mmdc`)

UiPlan markdown (kit templates, generated bundles) may include fenced ` ```mermaid ` blocks.
Syntax errors are caught early by running the Mermaid CLI in batch mode.

## Prerequisite

- Node.js 18+
- Global CLI: `npm install -g @mermaid-js/mermaid-cli` (provides the `mmdc` binary on `PATH`)

## Command

From the repository root:

```powershell
uv run python -m tools.uiplan validate-mermaid templates/uiplan/_spec-template.md
```

Pass one or more Markdown files. The command extracts every fenced Mermaid block and runs `mmdc` for each. Exit code `1` on the first failing block (stderr surfaced).

## CI

Default `pytest` stays fast and does **not** require Node. A lightweight unit test covers only the
Markdown extractor (`tools/uiplan/validators/mermaid_extract.py`); see `framework/tests/uiplan/test_mermaid_extract.py` and `test_mermaid_mmdc_optional.py`. To gate releases on diagrams,
add a separate workflow step or `workflow_dispatch` job that installs `@mermaid-js/mermaid-cli`
and runs the command above on chosen paths.
