"""Tests for write_file path resolution (smoke-driven defect fix #1)."""
from __future__ import annotations

from pathlib import Path

import pytest

from uipath_claude.tools import skill_execution_tools as set_mod
from uipath_claude.tools.skill_execution_tools import (
    resolve_write_destination,
    write_file,
)


@pytest.fixture
def chat_output(tmp_path, monkeypatch):
    """Make tmp_path the chat output root with no session id and a non-project CWD."""
    cwd = tmp_path / "cwd_no_project"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path / "chat"))
    monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
    return tmp_path


def test_absolute_path_inside_chat_output_accepted(chat_output, monkeypatch):
    target = chat_output / "chat" / "notes.md"
    monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
    resolved = resolve_write_destination(str(target))
    assert resolved is not None
    assert resolved == target.resolve()


def test_absolute_path_outside_allowed_root_rejected(tmp_path, monkeypatch):
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path / "chat"))
    monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")

    foreign = tmp_path / "elsewhere" / "leak.md"
    foreign.parent.mkdir(parents=True)
    assert resolve_write_destination(str(foreign)) is None


def test_absolute_path_with_project_json_ancestor_accepted(tmp_path, monkeypatch):
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path / "chat"))
    monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")

    proj = tmp_path / "elsewhere" / "MyProj"
    proj.mkdir(parents=True)
    (proj / "project.json").write_text("{}")
    target = proj / "Main.xaml"
    resolved = resolve_write_destination(str(target))
    assert resolved is not None
    assert resolved == target.resolve()


def test_relative_path_resolves_to_existing_project(tmp_path, monkeypatch):
    """Relative path resolves into the chat output / session dir."""
    monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path / "chat"))
    monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "session-1")
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    session_dir = tmp_path / "chat" / "session-1"
    session_dir.mkdir(parents=True)
    resolved = resolve_write_destination("workspace/notes.md")
    assert resolved is not None
    assert str(resolved).startswith(str(session_dir.resolve()))


def test_relative_path_rejects_traversal(chat_output):
    assert resolve_write_destination("../escape.md") is None


def test_write_file_accepts_absolute_path_under_chat_output(tmp_path, monkeypatch):
    monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path / "chat"))
    monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    target = tmp_path / "chat" / "notes.md"
    result = write_file.invoke({"file_path": str(target), "content": "hi"})
    assert result.startswith("[OK]"), result
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "hi"


def test_write_file_rejects_absolute_path_outside_root(tmp_path, monkeypatch):
    monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path / "chat"))
    monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    foreign = tmp_path / "elsewhere" / "leak.md"
    result = write_file.invoke({"file_path": str(foreign), "content": "nope"})
    assert "Invalid file path" in result
    assert not foreign.exists()
