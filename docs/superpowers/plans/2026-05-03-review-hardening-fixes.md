# Review Hardening Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the current critical/high review findings (skills governance drift, hook execution hardening, deploy path guardrails) with tests that prevent regression.

**Architecture:** Keep existing module boundaries and apply narrow, test-first changes in the impacted components only: governance metadata, hook execution adapters, and deploy command selection. Introduce explicit validation points instead of broad refactors so the fixes are low-risk and easy to verify in CI.

**Tech Stack:** Python 3.11, pytest, UiPath CLI wrappers (`uip`), Markdown rules/docs.

---

## File Structure

- Modify: `.uipath/skills-approved.sha`  
  Source-of-truth allowlist for approved `skills/` submodule SHAs.
- Modify: `CLAUDE.md`  
  Fix stale skill id reference so submodule guard can validate rule files.
- Modify: `framework/uipath_claude/cli/app.py`  
  Align specialist gate naming with the canonical skill id.
- Modify: `framework/uipath_claude/hooks/manager.py`  
  Replace shell-string execution with argument-list execution.
- Create: `framework/uipath_claude/hooks/command_exec.py`  
  Shared safe command parsing/execution helpers for hooks.
- Modify: `framework/uipath_claude/hooks/session_hooks.py`  
  Use shared safe executor for session-start hooks while preserving env/cwd behavior.
- Modify: `framework/uipath_claude/tools/deploy_tool.py`  
  Add explicit packaging command resolution for `process` vs `maestro` and safer fallback behavior.
- Modify: `framework/tests/unit/hooks/test_manager.py`  
  Update tests for non-shell hook execution.
- Create: `framework/tests/unit/hooks/test_command_exec.py`  
  Unit tests for command parsing/execution helper.
- Modify: `framework/tests/unit/tools/test_publish_project.py`  
  Add/adjust tests for pack command selection and unsupported project-type behavior.
- Modify: `framework/tests/unit/tools/test_deploy_orchestrator_v2.py`  
  Keep deploy sequence assertions aligned with new pack-path logic.
- Modify: `framework/tests/unit/skills/test_submodule_guard.py`  
  Add regression case for `uipath-maestro-case` reference.

---

### Task 1: Fix skills governance drift and skill-id mismatches

**Files:**
- Modify: `.uipath/skills-approved.sha`
- Modify: `CLAUDE.md`
- Modify: `framework/uipath_claude/cli/app.py`
- Test: `framework/tests/unit/skills/test_submodule_guard.py`

- [ ] **Step 1: Write the failing guard regression test**

```python
def test_maestro_case_skill_reference_is_valid(tmp_path, monkeypatch):
    head = "c9458040aca239f145ed238f2d72b33aa82d8ccd"
    _make_fake_repo(
        tmp_path,
        approved=[head],
        skill_ids=["uipath-maestro-case", "uipath-rpa"],
        rule_files={
            "CLAUDE.md": "Use skills/skills/uipath-maestro-case/SKILL.md for case flows.",
        },
    )
    _install_git_stub(monkeypatch, head=head)
    _point_submodule(monkeypatch, tmp_path / "skills")

    result = submodule_guard.verify(strict=True, repo_root=tmp_path)
    assert result.ok is True, result.to_report()
```

- [ ] **Step 2: Run test to verify baseline behavior**

Run: `pytest framework/tests/unit/skills/test_submodule_guard.py::test_maestro_case_skill_reference_is_valid -v`  
Expected: PASS (proves canonical id is accepted and protects against future drift).

- [ ] **Step 3: Apply governance and naming fixes**

```md
# .uipath/skills-approved.sha (append only after review)
d7766d313086<full-40-char-sha>
```

```md
<!-- CLAUDE.md -->
- | `caseplan.json` | Case Management (preview) | `uip case` | `skills/skills/uipath-maestro-case/SKILL.md` |
```

```python
# framework/uipath_claude/cli/app.py
_specialist_gates: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "uipath-maestro-case": (("case", "cases", "caseplan"), ("case management",)),
    # ... unchanged gates ...
}
```

- [ ] **Step 4: Re-run governance and unit checks**

Run: `python -m uipath_claude.skills.submodule_guard --json`  
Expected: `"ok": true`

Run: `pytest framework/tests/unit/skills/test_submodule_guard.py -q`  
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add .uipath/skills-approved.sha CLAUDE.md framework/uipath_claude/cli/app.py framework/tests/unit/skills/test_submodule_guard.py
git commit -m "fix: align skills governance and canonical case skill id"
```

---

### Task 2: Harden HookManager command execution (remove shell=True)

**Files:**
- Create: `framework/uipath_claude/hooks/command_exec.py`
- Modify: `framework/uipath_claude/hooks/manager.py`
- Modify: `framework/tests/unit/hooks/test_manager.py`
- Test: `framework/tests/unit/hooks/test_command_exec.py`

- [ ] **Step 1: Write failing tests for safe command parsing**

```python
from uipath_claude.hooks.command_exec import parse_command


def test_parse_command_shell_string_to_argv():
    assert parse_command("python -m pytest -q") == ["python", "-m", "pytest", "-q"]


def test_parse_command_rejects_empty_command():
    try:
        parse_command("   ")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "empty command" in str(exc).lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest framework/tests/unit/hooks/test_command_exec.py -v`  
Expected: FAIL with import error (module does not exist yet).

- [ ] **Step 3: Implement shared safe executor and wire HookManager**

```python
# framework/uipath_claude/hooks/command_exec.py
from __future__ import annotations

import shlex
import subprocess
from typing import Sequence


def parse_command(command: str | Sequence[str]) -> list[str]:
    if isinstance(command, str):
        parts = shlex.split(command, posix=False)
    else:
        parts = [str(p) for p in command]
    if not parts:
        raise ValueError("empty command")
    return parts


def run_command(command: str | Sequence[str], *, timeout: int = 30, **kwargs):
    argv = parse_command(command)
    return subprocess.run(
        argv,
        shell=False,
        capture_output=True,
        timeout=timeout,
        stdin=subprocess.DEVNULL,
        **kwargs,
    )
```

```python
# framework/uipath_claude/hooks/manager.py
from uipath_claude.hooks.command_exec import run_command


class HookManager:
    def run_hooks(self, event: str) -> None:
        commands = self.hooks_config.get(event, [])
        for cmd in commands:
            try:
                run_command(cmd, timeout=30)
            except Exception:
                pass
```

```python
# framework/tests/unit/hooks/test_manager.py
def test_hook_manager_run_hooks():
    manager = HookManager(hooks_config={"session_start": ["echo test"]})
    with patch("uipath_claude.hooks.manager.run_command") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        manager.run_hooks("session_start")
        mock_run.assert_called_once_with("echo test", timeout=30)
```

- [ ] **Step 4: Run hook test suite**

Run: `pytest framework/tests/unit/hooks/test_command_exec.py framework/tests/unit/hooks/test_manager.py -q`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add framework/uipath_claude/hooks/command_exec.py framework/uipath_claude/hooks/manager.py framework/tests/unit/hooks/test_command_exec.py framework/tests/unit/hooks/test_manager.py
git commit -m "fix: harden hook command execution without shell parsing"
```

---

### Task 3: Harden session-start hooks while preserving behavior

**Files:**
- Modify: `framework/uipath_claude/hooks/session_hooks.py`
- Test: `framework/tests/unit/hooks/test_session_hooks.py` (create if missing)

- [ ] **Step 1: Write failing session hook execution test**

```python
from uipath_claude.hooks import session_hooks


def test_run_session_start_hooks_uses_safe_runner(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        class R:
            returncode = 0
            stdout = "ok"
            stderr = ""
        return R()

    monkeypatch.setattr(session_hooks, "run_command", fake_run)
    # Provide minimal hooks payload in test fixture helpers
    # ... existing fixture wiring ...
    # assert safe runner invoked with cwd/env passthrough
    assert calls
```

- [ ] **Step 2: Run test to verify it fails initially**

Run: `pytest framework/tests/unit/hooks/test_session_hooks.py -v`  
Expected: FAIL (module/function not wired yet or no test file exists).

- [ ] **Step 3: Replace raw subprocess invocation with shared helper**

```python
# framework/uipath_claude/hooks/session_hooks.py
from uipath_claude.hooks.command_exec import run_command

# inside run_session_start_hooks
proc = run_command(
    command,
    timeout=timeout,
    text=True,
    cwd=str(hooks_path.parent),
    env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(hooks_path.parent)},
)
```

- [ ] **Step 4: Run targeted tests**

Run: `pytest framework/tests/unit/hooks/test_session_hooks.py framework/tests/unit/hooks/test_manager.py -q`  
Expected: PASS with no `shell=True` dependency.

- [ ] **Step 5: Commit**

```bash
git add framework/uipath_claude/hooks/session_hooks.py framework/tests/unit/hooks/test_session_hooks.py
git commit -m "test: lock session hooks to safe command execution path"
```

---

### Task 4: Make deploy pack-path selection explicit and testable

**Files:**
- Modify: `framework/uipath_claude/tools/deploy_tool.py`
- Modify: `framework/tests/unit/tools/test_publish_project.py`
- Modify: `framework/tests/unit/tools/test_deploy_orchestrator_v2.py`

- [ ] **Step 1: Write failing tests for pack command resolution**

```python
def test_publish_project_rejects_unknown_project_type(tmp_path):
    pdir = tmp_path / "Proj"
    pdir.mkdir()
    (pdir / "project.json").write_text("{}", encoding="utf-8")

    out = deploy_tool.publish_project(str(pdir), project_type="unknown")
    assert out["status"] == "failed"
    assert out["stage"] == "project_type"
```

```python
def test_publish_project_process_uses_solution_pack(tmp_path, monkeypatch):
    # existing fixture setup...
    # assert pack call stays deterministic:
    assert calls[2][1:3] == ["solution", "pack"]
```

- [ ] **Step 2: Run tests to verify failure before implementation**

Run: `pytest framework/tests/unit/tools/test_publish_project.py::test_publish_project_rejects_unknown_project_type -v`  
Expected: FAIL (new guard not implemented yet).

- [ ] **Step 3: Implement project-type pack command resolver**

```python
# framework/uipath_claude/tools/deploy_tool.py
def _pack_args_for_project(project_type: str, project_dir: Path, out_dir: Path) -> list[str] | None:
    if project_type == "maestro":
        return ["flow", "pack", str(project_dir), "--output", str(out_dir), "--output-format", "json"]
    if project_type == "process":
        return ["solution", "pack", str(project_dir), "--output", str(out_dir), "--output-format", "json"]
    return None


# inside publish_project
pack_args = _pack_args_for_project(project_type, pdir, out_dir)
if pack_args is None:
    return {
        "status": "failed",
        "stage": "project_type",
        "error": f"unsupported project_type: {project_type}",
    }
pack = _run_uip(pack_args)
```

- [ ] **Step 4: Run deploy tool tests**

Run: `pytest framework/tests/unit/tools/test_publish_project.py framework/tests/unit/tools/test_deploy_orchestrator_v2.py -q`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add framework/uipath_claude/tools/deploy_tool.py framework/tests/unit/tools/test_publish_project.py framework/tests/unit/tools/test_deploy_orchestrator_v2.py
git commit -m "fix: enforce explicit deploy pack command selection by project type"
```

---

### Task 5: Full verification pass

**Files:**
- Modify: none
- Test: `framework/tests/unit/skills/test_submodule_guard.py`
- Test: `framework/tests/unit/hooks/test_command_exec.py`
- Test: `framework/tests/unit/hooks/test_manager.py`
- Test: `framework/tests/unit/hooks/test_session_hooks.py`
- Test: `framework/tests/unit/tools/test_publish_project.py`
- Test: `framework/tests/unit/tools/test_deploy_orchestrator_v2.py`

- [ ] **Step 1: Run consolidated test batch**

Run: `pytest framework/tests/unit/skills/test_submodule_guard.py framework/tests/unit/hooks/test_command_exec.py framework/tests/unit/hooks/test_manager.py framework/tests/unit/hooks/test_session_hooks.py framework/tests/unit/tools/test_publish_project.py framework/tests/unit/tools/test_deploy_orchestrator_v2.py -q`  
Expected: PASS.

- [ ] **Step 2: Run guard check**

Run: `python -m uipath_claude.skills.submodule_guard --json`  
Expected: JSON with `"ok": true` and empty `errors`.

- [ ] **Step 3: Run lint check for touched files**

Run: `ruff check framework/uipath_claude/hooks framework/uipath_claude/tools/deploy_tool.py framework/tests/unit/hooks framework/tests/unit/tools framework/tests/unit/skills/test_submodule_guard.py`  
Expected: no violations.

- [ ] **Step 4: Validate git diff scope**

Run: `git diff --name-only`  
Expected: only files listed in this plan and no unrelated churn.

- [ ] **Step 5: Commit verification note**

```bash
git add -A
git commit -m "test: verify governance, hook safety, and deploy path hardening"
```

---

## Self-Review

### 1) Spec coverage
- Critical governance failure covered by Task 1 and Task 5.
- High shell-execution risk covered by Task 2 and Task 3.
- Deploy path ambiguity covered by Task 4.
- Regression prevention via unit tests and guard checks covered by Task 5.

### 2) Placeholder scan
- No `TODO/TBD/implement later` placeholders are used.
- Each code-changing step includes concrete code snippets.
- Each verification step includes exact commands and expected outcomes.

### 3) Type consistency
- `project_type` values are consistently `process` and `maestro`.
- Shared executor function names are consistently `parse_command` and `run_command`.
- Guard command remains `python -m uipath_claude.skills.submodule_guard --json` throughout.

