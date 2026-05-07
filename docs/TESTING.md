# Testing

Single home for the test layout, command reference, smoke tests,
and Studio cleanup playbook.

For detailed end-to-end smoke scenarios, see
[`SMOKE_TESTS.md`](SMOKE_TESTS.md).

---

## Where test code lives

- **All pytest modules** are under **`framework/tests/`** (sole `testpaths`
  entry in `pyproject.toml`).
- **UiPlan** tests (Typer code in `tools/uiplan/`) are in
  **`framework/tests/uiplan/`** and run explicitly.
- **MCP server** contract tests: **`framework/tests/mcp_tests/`**.

**Naming:** the MCP test package is `mcp_tests/`, not `mcp/`, so PyPI `mcp` is
not shadowed. Do **not** add `framework/tests` alone to the front of `sys.path`
in conftest: a folder literally named `mcp` next to the test root would break
`mcp_server.server` imports. Integration tests load `artifact_output_paths` via
`importlib` instead of `import` from a hacked path.

| Path | Purpose |
| --- | --- |
| `generated/test-runs/pytest/...` | Persistent on-disk output from a few chat integration tests. Defined in `framework/tests/artifact_output_paths.py` (used via `importlib` in those test modules). |
| `generated/test-runs/manual-review/<id>/` | Human or checklist runs (clones, samples, logs). |
| `generated/chat/`, `generated/evals/`, etc. | Normal CLI / local runs. |

A short index: [`framework/tests/README.md`](../framework/tests/README.md).

---

## Commands

```bash
uv run pytest -q
uv run pytest framework/tests/uiplan -q
uv run pytest framework/tests/mcp_tests/test_server.py -q
uv run pytest framework/tests/integration/test_chat_skill_picking_outputs.py \
  framework/tests/integration/test_integration_service_workflows.py::test_chat_integration_service_intent_detection -q
uv run pytest -m "not integration" -q
```

A full `pytest` over **~1424** collected tests can take a long time; a
mid-run stall may mean a single test is waiting on I/O. Use `pytest -x` or
`--maxfail=1` to find the first failure, or run in CI.

Use the repo venv: `.venv\Scripts\python.exe -m pytest ...` (or `uv run` if
it responds; `uv run` has been observed to block with no output on some
Windows runs).

---

## Conclusions (2026)

- **One default test tree** under `framework/tests/`; UiPlan runtime tests
  remain explicit under `framework/tests/uiplan/`.
- **One pytest artifact root** for automation: `generated/test-runs/pytest/`.
- **No conftest `sys.path` prepends** for ad-hoc test helpers. Use `importlib`
  for `artifact_output_paths` and keep the MCP test directory named
  `mcp_tests/`.
- **Cleanup blockers (local):** if a root-level **`LogMessageProject/`** (or
  similar RPA test scaffold) cannot be deleted, a **Studio / host process**
  may hold `GlobalVariables*.dll` under `.local/` - close Studio and related
  hosts, then remove manually; do not force-delete in automation loops.

### Suggested fixes (recovery lessons)

- **Scattered chat artifacts:** tests used multiple `generated/test-runs/<suite>`
  roots. Route automation output through `generated/test-runs/pytest/...` via
  `artifact_output_paths.py`; keep manual review under
  `generated/test-runs/manual-review/...`.
- **MCP import failures:** a test folder named `mcp` can shadow the PyPI SDK.
  Keep `framework/tests/mcp_tests/` and avoid prepending `framework/tests` to
  `sys.path` for helper imports.
- **Broad search-replace damage:** restore unrelated files before narrow
  test-layout edits; re-check with `git diff --stat` before running the
  suite.

### Last verification (2026-04-25, local)

| Command | Result |
| --- | --- |
| `python -m pytest framework/tests/uiplan -q` | 16 passed (~20s) |
| `python -m pytest framework/tests/mcp_tests/test_server.py -q` | 10 passed, 1 warning (~2.4s) |
| `python -m pytest` (two chat integration modules + one test id) | 4 passed (~90s) |

---

## Manual chat tests with Studio cleanup

When testing chat-driven workflow generation against a live UiPath
Studio, follow this loop. Studio leaves processes (`UiPath.Studio`,
`UiPath.Executor`, `UiRobot`, `UiPath.Agent`) running between tests
that hold file locks and consume resources.

### Quick start

Single test with auto-cleanup:

```powershell
.\run_test_with_cleanup.ps1 -TestInput "Create a workflow that logs Hello World" -TestID "BUILD-001"
```

### Manual loop

```powershell
# 1. New isolated test dir
$testDir = "C:\Users\$env:USERNAME\projects\test-$(Get-Date -Format 'HHmmss')"
mkdir $testDir; cd $testDir

# 2. Run the chat
echo "Your test input here`nexit" | uipath-claude chat --no-plan 2>&1 |
    Tee-Object output.txt

# 3. Inspect what was created
Get-ChildItem -Recurse -Include "*.xaml","project.json"
Select-String -Path output.txt -Pattern "validation passed"
Select-String -Path output.txt -Pattern "\[ANSWERING\]|\[CLARIFYING\]"

# 4. If Studio held the project (open-project, debug, CLI Studio IPC),
#    release it before cleanup:
uip rpa close-project --project-dir $testDir --output json

# 5. Mandatory cleanup (kills Studio/Executor/UiRobot/Agent)
cd C:\Users\<you>\projects\uipath-builder-agent
.\cleanup_after_tests.ps1
```

When to run cleanup:

- After each test session
- Before a new batch of tests
- If tests are failing unexpectedly
- If system performance is degraded

### Troubleshooting

| Symptom | Action |
| --- | --- |
| Test hangs | `Get-Process uipath-claude \| Stop-Process -Force` then `.\cleanup_after_tests.ps1` |
| `Access Denied` / `File Locked` | `Get-Process UiPath* \| Stop-Process -Force; Start-Sleep 2` |
| Many Studio instances | `(Get-Process UiPath.Studio).Count` then `.\cleanup_after_tests.ps1` if > 5 |

### Best practices

1. Always cleanup between test batches.
2. Monitor with `Get-Process UiPath* | Measure-Object`.
3. Use timeouts; tests should not run more than 2-3 minutes.
4. Periodically delete old test dirs:

   ```powershell
   Get-ChildItem C:\Users\$env:USERNAME\projects -Directory -Filter "test-*" |
       Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-1) } |
       Remove-Item -Recurse -Force
   ```

### Full test cycle example

```powershell
.\cleanup_after_tests.ps1

$tests = @(
    "Create workflow with log message",
    "What is project.json?",
    "Automate my email",
    "Create Excel workflow",
    "Create workflow with variables"
)

foreach ($test in $tests) {
    Write-Host "Testing: $test" -ForegroundColor Yellow
    echo "$test`nexit" | uipath-claude chat --no-plan
    Get-Process UiPath.Executor -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 2
}

.\cleanup_after_tests.ps1

if (Get-Process UiPath* -ErrorAction SilentlyContinue) {
    Write-Host "Some processes still running" -ForegroundColor Yellow
} else {
    Write-Host "All clean" -ForegroundColor Green
}
```

The cleanup script:

- Gracefully closes Studio windows (`$process.CloseMainWindow()`).
- Force-kills if still running after 500 ms.
- Handles multiple instances and reports what was closed.
- Safe to run anytime; only closes test-related processes.

---

## See also

- [`SMOKE_TESTS.md`](SMOKE_TESTS.md) - end-to-end smoke scenarios
- [`legacy/MANUAL_EVAL_AND_QA.md`](legacy/MANUAL_EVAL_AND_QA.md) - manual eval matrix (consolidation pending)
- [`evaluations/README.md`](evaluations/README.md) - automated eval harness
- [`evaluations/HOW_TO_RUN_TESTS.md`](evaluations/HOW_TO_RUN_TESTS.md) - prerequisites for evals
