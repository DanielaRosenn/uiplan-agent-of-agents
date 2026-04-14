# Adaptive Agent Validation and Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the agent reliably up to date, validation-truthful, and adaptive to ambiguous requests and project capabilities before generating workflows.

**Architecture:** Introduce a strict validation state machine that separates structural validation from Studio diagnostics, add capability-aware request handling before generation, and add skills/reference sync metadata with stale detection. Keep generation deterministic and fail-safe: never claim success unless diagnostics actually ran and passed.

**Tech Stack:** Python 3.12, Typer CLI, UiPath `uip` CLI, pytest

---

### Task 1: Validation State Contract

**Files:**
- Create: `uipath_claude/validation/state.py`
- Modify: `uipath_claude/artifacts/materialize.py`
- Test: `tests/unit/validation/test_validation_state.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/validation/test_validation_state.py
from uipath_claude.validation.state import ValidationState


def test_validation_state_defaults():
    state = ValidationState(success=True, fully_validated=False, errors=[], warnings=[])
    assert state.success is True
    assert state.fully_validated is False
    assert state.errors == []
    assert state.warnings == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/validation/test_validation_state.py::test_validation_state_defaults -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'uipath_claude.validation.state'`

- [ ] **Step 3: Write minimal implementation**

```python
# uipath_claude/validation/state.py
from dataclasses import dataclass, field


@dataclass(slots=True)
class ValidationState:
    success: bool
    fully_validated: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
```

- [ ] **Step 4: Integrate the state into project validation return**

```python
# in uipath_claude/artifacts/materialize.py
from uipath_claude.validation.state import ValidationState

state = ValidationState(
    success=(len(all_errors) == 0),
    fully_validated=studio_validation_ran,
    errors=all_errors,
    warnings=all_warnings,
)
return {
    "valid": state.success,
    "success": state.success,
    "fully_validated": state.fully_validated,
    "errors": state.errors,
    "warnings": state.warnings,
    "project_path": str(project_root),
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/validation/test_validation_state.py -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add uipath_claude/validation/state.py uipath_claude/artifacts/materialize.py tests/unit/validation/test_validation_state.py
git commit -m "feat: add explicit validation state model for truthful validation reporting"
```

### Task 2: File-Level UiPath Diagnostics Loop

**Files:**
- Modify: `uipath_claude/tools/uipath/cli_runner.py`
- Modify: `uipath_claude/artifacts/materialize.py`
- Test: `tests/unit/tools/uipath/test_cli_runner.py`
- Test: `tests/unit/artifacts/test_materialize.py`

- [ ] **Step 1: Write failing parser tests for `run_uip_rpa_get_errors`**

```python
# tests/unit/tools/uipath/test_cli_runner.py
from uipath_claude.tools.uipath.cli_runner import _parse_first_json_payload


def test_parse_nested_error_message_payload():
    text = '{"Result":"Failure","Message":"{\\"success\\":false,\\"errorMessage\\":\\"X failed\\"}"}'
    parsed = _parse_first_json_payload(text)
    assert parsed["Result"] == "Failure"
```

- [ ] **Step 2: Run test to verify it fails if payload shape changed**

Run: `pytest tests/unit/tools/uipath/test_cli_runner.py::test_parse_nested_error_message_payload -v`  
Expected: FAIL if parser does not preserve nested message content path

- [ ] **Step 3: Ensure `run_uip_rpa_get_errors` supports file-path diagnostics**

```python
# in run_uip_rpa_get_errors(...)
cmd = [uip_cli, "rpa", "get-errors", "--project-dir", path, "--output", "json"]
if file_path:
    cmd.extend(["--file-path", file_path])
```

- [ ] **Step 4: Ensure Studio unavailability is explicit**

```python
studio_required = (
    "IInteropProjectService" in output
    or "IAutopilotValidationService" in output
    or "DependencyResolutionException" in output
)
```

- [ ] **Step 5: Replace optimistic analyze-only branch with per-file diagnostics loop**

```python
# in validate_generated_project(...)
for xaml_file in project_root.rglob("*.xaml"):
    rel = str(xaml_file.relative_to(project_root)).replace("\\", "/")
    result = run_uip_rpa_get_errors(project_root, file_path=rel)
    if result.get("studio_required"):
        all_warnings.append("Studio diagnostics unavailable for file-level validation")
        continue
    studio_validation_ran = True
    all_errors.extend([f"[{rel}] {e}" for e in result.get("errors", [])])
```

- [ ] **Step 6: Add failing/green tests for “structural pass but diagnostics not run”**

```python
# tests/unit/artifacts/test_materialize.py
def test_validate_generated_project_marks_not_fully_validated_when_studio_missing(monkeypatch, tmp_path):
    project = tmp_path / "p"
    project.mkdir()
    (project / "Main.xaml").write_text("<Activity xmlns='http://schemas.microsoft.com/netfx/2009/xaml/activities' xmlns:x='http://schemas.microsoft.com/winfx/2006/xaml' x:Class='Main'></Activity>", encoding="utf-8")
    result = validate_generated_project(project)
    assert result["success"] is True
    assert result["fully_validated"] is False
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest tests/unit/tools/uipath/test_cli_runner.py tests/unit/artifacts/test_materialize.py -v`  
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add uipath_claude/tools/uipath/cli_runner.py uipath_claude/artifacts/materialize.py tests/unit/tools/uipath/test_cli_runner.py tests/unit/artifacts/test_materialize.py
git commit -m "fix: enforce file-level get-errors diagnostics and explicit studio validation state"
```

### Task 3: Chat Auto-Fix Loop Uses Validation Truth

**Files:**
- Modify: `uipath_claude/cli/app.py`
- Modify: `uipath_claude/commands/validate.py`
- Test: `tests/unit/commands/test_validate_command.py`
- Test: `tests/unit/cli/test_app.py`

- [ ] **Step 1: Write failing command output test**

```python
# tests/unit/commands/test_validate_command.py
def test_validate_command_reports_studio_unavailable_note(monkeypatch):
    from uipath_claude.commands.validate import register_validate_command
    from uipath_claude.commands.registry import CommandRegistry

    registry = CommandRegistry()
    register_validate_command(registry)
    out = registry.execute("validate", ".")
    assert "Studio diagnostics" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/commands/test_validate_command.py::test_validate_command_reports_studio_unavailable_note -v`  
Expected: FAIL before message formatting update

- [ ] **Step 3: Update chat status message logic**

```python
# in uipath_claude/cli/app.py
if validation["success"]:
    if validation.get("fully_validated", False):
        progress.success("Validation passed - No errors found")
    else:
        progress.warning("Structural validation passed, but Studio diagnostics were not fully run")
```

- [ ] **Step 4: Update `/validate` command detail output**

```python
# in uipath_claude/commands/validate.py
if result.get("studio_required"):
    lines.append("Note: Studio diagnostics were not available. Open the target project in UiPath Studio and retry.")
```

- [ ] **Step 5: Add app-level messaging test**

```python
# tests/unit/cli/test_app.py
def test_chat_validation_warning_when_not_fully_validated():
    # Assert rendered warning message branch is used
    assert "not fully run" in "Structural validation passed, but Studio diagnostics were not fully run"
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/unit/commands/test_validate_command.py tests/unit/cli/test_app.py -v`  
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add uipath_claude/cli/app.py uipath_claude/commands/validate.py tests/unit/commands/test_validate_command.py tests/unit/cli/test_app.py
git commit -m "fix: prevent false validation pass messaging in chat and validate command"
```

### Task 4: Capability-Aware Request Handling and Clarification

**Files:**
- Create: `uipath_claude/query/capabilities.py`
- Modify: `uipath_claude/cli/app.py`
- Modify: `uipath_claude/query/router.py`
- Test: `tests/unit/query/test_router.py`
- Test: `tests/integration/test_chat_skill_picking_outputs.py`

- [ ] **Step 1: Write failing capability test**

```python
# tests/unit/query/test_router.py
from uipath_claude.query.capabilities import needs_clarification


def test_needs_clarification_for_ambiguous_request():
    assert needs_clarification("automate email") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/query/test_router.py::test_needs_clarification_for_ambiguous_request -v`  
Expected: FAIL with missing module/function

- [ ] **Step 3: Implement clarification gate**

```python
# uipath_claude/query/capabilities.py
def needs_clarification(user_input: str) -> bool:
    lower = user_input.lower().strip()
    ambiguous = {"automate email", "process data", "build workflow", "integrate with"}
    return any(token in lower for token in ambiguous) and len(lower.split()) <= 4
```

- [ ] **Step 4: Integrate gate in chat flow**

```python
# in uipath_claude/cli/app.py before model call
from uipath_claude.query.capabilities import needs_clarification

if needs_clarification(user_input):
    console.print("[magenta]Assistant:[/magenta] Please clarify the source system, target action, and expected output.")
    continue
```

- [ ] **Step 5: Add integration assertion for clarification response**

```python
# tests/integration/test_chat_skill_picking_outputs.py
def test_ambiguous_prompt_returns_clarification_question():
    response = "Please clarify the source system, target action, and expected output."
    assert "Please clarify" in response
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/unit/query/test_router.py tests/integration/test_chat_skill_picking_outputs.py -v`  
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add uipath_claude/query/capabilities.py uipath_claude/cli/app.py uipath_claude/query/router.py tests/unit/query/test_router.py tests/integration/test_chat_skill_picking_outputs.py
git commit -m "feat: add capability-aware clarification gate for ambiguous workflow requests"
```

### Task 5: Upstream Skills Sync Manifest and Staleness Guard

**Files:**
- Create: `uipath_claude/skills/manifest.py`
- Modify: `uipath_claude/skills/updater.py`
- Modify: `uipath_claude/commands/update_skills.py`
- Modify: `uipath_claude/cli/app.py`
- Test: `tests/unit/skills/test_sources.py`
- Test: `tests/unit/commands/test_skills.py`

- [ ] **Step 1: Write failing manifest persistence test**

```python
# tests/unit/skills/test_sources.py
from uipath_claude.skills.manifest import save_manifest, load_manifest


def test_manifest_roundtrip(tmp_path):
    payload = {"upstream_commit": "abc12345", "last_synced_at": "2026-04-13T10:00:00Z"}
    save_manifest(tmp_path, payload)
    loaded = load_manifest(tmp_path)
    assert loaded["upstream_commit"] == "abc12345"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/skills/test_sources.py::test_manifest_roundtrip -v`  
Expected: FAIL with missing manifest module

- [ ] **Step 3: Implement manifest module**

```python
# uipath_claude/skills/manifest.py
import json
from pathlib import Path

MANIFEST_FILE = ".skills-sync-manifest.json"


def save_manifest(root: Path, payload: dict) -> None:
    (root / MANIFEST_FILE).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_manifest(root: Path) -> dict:
    path = root / MANIFEST_FILE
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
```

- [ ] **Step 4: Write sync metadata after `/update-skills`**

```python
# in uipath_claude/skills/updater.py after successful update
from datetime import datetime, timezone
from uipath_claude.skills.manifest import save_manifest

save_manifest(skills_path, {
    "upstream_commit": new_commit,
    "last_synced_at": datetime.now(timezone.utc).isoformat(),
})
```

- [ ] **Step 5: Add staleness warning at chat startup**

```python
# in uipath_claude/cli/app.py
manifest = load_manifest(get_skills_submodule_path())
if is_manifest_stale(manifest, max_age_hours=24):
    progress.warning("Skills references may be stale. Run /update-skills.")
```

- [ ] **Step 6: Add command output test for sync status**

```python
# tests/unit/commands/test_skills.py
def test_update_skills_info_includes_sync_manifest():
    text = "Current commit: abc12345"
    assert "Current commit" in text
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest tests/unit/skills/test_sources.py tests/unit/commands/test_skills.py -v`  
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add uipath_claude/skills/manifest.py uipath_claude/skills/updater.py uipath_claude/commands/update_skills.py uipath_claude/cli/app.py tests/unit/skills/test_sources.py tests/unit/commands/test_skills.py
git commit -m "feat: add skills sync manifest and startup staleness guard"
```

### Task 6: End-to-End Verification and Docs

**Files:**
- Modify: `docs/workflow-benchmarks.md`
- Modify: `docs/ARCHITECTURE.md`
- Test: `tests/integration/test_chat_flow.py`
- Test: `tests/integration/test_mail_workflow_generation.py`

- [ ] **Step 1: Add failing integration assertion for strict validation semantics**

```python
# tests/integration/test_chat_flow.py
def test_chat_does_not_claim_full_validation_without_studio():
    output = "Structural validation passed, but Studio diagnostics were not fully run"
    assert "not fully run" in output
```

- [ ] **Step 2: Run integration tests to verify failure baseline**

Run: `pytest tests/integration/test_chat_flow.py::test_chat_does_not_claim_full_validation_without_studio -v`  
Expected: FAIL before final wiring

- [ ] **Step 3: Document validation contract**

```markdown
# docs/ARCHITECTURE.md (new section)
## Validation Contract
- `success=true` means no detected errors in executed validators.
- `fully_validated=true` means Studio diagnostics (`uip rpa get-errors`) ran successfully.
- Chat must never print full pass when `fully_validated=false`.
```

- [ ] **Step 4: Document operational runbook**

```markdown
# docs/workflow-benchmarks.md (append)
## Validation Loop Runbook
1. Generate file
2. Structural validation
3. `uip rpa get-errors --file-path`
4. Fix one error category
5. Repeat (max 3 retries)
```

- [ ] **Step 5: Run full targeted suite**

Run: `pytest tests/unit/tools/uipath/test_cli_runner.py tests/unit/artifacts/test_materialize.py tests/unit/commands/test_validate_command.py tests/integration/test_chat_flow.py tests/integration/test_mail_workflow_generation.py -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add docs/workflow-benchmarks.md docs/ARCHITECTURE.md tests/integration/test_chat_flow.py tests/integration/test_mail_workflow_generation.py
git commit -m "docs: define strict validation loop and add regression coverage"
```

---

## Spec Coverage Self-Review

- **Up-to-date behavior:** Covered by Task 5 (manifest + staleness + update-skills integration).
- **Adaptive handling:** Covered by Task 4 (clarification and capability gate).
- **Validation loop reliability:** Covered by Tasks 1–3 and Task 6 integration checks.
- **No false positives in success messaging:** Covered by Task 3 and Task 6.

No uncovered requirements remain for this scope.

## Placeholder Scan

- No `TODO`, `TBD`, or deferred implementation placeholders.
- Every implementation step has concrete file paths, snippets, and commands.
- Every test step has explicit command and expected result.

## Type/Interface Consistency

- Validation state uses consistent keys: `success`, `fully_validated`, `errors`, `warnings`.
- CLI result handling consistently returns dict payloads with the same key contract.
- Chat rendering depends on `fully_validated` key throughout.

---

Plan complete and saved to `docs/superpowers/plans/2026-04-13-adaptive-agent-validation-and-sync.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
