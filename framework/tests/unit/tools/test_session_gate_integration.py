"""Integration tests for write_file -> session_gate keying (fixes #1, #4)."""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

import pytest

from mcp_server.tools import workflow_tools
from uipath_claude.tools import session_gate


@pytest.fixture(autouse=True)
def _reset_gate(monkeypatch):
    """Reset the in-process gate state before each test and disable design-gate."""
    session_gate.reset()
    monkeypatch.setenv("UIPATH_MCP_GATE_ENABLED", "1")
    monkeypatch.setenv("UIPATH_DESIGN_APPROVAL_ENABLED", "0")
    yield
    session_gate.reset()


def _make_project(tmp_path: Path) -> Path:
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "project.json").write_text("{\"name\": \"proj\"}")
    return proj


def _call(name: str, args: dict) -> object:
    return asyncio.run(workflow_tools.call_workflow_tool(name, args))


def test_write_file_marks_owning_project_dirty_via_absolute_path(tmp_path, monkeypatch):
    proj = _make_project(tmp_path)
    monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path / "chat"))
    monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
    monkeypatch.chdir(tmp_path)

    target = proj / "Helper.cs"
    result = _call(
        "uipath_workflow_write_file",
        {"file_path": str(target), "content": "// helper"},
    )
    assert isinstance(result, str) and result.startswith("[OK]"), result

    state = session_gate.status(str(proj))
    assert state.status == "dirty", state.status


def test_session_status_detects_out_of_band_edit(tmp_path, monkeypatch):
    proj = _make_project(tmp_path)
    monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path / "chat"))
    monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
    monkeypatch.chdir(tmp_path)

    main = proj / "Main.xaml"
    main.write_text("<a/>")
    session_gate.mark_verified(str(proj))
    assert session_gate.status(str(proj)).status == "verified"

    time.sleep(1.2)
    main.write_text("<b/>")
    new_mtime = time.time() + 5
    os.utime(main, (new_mtime, new_mtime))

    payload = _call("uipath_workflow_session_status", {"project_dir": str(proj)})
    assert isinstance(payload, str)
    data = json.loads(payload)
    assert data["status"] == "dirty", data
