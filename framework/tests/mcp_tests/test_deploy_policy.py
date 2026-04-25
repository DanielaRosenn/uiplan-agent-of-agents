from __future__ import annotations

from mcp_server.tools.workflow_tools import get_workflow_tools


def _tool(name: str):
    for tool in get_workflow_tools():
        if tool.name == name:
            return tool
    raise AssertionError(f"Tool {name!r} not registered")


def test_deploy_tool_description_requires_runbook_approval_and_nonprod_target():
    desc = _tool("uipath_workflow_deploy").description or ""

    assert "docs/ORCHESTRATOR_DEPLOYMENT.md" in desc
    assert "explicit human approval" in desc
    assert "personal workspace" in desc
    assert "Dev folder" in desc
    assert "never Production" in desc


def test_publish_tool_description_requires_runbook_approval_and_nonprod_target():
    desc = _tool("uipath_workflow_publish").description or ""

    assert "docs/ORCHESTRATOR_DEPLOYMENT.md" in desc
    assert "explicit human approval" in desc
    assert "personal workspace" in desc
    assert "Dev target" in desc
    assert "never Production" in desc
