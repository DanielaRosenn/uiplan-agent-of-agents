# Test suite (single source)

All **pytest** targets are under this directory: `testpaths = ["framework/tests"]` in `pyproject.toml`.

| Area | Path |
| --- | --- |
| **Unit, integration, e2e, etc.** | `framework/tests/…` |
| **UiPlan** (implementation in `tools/uiplan/`) | `framework/tests/uiplan/` |
| **MCP** server tools | `framework/tests/mcp_tests/` |

**On-disk test material:** `generated/test-runs/pytest/…` (see `artifact_output_paths.py` and
`importlib` usage in chat integration tests; no `sys.path` hack in conftest).

[docs/TESTING.md](../../docs/TESTING.md) has the full map and **testing conclusions**.
