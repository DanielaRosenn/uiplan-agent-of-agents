"""Real-CLI integration tests for uipath_workflow_create_project.

Opt-in: requires ``UIPATH_RUN_DEPLOY_TESTS=1`` and ``uip`` on PATH.
For ``project_type=process`` Studio must also be running locally because
``uip rpa create-project`` shells through Studio to materialise files.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import pytest

from mcp_server.tools import workflow_tools as wt
from uipath_claude.tools import design_store, session_gate


pytestmark = pytest.mark.skipif(
    os.environ.get("UIPATH_RUN_DEPLOY_TESTS") != "1" or shutil.which("uip") is None,
    reason="set UIPATH_RUN_DEPLOY_TESTS=1 and have `uip` on PATH to run these",
)


def _stamp() -> str:
    return time.strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex[:6]


def _reset_state(project_dir: Path) -> None:
    try:
        session_gate.reset(in_memory_only=True)
    except Exception:
        pass
    try:
        design_store.reset(in_memory_only=True)
    except Exception:
        pass


@pytest.mark.asyncio
async def test_real_create_process_project_writes_project_json(tmp_path: Path):
    name = f"PddSmokeProc{_stamp()}"
    _reset_state(tmp_path)

    result = await wt.call_workflow_tool(
        "uipath_workflow_create_project",
        {
            "project_dir": str(tmp_path),
            "project_name": name,
            "project_type": "process",
            "auto_verify": False,
        },
    )

    assert "[ERROR]" not in result, result
    project_json = tmp_path / name / "project.json"
    assert project_json.exists(), f"project.json not materialised at {project_json}; tool said: {result[:400]}"

    parsed = json.loads(project_json.read_text(encoding="utf-8"))
    assert parsed.get("name") == name


@pytest.mark.asyncio
async def test_real_create_library_project(tmp_path: Path):
    name = f"PddSmokeLib{_stamp()}"
    _reset_state(tmp_path)

    result = await wt.call_workflow_tool(
        "uipath_workflow_create_project",
        {
            "project_dir": str(tmp_path),
            "project_name": name,
            "project_type": "library",
            "auto_verify": False,
        },
    )
    assert "[ERROR]" not in result, result
    assert (tmp_path / name / "project.json").exists()


@pytest.mark.asyncio
async def test_real_create_then_design_gate_blocks_first_write(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("UIPATH_DESIGN_APPROVAL_ENABLED", "1")
    name = f"PddSmokeGate{_stamp()}"
    _reset_state(tmp_path)

    create = await wt.call_workflow_tool(
        "uipath_workflow_create_project",
        {
            "project_dir": str(tmp_path),
            "project_name": name,
            "project_type": "process",
            "auto_verify": False,
        },
    )
    assert "[ERROR]" not in create, create

    project_dir = tmp_path / name
    target = project_dir / "Sequences" / "Greet.xaml"

    blocked = await wt.call_workflow_tool(
        "uipath_workflow_write_file",
        {"file_path": str(target), "content": "<Activity/>"},
    )
    assert "[BLOCKED]" in blocked or "design" in blocked.lower(), blocked
