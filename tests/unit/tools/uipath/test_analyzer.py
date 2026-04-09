"""Test UiPath Workflow Analyzer tool."""
from unittest.mock import patch, MagicMock
from uipath_claude.tools.uipath.analyzer import workflow_analyzer_tool


def test_workflow_analyzer_tool():
    """Test workflow analyzer tool execution."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="No errors found"
        )
        
        result = workflow_analyzer_tool.invoke({"project_path": "/test/project"})
        
        assert "No errors found" in result
        mock_run.assert_called_once()
