"""Test UiPath Workflow Analyzer tool."""
from unittest.mock import MagicMock, patch

from uipath_claude.tools.uipath.analyzer import workflow_analyzer_tool


def test_workflow_analyzer_tool():
    """Test workflow analyzer tool execution."""
    proc = MagicMock(returncode=0, stdout="No errors found", stderr="")
    with patch(
        "uipath_claude.tools.uipath.analyzer.run_studio_package_analyze",
        return_value=proc,
    ) as mock_analyze:
        result = workflow_analyzer_tool.invoke({"project_path": "/test/project"})
        assert "No errors found" in result
        mock_analyze.assert_called_once()
