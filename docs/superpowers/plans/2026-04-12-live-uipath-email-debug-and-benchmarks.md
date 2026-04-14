# Live UiPath Email Reliability + Benchmarking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make live email workflow generation reliably produce openable UiPath projects and add repeatable benchmark tests that guard against regressions.

**Architecture:** Introduce a strict validation pipeline (CLI analyze/get-errors + activity-existence checks), ensure generated chat artifacts are promoted to real UiPath project structure before final validation, and add benchmark tests (simple, long-running, maestro flow) executed by default in CI-compatible mode and optionally in real-cli mode.

**Tech Stack:** Python 3.12, pytest, UiPath CLI (`uip`), Typer chat app, PowerShell shell execution

---

## Scope and Constraints

- This plan targets **RPA/XAML generation reliability** and **benchmark automation** only.
- It does not redesign all skill-routing architecture.
- Real CLI tests must remain optional via env guard to keep local/CI deterministic.

## File Structure (Planned Changes)

- Modify: `uipath_claude/tools/uipath/cli_runner.py`
  - Harden JSON extraction from noisy CLI output.
- Modify: `uipath_claude/artifacts/materialize.py`
  - Enforce strict post-materialization validation and deterministic fallback behavior.
- Modify: `uipath_claude/cli/app.py`
  - Improve validation error display and stop false success messaging.
- Modify: `tests/unit/tools/uipath/test_cli_runner.py`
  - Add noisy-output parser tests.
- Modify: `tests/unit/artifacts/test_materialize.py`
  - Add strict validation behavior tests.
- Modify/Create: `tests/integration/test_mail_workflow_generation.py`
  - Realistic mail invariants and hallucination checks.
- Create: `tests/integration/test_workflow_benchmarks.py`
  - Dispatcher + long-running + maestro benchmark flows.
- Create: `docs/workflow-benchmarks.md`
  - Benchmark runbook, interpretation, and troubleshooting.
- Create: `docs/reports/live-email-debug-report.md`
  - Live run evidence and outcomes.

---

### Task 1: Fix CLI JSON Parsing Robustness

**Files:**
- Modify: `uipath_claude/tools/uipath/cli_runner.py`
- Test: `tests/unit/tools/uipath/test_cli_runner.py`

- [ ] **Step 1: Write failing tests for telemetry-prefixed JSON output**

```python
# tests/unit/tools/uipath/test_cli_runner.py
@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_find_activities_parses_json_with_telemetry_prefix(mock_run):
    payload = {"Result": "Success", "Data": {"Activities": [{"ClassName": "UiPath.Core.Activities.LogMessage", "ActivityTypeId": "LogMessage"}]}}
    mock_proc = MagicMock()
    mock_proc.stdout = "[Telemetry Request] Completed: ProjectPackager.Validate (1.85ms)\n" + json.dumps(payload)
    mock_proc.returncode = 0
    mock_run.return_value = mock_proc

    result = run_uip_rpa_find_activities("LogMessage")

    assert result["success"] is True
    assert len(result["activities"]) == 1
```

- [ ] **Step 2: Run test and verify failure (if currently broken)**

Run: `pytest tests/unit/tools/uipath/test_cli_runner.py::test_find_activities_parses_json_with_telemetry_prefix -v`
Expected: Fails before parser fix, passes after parser fix.

- [ ] **Step 3: Implement parser hardening in CLI runner**

```python
# uipath_claude/tools/uipath/cli_runner.py

def _parse_first_json_payload(text: str) -> dict | None:
    start = text.find("{")
    if start < 0:
        return None
    try:
        payload, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None
```

- [ ] **Step 4: Run full CLI runner tests**

Run: `pytest tests/unit/tools/uipath/test_cli_runner.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add uipath_claude/tools/uipath/cli_runner.py tests/unit/tools/uipath/test_cli_runner.py
git commit --trailer "Made-with: Cursor" -m "fix: parse first JSON payload from noisy uip CLI output"
```

---

### Task 2: Enforce Strict Validation on Generated Artifacts

**Files:**
- Modify: `uipath_claude/artifacts/materialize.py`
- Test: `tests/unit/artifacts/test_materialize.py`

- [ ] **Step 1: Write failing test for activity-validation failure propagation**

```python
# tests/unit/artifacts/test_materialize.py

def test_validate_generated_project_includes_activity_validation_errors(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "project.json").write_text('{"name":"Test","main":"Main.xaml"}', encoding="utf-8")
    (root / "Main.xaml").write_text("<Activity><ui:FakeHallucinatedActivity/></Activity>", encoding="utf-8")

    with patch("uipath_claude.tools.uipath.cli_runner.run_uip_rpa_analyze") as mock_analyze:
        mock_analyze.return_value = {"success": True, "errors": [], "warnings": [], "raw_output": "{}"}
        with patch("uipath_claude.validation.activity_validator.validate_activities_in_xaml") as mock_validate:
            mock_validate.return_value = (False, ["Activity 'FakeHallucinatedActivity' not found in UiPath packages."])
            result = validate_generated_project(root)

    assert result["success"] is False
    assert "FakeHallucinatedActivity" in result["errors"][0]
```

- [ ] **Step 2: Implement strict merge of analyzer + activity validation errors**

```python
# uipath_claude/artifacts/materialize.py
result = run_uip_rpa_analyze(project_path)
activity_errors = []
for xaml_file in project_path.rglob("*.xaml"):
    ok, errors = validate_activities_in_xaml(xaml_file)
    if not ok:
        activity_errors.extend([f"{xaml_file.relative_to(project_path)}: {err}" for err in errors])

combined_errors = list(result["errors"]) + activity_errors
success = result["success"] and not activity_errors
```

- [ ] **Step 3: Run unit tests**

Run: `pytest tests/unit/artifacts/test_materialize.py -v`
Expected: PASS.

- [ ] **Step 4: Run lint for modified files**

Run: `python -m ruff check uipath_claude/artifacts/materialize.py tests/unit/artifacts/test_materialize.py`
Expected: No new lint errors.

- [ ] **Step 5: Commit**

```bash
git add uipath_claude/artifacts/materialize.py tests/unit/artifacts/test_materialize.py
git commit --trailer "Made-with: Cursor" -m "fix: fail generated-project validation on hallucinated activities"
```

---

### Task 3: Build Deterministic Mail Workflow Integration Tests

**Files:**
- Modify/Create: `tests/integration/test_mail_workflow_generation.py`

- [ ] **Step 1: Write integration test for valid mail workflow invariants**

```python
@pytest.mark.integration
def test_mail_workflow_uses_correct_activities(tmp_path):
    # materialize known-good mail workflow and assert required tokens
    ...
    assert "ui:GetOutlookMailMessages" in content
    assert "snm:MailMessage" in content
    assert "ui:StartOutlook" not in content
```

- [ ] **Step 2: Write integration test for hallucinated activity warning path**

```python
@pytest.mark.integration
def test_mail_workflow_validation_detects_hallucinated_activities(tmp_path):
    with patch("uipath_claude.validation.activity_validator.run_uip_rpa_find_activities") as mock_find:
        mock_find.return_value = {"success": True, "activities": [], "raw_output": "{}"}
        with pytest.warns(UserWarning, match="FakeHallucinatedActivity"):
            materialize_from_assistant_text(...)
```

- [ ] **Step 3: Run integration test file**

Run: `pytest tests/integration/test_mail_workflow_generation.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_mail_workflow_generation.py
git commit --trailer "Made-with: Cursor" -m "test: add deterministic mail workflow validity integration tests"
```

---

### Task 4: Add Reusable Benchmark Workflow Suite (RPA + Maestro)

**Files:**
- Create: `tests/integration/test_workflow_benchmarks.py`
- Create: `docs/workflow-benchmarks.md`

- [ ] **Step 1: Implement benchmark helper using resolved `uip` path**

```python
from uipath_claude.tools.uipath.cli_runner import _find_uip_cli

def _run_uip(command: list[str], cwd: Path, timeout: int = 120) -> dict:
    resolved = [_find_uip_cli(), *command]
    proc = subprocess.run(resolved, cwd=str(cwd), capture_output=True, text=True, timeout=timeout, check=False)
    assert proc.returncode == 0
    payload_text = "\n".join(p for p in (proc.stdout, proc.stderr) if p)
    start = payload_text.find("{")
    payload, _ = json.JSONDecoder().raw_decode(payload_text[start:])
    return payload
```

- [ ] **Step 2: Add dispatcher + long-running benchmark tests**

```python
def test_benchmark_dispatcher_template_get_errors():
    result = _run_uip(["rpa", "get-errors", "--project-dir", str(project_dir), "--output", "json"], cwd=repo_root)
    assert result["Result"] == "Success"

def test_benchmark_long_running_template_get_errors():
    result = _run_uip(["rpa", "get-errors", "--project-dir", str(project_dir), "--output", "json"], cwd=repo_root)
    assert result["Result"] == "Success"
```

- [ ] **Step 3: Add maestro benchmark test (solution+flow init+validate)**

```python
def test_benchmark_maestro_flow_init_and_validate(tmp_path):
    _run_uip(["solution", "new", "BenchmarkFlow", "--output", "json"], cwd=workspace)
    _run_uip(["flow", "init", "BenchmarkFlowFlow"], cwd=workspace / "BenchmarkFlow")
    flow_file = workspace / "BenchmarkFlow" / "BenchmarkFlowFlow" / "BenchmarkFlowFlow.flow"
    result = _run_uip(["flow", "validate", str(flow_file), "--output", "json"], cwd=workspace)
    assert result["Result"] == "Success"
```

- [ ] **Step 4: Document benchmark usage and expected output**

Create `docs/workflow-benchmarks.md` with:
- benchmark list
- run commands
- env var (`UIPATH_RUN_BENCHMARKS=1`)
- debug checklist

- [ ] **Step 5: Run benchmarks in real CLI mode**

Run: `$env:UIPATH_RUN_BENCHMARKS='1'; pytest tests/integration/test_workflow_benchmarks.py -v`
Expected: `3 passed`.

- [ ] **Step 6: Commit**

```bash
git add tests/integration/test_workflow_benchmarks.py docs/workflow-benchmarks.md
git commit --trailer "Made-with: Cursor" -m "test: add real-cli benchmark workflow suite including maestro flow"
```

---

### Task 5: Live End-to-End Email Run With Evidence

**Files:**
- Create: `docs/reports/live-email-debug-report.md`

- [ ] **Step 1: Execute live chat generation with fixed session ID**

Run:
```powershell
$env:UIPATH_CHAT_OUTPUT_DIR="C:\Users\DanielaRosenstein\projects\uipath-builder-agent\generated\chat-live"
$env:UIPATH_CHAT_SESSION_ID="live-outlook-test"
"can you build a test workflow for me that will read outlook emails, and log to the user the first 5 email subject?`nexit`n" |
  python -m uipath_claude.cli.app chat --no-banner
```
Expected: workflow generated and validation output printed.

- [ ] **Step 2: Validate generated project directly with CLI**

Run:
```powershell
uip rpa get-errors --project-dir "C:\Users\DanielaRosenstein\projects\uipath-builder-agent\generated\chat-live\live-outlook-test" --output json
```
Expected: no hallucinated activities, errors meaningful if present.

- [ ] **Step 3: Inspect generated `Main.xaml` invariants**

Assert manually or via command:
- contains `ui:GetOutlookMailMessages`
- contains `snm:MailMessage`
- does not contain `GetOutlookQueuedEmails`
- does not contain `ui:OutlookQueuedEmailMessage`

- [ ] **Step 4: Record evidence report**

Create `docs/reports/live-email-debug-report.md` with:
- timestamp
- output folder path
- command transcript snippets
- pass/fail per invariant
- exact remaining errors (if any)
- next fix recommendation

- [ ] **Step 5: Commit**

```bash
git add docs/reports/live-email-debug-report.md
git commit --trailer "Made-with: Cursor" -m "docs: add live email workflow debug evidence report"
```

---

### Task 6: Final Regression Gate Command

**Files:**
- Modify: `docs/workflow-benchmarks.md` (append gate command)

- [ ] **Step 1: Add one-shot regression gate command**

```markdown
## Regression Gate (Run Before Merge)

```powershell
$env:UIPATH_RUN_BENCHMARKS='1'
pytest tests/unit/tools/uipath/test_cli_runner.py \
       tests/unit/artifacts/test_materialize.py \
       tests/integration/test_mail_workflow_generation.py \
       tests/integration/test_workflow_benchmarks.py -v
```
```

- [ ] **Step 2: Run full gate once and verify**

Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add docs/workflow-benchmarks.md
git commit --trailer "Made-with: Cursor" -m "docs: add pre-merge regression gate for workflow reliability"
```

---

## Self-Review

**1. Spec coverage**
- Covers parser robustness, strict validation, benchmark suite, maestro flow, live email evidence, and repeatable gate command.
- Includes references to UiPath CLI behavior and noisy output handling.

**2. Placeholder scan**
- No TODO/TBD placeholders.
- All tasks include concrete files, commands, and expected outcomes.

**3. Type consistency**
- Validation interfaces use existing types from codebase (`dict`, `Tuple[bool, List[str]]`).
- Benchmark helper contract is consistent across benchmark tests.

---

Plan complete and saved to `docs/superpowers/plans/2026-04-12-live-uipath-email-debug-and-benchmarks.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration

2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
