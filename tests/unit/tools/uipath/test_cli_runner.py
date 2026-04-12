"""Test UiPath CLI runner functions."""
from unittest.mock import MagicMock, patch
import json

from uipath_claude.tools.uipath.cli_runner import (
    run_uip_rpa_find_activities,
    run_uip_rpa_get_errors,
    run_uip_rpa_analyze,
)


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_run_uip_rpa_find_activities_success(mock_run):
    """Test find-activities with successful result."""
    mock_proc = MagicMock(
        returncode=0,
        stdout=json.dumps({
            "Result": "Success",
            "Data": {
                "found": ["ui:LogMessage", "ui:WriteLine"],
                "not_found": ["ui:FakeActivity"],
            }
        }),
        stderr="",
    )
    mock_run.return_value = mock_proc
    
    result = run_uip_rpa_find_activities(
        activity_names=["ui:LogMessage", "ui:WriteLine", "ui:FakeActivity"],
        project_path="/test/project",
    )
    
    assert result["success"] is True
    assert "ui:LogMessage" in result["found"]
    assert "ui:WriteLine" in result["found"]
    assert "ui:FakeActivity" in result["not_found"]
    
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "find-activities" in call_args
    assert "--activity-names" in call_args
    assert "--project-dir" in call_args


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_run_uip_rpa_find_activities_empty_list(mock_run):
    """Test find-activities with empty activity list."""
    result = run_uip_rpa_find_activities(
        activity_names=[],
        project_path="/test/project",
    )
    
    assert result["success"] is True
    assert result["found"] == []
    assert result["not_found"] == []
    mock_run.assert_not_called()


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_run_uip_rpa_find_activities_cli_not_found(mock_run):
    """Test find-activities when CLI is not installed."""
    mock_run.side_effect = FileNotFoundError()
    
    result = run_uip_rpa_find_activities(
        activity_names=["ui:LogMessage"],
        project_path="/test/project",
    )
    
    assert result["success"] is False
    assert "uip CLI not found" in result["error"]
    assert result["not_found"] == ["ui:LogMessage"]


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_run_uip_rpa_find_activities_timeout(mock_run):
    """Test find-activities timeout."""
    from subprocess import TimeoutExpired
    
    mock_run.side_effect = TimeoutExpired(cmd="uip", timeout=60)
    
    result = run_uip_rpa_find_activities(
        activity_names=["ui:LogMessage"],
        project_path="/test/project",
        timeout=60,
    )
    
    assert result["success"] is False
    assert "timed out" in result["error"]
    assert result["not_found"] == ["ui:LogMessage"]


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_run_uip_rpa_find_activities_command_error(mock_run):
    """Test find-activities when command returns error."""
    mock_proc = MagicMock(
        returncode=1,
        stdout=json.dumps({
            "Result": "Error",
            "Message": "Project not found",
        }),
        stderr="",
    )
    mock_run.return_value = mock_proc
    
    result = run_uip_rpa_find_activities(
        activity_names=["ui:LogMessage"],
        project_path="/test/project",
    )
    
    assert result["success"] is False
    assert "Project not found" in result["error"]


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_run_uip_rpa_find_activities_invalid_json(mock_run):
    """Test find-activities with invalid JSON response."""
    mock_proc = MagicMock(
        returncode=0,
        stdout="not valid json",
        stderr="",
    )
    mock_run.return_value = mock_proc
    
    result = run_uip_rpa_find_activities(
        activity_names=["ui:LogMessage"],
        project_path="/test/project",
    )
    
    assert result["success"] is False
    assert "error" in result
