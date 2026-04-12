"""Test UiPath Workflow Analyzer tool."""
from unittest.mock import MagicMock, patch

from uipath_claude.tools.uipath.analyzer import workflow_analyzer_tool


def test_workflow_analyzer_tool():
    """Test workflow analyzer tool execution."""
    proc = MagicMock(returncode=0, stdout="No errors found", stderr="")
    with patch(
        "uipath_claude.tools.uipath.analyzer.check_cli_approval",
        return_value=(True, ""),
    ), patch(
        "uipath_claude.tools.uipath.analyzer.run_studio_package_analyze",
        return_value=proc,
    ) as mock_analyze:
        result = workflow_analyzer_tool.invoke({"project_path": "/test/project"})
        assert "No errors found" in result
        mock_analyze.assert_called_once()


def test_workflow_analyzer_tool_blocked_without_approval():
    with patch(
        "uipath_claude.tools.uipath.analyzer.check_cli_approval",
        return_value=(False, "approval required"),
    ), patch(
        "uipath_claude.tools.uipath.analyzer.run_studio_package_analyze"
    ) as mock_analyze:
        result = workflow_analyzer_tool.invoke({"project_path": "/test/project"})
        assert result == "approval required"
        mock_analyze.assert_not_called()
