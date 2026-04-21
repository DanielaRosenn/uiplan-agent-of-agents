"""MCP design gate tools (isolated store file)."""
from __future__ import annotations

import json

import pytest

from mcp_server.tools.design_tools import call_design_tool, get_design_tools


@pytest.fixture
def design_store_path(tmp_path, monkeypatch):
    p = tmp_path / "design_proposals.json"
    monkeypatch.setenv("UIPATH_DESIGN_STORE_PATH", str(p))
    yield p


def test_design_registry():
    names = {t.name for t in get_design_tools()}
    assert names == {
        "uipath_design_propose",
        "uipath_design_approve",
        "uipath_design_reject",
        "uipath_design_list",
        "uipath_design_status",
    }


@pytest.mark.asyncio
async def test_unknown_raises():
    with pytest.raises(ValueError, match="Unknown design tool"):
        await call_design_tool("uipath_design_nope", {})


@pytest.mark.asyncio
async def test_propose_list_status_approve_lifecycle(design_store_path, tmp_path):
    proj = str(tmp_path / "myproj")
    out = await call_design_tool(
        "uipath_design_propose",
        {
            "project_dir": proj,
            "title": "T",
            "summary": "Short sum",
            "body": "Long body",
            "rationale": "because",
            "citations": ["uipath-docs/foo"],
            "resolutions": {"project_type": "process"},
        },
    )
    assert "[STAGED]" in str(out)
    assert "design_id=" in str(out)

    listed = await call_design_tool("uipath_design_list", {"project_dir": proj})
    assert isinstance(listed, str)
    data = json.loads(listed)
    assert len(data) >= 1
    design_id = data[0]["design_id"]

    status_raw = await call_design_tool(
        "uipath_design_status", {"project_dir": proj}
    )
    snap = json.loads(str(status_raw))
    assert snap["project_dir"]
    assert snap.get("latest_pending") is not None

    approved = await call_design_tool(
        "uipath_design_approve",
        {"design_id": design_id, "note": "ok", "actor": "test"},
    )
    assert "[OK] approved" in str(approved)

    snap2 = json.loads(
        await call_design_tool("uipath_design_status", {"project_dir": proj})
    )
    assert snap2.get("has_approved_design") is True


@pytest.mark.asyncio
async def test_reject_unknown_id_returns_err(design_store_path):
    out = await call_design_tool(
        "uipath_design_reject",
        {"design_id": "no-such-id", "note": "nope"},
    )
    assert "[ERR]" in str(out)


@pytest.mark.asyncio
async def test_reject_pending(design_store_path, tmp_path):
    proj = str(tmp_path / "p2")
    await call_design_tool(
        "uipath_design_propose",
        {
            "project_dir": proj,
            "title": "x",
            "summary": "s",
            "body": "b",
        },
    )
    listed = await call_design_tool("uipath_design_list", {"project_dir": proj})
    data = json.loads(str(listed))
    did = data[0]["design_id"]
    rej = await call_design_tool(
        "uipath_design_reject", {"design_id": did, "note": "changed mind"}
    )
    assert "[OK] rejected" in str(rej)


@pytest.mark.asyncio
async def test_status_requires_project_dir():
    with pytest.raises(KeyError):
        await call_design_tool("uipath_design_status", {})
