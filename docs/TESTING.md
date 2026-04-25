# Testing (layout and conclusions)

## Where test code lives

- **All pytest modules** are under **`framework/tests/`** (sole `testpaths` entry in `pyproject.toml`).
- **UiPlan** tests (Typer code in `tools/uiplan/`) are in **`framework/tests/uiplan/`** and run explicitly.
- **MCP server** contract tests: **`framework/tests/mcp/`**.

Do **not** add `framework/tests` to the front of `sys.path` in conftest: a subfolder
named `mcp` would shadow the PyPI **`mcp`** (MCP SDK) and break
`mcp_server.server` imports. Integration tests load `artifact_output_paths` via
`importlib` instead of `import` from a hacked path.

| Path | Purpose |
| --- | --- |
| `generated/test-runs/pytest/…` | Persistent on-disk output from a few chat integration tests. Defined in `framework/tests/artifact_output_paths.py` (used via `importlib` in those test modules). |
| `generated/test-runs/manual-review/<id>/` | Human or checklist runs (clones, samples, logs). |
| `generated/chat/`, `generated/evals/`, etc. | Normal CLI / local runs. |

A short index: [framework/tests/README.md](../framework/tests/README.md).

## Conclusions (2026)

- **One default test tree** under `framework/tests/`; UiPlan runtime tests remain explicit under `framework/tests/uiplan/`.
- **One pytest artifact root** for automation: `generated/test-runs/pytest/`.
- **No conftest `sys.path` prepends** for test helpers, to keep `import mcp` working for the MCP
  server.
- **Cleanup blockers (local):** if a root-level **`LogMessageProject/`** (or similar RPA test scaffold) cannot be deleted, a **Studio / host process** may hold `GlobalVariables*.dll` under `.local/` — close Studio and related hosts, then remove manually; do not force-delete in automation loops.

## Commands

```bash
uv run pytest -q
uv run pytest framework/tests/uiplan -q
uv run pytest -m "not integration" -q
```

See also: [SMOKE_TESTS](SMOKE_TESTS.md) and the manual review docs for MCP checklists.
