# Testing (layout and conclusions)

## Where test code lives

- **All pytest modules** are under **`framework/tests/`** (sole `testpaths` entry in `pyproject.toml`).
- **UiPlan** tests (Typer code in `tools/uiplan/`) are in **`framework/tests/uiplan/`** and run explicitly.
- **MCP server** contract tests: **`framework/tests/mcp_tests/`**.

**Naming:** the MCP test package is `mcp_tests/`, not `mcp/`, so PyPI `mcp` is
not shadowed. Do **not** add `framework/tests` alone to the front of `sys.path` in
conftest: a folder literally named `mcp` next to the test root would break
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
- **No conftest `sys.path` prepends** for ad-hoc test helpers. Use `importlib` for
  `artifact_output_paths` and keep the MCP test directory named `mcp_tests/`.
- **Cleanup blockers (local):** if a root-level **`LogMessageProject/`** (or similar RPA test scaffold) cannot be deleted, a **Studio / host process** may hold `GlobalVariables*.dll` under `.local/` — close Studio and related hosts, then remove manually; do not force-delete in automation loops.

## Commands

```bash
uv run pytest -q
uv run pytest framework/tests/uiplan -q
uv run pytest framework/tests/mcp_tests/test_server.py -q
uv run pytest framework/tests/integration/test_chat_skill_picking_outputs.py \
  framework/tests/integration/test_integration_service_workflows.py::test_chat_integration_service_intent_detection -q
uv run pytest -m "not integration" -q
```

## Suggested fixes (recovery lessons)

- **Scattered chat artifacts:** tests used multiple `generated/test-runs/<suite>` roots. Route automation output through `generated/test-runs/pytest/…` via `artifact_output_paths.py`; keep manual review under `generated/test-runs/manual-review/…`.
- **MCP import failures:** a test folder named `mcp` can shadow the PyPI SDK. Keep `framework/tests/mcp_tests/` and avoid prepending `framework/tests` to `sys.path` for helper imports.
- **Broad search-replace damage:** restore unrelated files before narrow test-layout edits; re-check with `git diff --stat` before running the suite.

## Last verification (automated)

Re-run the commands above after any change to `pyproject.toml`, `conftest`, or
`mcp_server/`. Full-suite numbers belong in CI logs, not a fixed number here.
See also: [SMOKE_TESTS](SMOKE_TESTS.md) and the manual review docs for MCP checklists.
