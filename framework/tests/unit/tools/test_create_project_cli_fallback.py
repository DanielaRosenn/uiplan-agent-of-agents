"""Tests for create_project CLI-only fallback when Studio IPC is unavailable."""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

from uipath_claude.tools import skill_execution_tools as set_mod
from uipath_claude.tools.skill_execution_tools import create_project


def _fake_proc(returncode: int = 0, stdout: str = "", stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def _set_chat_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path / "chat"))
    monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")


def test_fallback_runs_when_studio_unresolvable_message(tmp_path, monkeypatch):
    """Studio-unresolvable error from rpa create-project triggers CLI-only scaffold."""
    _set_chat_env(monkeypatch, tmp_path)
    parent = tmp_path / "out"
    calls: list[list[str]] = []

    def _runner(cmd, *args, **kwargs):
        calls.append(list(cmd))
        if "create-project" in cmd:
            return _fake_proc(
                returncode=1,
                stderr="Error: Could not resolve Studio installation directory. Use --studio-dir.",
            )
        if "solution" in cmd and "new" in cmd:
            return _fake_proc(returncode=0, stdout='{"ok": true}')
        return _fake_proc()

    with (
        patch.object(set_mod, "_find_uip_cli", return_value="uip"),
        patch.object(set_mod, "_resolve_studio_dir", return_value=None),
        patch.object(set_mod.subprocess, "run", side_effect=_runner),
    ):
        result = create_project.invoke(
            {
                "project_dir": str(parent),
                "project_name": "FbProj",
                "project_type": "process",
                "auto_verify": False,
            }
        )

    assert result.startswith("[OK]"), result
    assert "created_via: cli-fallback" in result
    pj = parent / "FbProj" / "project.json"
    assert pj.exists()
    payload = json.loads(pj.read_text())
    assert payload["name"] == "FbProj"
    assert payload["dependencies"] == {}
    assert payload["projectType"] == "Process"
    # Two attempts: original create-project + solution new
    assert any("create-project" in c for c in calls)
    assert any("solution" in c and "new" in c for c in calls)


def test_fallback_for_library_uses_library_project_type(tmp_path, monkeypatch):
    _set_chat_env(monkeypatch, tmp_path)
    parent = tmp_path / "out"

    def _runner(cmd, *args, **kwargs):
        if "create-project" in cmd:
            return _fake_proc(returncode=0, stdout="ok")  # success but no project.json
        return _fake_proc()

    with (
        patch.object(set_mod, "_find_uip_cli", return_value="uip"),
        patch.object(set_mod, "_resolve_studio_dir", return_value=None),
        patch.object(set_mod.subprocess, "run", side_effect=_runner),
    ):
        result = create_project.invoke(
            {
                "project_dir": str(parent),
                "project_name": "FbLib",
                "project_type": "library",
                "auto_verify": False,
            }
        )

    assert result.startswith("[OK]"), result
    pj = parent / "FbLib" / "project.json"
    payload = json.loads(pj.read_text())
    assert payload["projectType"] == "Library"


def test_no_fallback_when_first_attempt_succeeds(tmp_path, monkeypatch):
    _set_chat_env(monkeypatch, tmp_path)
    parent = tmp_path / "out"
    calls: list[list[str]] = []

    def _runner(cmd, *args, **kwargs):
        calls.append(list(cmd))
        if "create-project" in cmd:
            target = parent / "Happy"
            target.mkdir(parents=True, exist_ok=True)
            (target / "project.json").write_text('{"name": "Happy"}')
            return _fake_proc(returncode=0, stdout="ok")
        return _fake_proc()

    with (
        patch.object(set_mod, "_find_uip_cli", return_value="uip"),
        patch.object(set_mod, "_resolve_studio_dir", return_value=None),
        patch.object(set_mod.subprocess, "run", side_effect=_runner),
    ):
        result = create_project.invoke(
            {
                "project_dir": str(parent),
                "project_name": "Happy",
                "auto_verify": False,
            }
        )

    assert result.startswith("[OK]"), result
    assert "created_via: studio" in result
    assert all("solution" not in c or "new" not in c for c in calls), calls


def test_fallback_succeeds_even_if_solution_new_fails(tmp_path, monkeypatch):
    """The fallback hand-builds project.json regardless of solution-new success."""
    _set_chat_env(monkeypatch, tmp_path)
    parent = tmp_path / "out"

    def _runner(cmd, *args, **kwargs):
        if "create-project" in cmd:
            return _fake_proc(
                returncode=1, stderr="Could not resolve Studio installation directory"
            )
        if "solution" in cmd and "new" in cmd:
            return _fake_proc(returncode=2, stderr="solution new failed")
        return _fake_proc()

    with (
        patch.object(set_mod, "_find_uip_cli", return_value="uip"),
        patch.object(set_mod, "_resolve_studio_dir", return_value=None),
        patch.object(set_mod.subprocess, "run", side_effect=_runner),
    ):
        result = create_project.invoke(
            {
                "project_dir": str(parent),
                "project_name": "Resilient",
                "auto_verify": False,
            }
        )

    assert result.startswith("[OK]"), result
    assert (parent / "Resilient" / "project.json").exists()
    assert (parent / "Resilient" / "Main.xaml").exists()
