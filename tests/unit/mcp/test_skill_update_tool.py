"""Smoke test for the MCP skill update tools."""
from __future__ import annotations

from unittest.mock import patch

import pytest


def test_uipath_skill_check_updates_calls_check_for_updates() -> None:
    from mcp_server.tools import skill_tools

    with patch(
        "mcp_server.tools.skill_tools.check_for_updates",
        return_value=(True, "new", "aaaa", "bbbb"),
    ) as m:
        result = skill_tools.uipath_skill_check_updates()
    m.assert_called_once()
    assert result["has_updates"] is True
    assert result["current"] == "aaaa"
    assert result["remote"] == "bbbb"


def test_uipath_skill_update_calls_ensure_fresh() -> None:
    from mcp_server.tools import skill_tools

    with patch(
        "mcp_server.tools.skill_tools.ensure_fresh",
        return_value="updated: 2 files",
    ) as m:
        result = skill_tools.uipath_skill_update(force=False)
    m.assert_called_once()
    assert "updated" in result["status"]
