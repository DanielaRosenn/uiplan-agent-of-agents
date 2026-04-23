"""Tests for uipath_workflow_create_project post-create validation (fix #3)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from uipath_claude.tools import skill_execution_tools as set_mod
from uipath_claude.tools.skill_execution_tools import create_project


def _fake_proc(returncode: int = 0, stdout: str = "ok", stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def test_create_project_falls_back_when_cli_succeeds_but_no_project_json(tmp_path, monkeypatch):
    """uip 0.1.21+: missing project.json after success triggers CLI-only fallback."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path / "chat"))
    monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")

    with (
        patch.object(set_mod, "_find_uip_cli", return_value="uip"),
        patch.object(set_mod, "_resolve_studio_dir", return_value=None),
        patch.object(set_mod.subprocess, "run", return_value=_fake_proc()),
    ):
        result = create_project.invoke(
            {
                "project_dir": str(tmp_path / "out"),
                "project_name": "Empty",
                "auto_verify": False,
            }
        )
    assert result.startswith("[OK]"), result
    assert "created_via: cli-fallback" in result
    assert (tmp_path / "out" / "Empty" / "project.json").exists()


def test_create_project_succeeds_when_project_json_written(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path / "chat"))
    monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")

    parent = tmp_path / "out"

    def _fake_run(cmd, *args, **kwargs):
        target = parent / "Real"
        target.mkdir(parents=True, exist_ok=True)
        (target / "project.json").write_text("{\"name\": \"Real\"}")
        return _fake_proc()

    with (
        patch.object(set_mod, "_find_uip_cli", return_value="uip"),
        patch.object(set_mod, "_resolve_studio_dir", return_value=None),
        patch.object(set_mod.subprocess, "run", side_effect=_fake_run),
    ):
        result = create_project.invoke(
            {
                "project_dir": str(parent),
                "project_name": "Real",
                "auto_verify": False,
            }
        )
    assert result.startswith("[OK]"), result
    assert (parent / "Real" / "project.json").exists()


def test_create_project_timeout_env_override(tmp_path, monkeypatch):
    """UIPATH_CREATE_PROJECT_TIMEOUT changes the subprocess timeout argument."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path / "chat"))
    monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
    monkeypatch.setenv("UIPATH_CREATE_PROJECT_TIMEOUT", "777")

    captured = {}

    def _fake_run(cmd, *args, **kwargs):
        if "create-project" in cmd:
            captured["timeout"] = kwargs.get("timeout")
        return _fake_proc()

    with (
        patch.object(set_mod, "_find_uip_cli", return_value="uip"),
        patch.object(set_mod, "_resolve_studio_dir", return_value=None),
        patch.object(set_mod.subprocess, "run", side_effect=_fake_run),
    ):
        create_project.invoke(
            {
                "project_dir": str(tmp_path / "out"),
                "project_name": "Whatever",
                "auto_verify": False,
            }
        )
    assert captured["timeout"] == 777
