"""Tests for session-start hooks."""

from __future__ import annotations

import subprocess
from pathlib import Path

from uipath_claude.hooks import session_hooks


def _mock_hooks_payload(command: str = "python ${CLAUDE_PLUGIN_ROOT}/hook.py", timeout: int = 42) -> dict:
    return {
        "hooks": {
            "SessionStart": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": command,
                            "timeout": timeout,
                            "statusMessage": "Run hook",
                        }
                    ]
                }
            ]
        }
    }


def test_run_session_start_hooks_uses_safe_runner(monkeypatch, tmp_path: Path):
    calls: list[tuple[str, dict]] = []
    hooks_parent = tmp_path / "skills"
    hooks_dir = hooks_parent / "hooks"
    hooks_dir.mkdir(parents=True)

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))

        class Result:
            returncode = 0
            stdout = "ok"
            stderr = ""

        return Result()

    monkeypatch.setattr(session_hooks, "get_skills_hooks_path", lambda: hooks_dir)
    monkeypatch.setattr(session_hooks, "load_skills_hooks", lambda: _mock_hooks_payload())
    monkeypatch.setattr(session_hooks, "run_command", fake_run)

    results = session_hooks.run_session_start_hooks()

    assert len(calls) == 1
    command, kwargs = calls[0]
    assert command == f"python {hooks_parent}/hook.py"
    assert kwargs["timeout"] == 42
    assert kwargs["text"] is True
    assert kwargs["cwd"] == str(hooks_parent)
    assert kwargs["env"]["CLAUDE_PLUGIN_ROOT"] == str(hooks_parent)
    assert results == [
        {
            "command": f"python {hooks_parent}/hook.py",
            "status": "success",
            "output": "ok",
        }
    ]


def test_run_session_start_hooks_preserves_failed_status_with_stderr(monkeypatch, tmp_path: Path):
    hooks_parent = tmp_path / "skills"
    hooks_dir = hooks_parent / "hooks"
    hooks_dir.mkdir(parents=True)

    class Failed:
        returncode = 1
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr(session_hooks, "get_skills_hooks_path", lambda: hooks_dir)
    monkeypatch.setattr(session_hooks, "load_skills_hooks", lambda: _mock_hooks_payload("python bad.py", 7))
    monkeypatch.setattr(session_hooks, "run_command", lambda *_args, **_kwargs: Failed())

    results = session_hooks.run_session_start_hooks()

    assert results[0]["status"] == "failed"
    assert results[0]["output"] == "boom"
    assert results[0]["error"] == "boom"


def test_run_session_start_hooks_reports_timeout(monkeypatch, tmp_path: Path):
    hooks_dir = tmp_path / "skills" / "hooks"
    hooks_dir.mkdir(parents=True)

    def raise_timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="python slow.py", timeout=5)

    monkeypatch.setattr(session_hooks, "get_skills_hooks_path", lambda: hooks_dir)
    monkeypatch.setattr(session_hooks, "load_skills_hooks", lambda: _mock_hooks_payload("python slow.py", 5))
    monkeypatch.setattr(session_hooks, "run_command", raise_timeout)

    results = session_hooks.run_session_start_hooks()

    assert results[0]["status"] == "timeout"
    assert results[0]["error"] == "Hook timed out after 5s"
