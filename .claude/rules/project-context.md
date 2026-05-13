# Project Context (Auto-discovered)

## Identity
- Project: `uipath-builder-agent`
- Type: LangGraph coded-agent workspace (Python)
- Primary entry graph: `langgraph.json` -> `uipath_claude.graph:graph`
- Primary CLI entrypoint: `uipath-claude` -> `uipath_claude.cli.app:app`

## Structure
- Runtime package root: `framework/`
- Main runtime: `framework/uipath_claude/`
- MCP server: `framework/mcp_server/`
- Template sources: `templates/` (canonical), `framework/uipath_claude/templates/` (generated mirrors)

## Tests
- All tests: `uv run pytest -q`
- Non-integration: `uv run pytest -m "not integration" -q`
- UiPlan tests: `uv run pytest framework/tests/uiplan -q`

## Conventions
- Python 3.11+
- Line length: 100
- Snake_case module naming
- LangGraph route -> execute flow in graph builder
- Do not edit generated template mirrors directly when canonical source exists
