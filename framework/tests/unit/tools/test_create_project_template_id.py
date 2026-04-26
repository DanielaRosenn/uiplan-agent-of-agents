"""Tests for create_project --template-id mapping and --studio-dir injection (uip 0.1.21+)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from uipath_claude.tools import skill_execution_tools as set_mod
from uipath_claude.tools.skill_execution_tools import create_project


def _fake_proc(returncode: int = 0, stdout: str = "ok", stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def _writes_project_json(parent, name):
    def _runner(cmd, *args, **kwargs):
        target = parent / name
        target.mkdir(parents=True, exist_ok=True)
        (target / "project.json").write_text('{"name": "' + name + '"}')
        return _fake_proc()

    return _runner


def _capture_cmd(captured):
    def _runner(cmd, *args, **kwargs):
        captured["cmd"] = list(cmd)
        return _fake_proc()

    return _runner


def _capture_then_run(captured, runner):
    def _runner(cmd, *args, **kwargs):
        captured.setdefault("cmd", list(cmd))
        return runner(cmd, *args, **kwargs)

    return _runner


def _set_chat_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path / "chat"))
    monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")


def test_process_uses_blank_template(tmp_path, monkeypatch):
    _set_chat_env(monkeypatch, tmp_path)
    parent = tmp_path / "out"
    captured: dict = {}

    runner = _writes_project_json(parent, "Proc")
    real_runner = _capture_then_run(captured, runner)

    with (
        patch.object(set_mod, "_find_uip_cli", return_value="uip"),
        patch.object(set_mod, "_resolve_studio_dir", return_value=None),
        patch.object(set_mod.subprocess, "run", side_effect=real_runner),
    ):
        result = create_project.invoke(
            {
                "project_dir": str(parent),
                "project_name": "Proc",
                "project_type": "process",
                "auto_verify": False,
            }
        )

    assert result.startswith("[OK]"), result
    cmd = captured["cmd"]
    assert "--template-id" in cmd
    assert cmd[cmd.index("--template-id") + 1] == "BlankTemplate"
    assert "--type" not in cmd
    assert cmd[cmd.index("--expression-language") + 1] == "CSharp"
    assert cmd[cmd.index("--target-framework") + 1] == "Windows"


def test_library_uses_library_template(tmp_path, monkeypatch):
    _set_chat_env(monkeypatch, tmp_path)
    parent = tmp_path / "out"
    captured: dict = {}

    runner = _writes_project_json(parent, "Lib")
    real_runner = _capture_then_run(captured, runner)

    with (
        patch.object(set_mod, "_find_uip_cli", return_value="uip"),
        patch.object(set_mod, "_resolve_studio_dir", return_value=None),
        patch.object(set_mod.subprocess, "run", side_effect=real_runner),
    ):
        create_project.invoke(
            {
                "project_dir": str(parent),
                "project_name": "Lib",
                "project_type": "library",
                "auto_verify": False,
            }
        )

    cmd = captured["cmd"]
    assert cmd[cmd.index("--template-id") + 1] == "LibraryProcessTemplate"


def test_coded_uses_blank_template_and_csharp(tmp_path, monkeypatch):
    _set_chat_env(monkeypatch, tmp_path)
    parent = tmp_path / "out"
    captured: dict = {}

    runner = _writes_project_json(parent, "Coded")
    real_runner = _capture_then_run(captured, runner)

    with (
        patch.object(set_mod, "_find_uip_cli", return_value="uip"),
        patch.object(set_mod, "_resolve_studio_dir", return_value=None),
        patch.object(set_mod.subprocess, "run", side_effect=real_runner),
    ):
        create_project.invoke(
            {
                "project_dir": str(parent),
                "project_name": "Coded",
                "project_type": "coded",
                "auto_verify": False,
            }
        )

    cmd = captured["cmd"]
    assert cmd[cmd.index("--template-id") + 1] == "BlankTemplate"
    assert "--expression-language" in cmd
    assert cmd[cmd.index("--expression-language") + 1] == "CSharp"


def test_studio_dir_injected_before_subcommand_when_resolved(tmp_path, monkeypatch):
    _set_chat_env(monkeypatch, tmp_path)
    parent = tmp_path / "out"
    studio = tmp_path / "fake-studio"
    studio.mkdir()
    captured: dict = {}

    runner = _writes_project_json(parent, "Proj")
    real_runner = _capture_then_run(captured, runner)

    with (
        patch.object(set_mod, "_find_uip_cli", return_value="uip"),
        patch.object(set_mod, "_resolve_studio_dir", return_value=str(studio)),
        patch.object(set_mod.subprocess, "run", side_effect=real_runner),
    ):
        create_project.invoke(
            {
                "project_dir": str(parent),
                "project_name": "Proj",
                "auto_verify": False,
            }
        )

    cmd = captured["cmd"]
    rpa_idx = cmd.index("rpa")
    sd_idx = cmd.index("--studio-dir")
    cp_idx = cmd.index("create-project")
    assert rpa_idx < sd_idx < cp_idx, f"order wrong: {cmd}"
    assert cmd[sd_idx + 1] == str(studio)


def test_studio_dir_omitted_when_none_resolved(tmp_path, monkeypatch):
    _set_chat_env(monkeypatch, tmp_path)
    parent = tmp_path / "out"
    captured: dict = {}

    runner = _writes_project_json(parent, "Proj")
    real_runner = _capture_then_run(captured, runner)

    with (
        patch.object(set_mod, "_find_uip_cli", return_value="uip"),
        patch.object(set_mod, "_resolve_studio_dir", return_value=None),
        patch.object(set_mod.subprocess, "run", side_effect=real_runner),
    ):
        create_project.invoke(
            {
                "project_dir": str(parent),
                "project_name": "Proj",
                "auto_verify": False,
            }
        )

    assert "--studio-dir" not in captured["cmd"]


def test_resolve_studio_dir_prefers_env(tmp_path, monkeypatch):
    studio = tmp_path / "custom-studio"
    studio.mkdir()
    monkeypatch.setenv("UIPATH_STUDIO_DIR", str(studio))
    assert set_mod._resolve_studio_dir() == str(studio)


def test_resolve_studio_dir_returns_none_for_missing_env(tmp_path, monkeypatch):
    monkeypatch.setenv("UIPATH_STUDIO_DIR", str(tmp_path / "does-not-exist"))
    # Force non-Windows branch so well-known paths aren't probed.
    monkeypatch.setattr(set_mod.os, "name", "posix")
    assert set_mod._resolve_studio_dir() is None
