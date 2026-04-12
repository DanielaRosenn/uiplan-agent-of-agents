"""Test UiPath CLI runner functions."""
from unittest.mock import MagicMock, patch
import json

from uipath_claude.tools.uipath.cli_runner import (
    run_uip_rpa_find_activities,
    run_uip_rpa_get_errors,
    run_uip_rpa_analyze,
)


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_run_uip_rpa_find_activities_success_found(mock_run):
    """Test find-activities when activity is found."""
    mock_proc = MagicMock(
        returncode=0,
        stdout=json.dumps({
            "Result": "Success",
            "Data": {
                "found": True,
            }
        }),
        stderr="",
    )
    mock_run.return_value = mock_proc
    
    result = run_uip_rpa_find_activities(query="ui:LogMessage")
    
    assert result["success"] is True
    assert result["found"] is True
    
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "find-activities" in call_args
    assert "--query" in call_args
    assert "ui:LogMessage" in call_args


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_run_uip_rpa_find_activities_success_not_found(mock_run):
    """Test find-activities when activity is not found."""
    mock_proc = MagicMock(
        returncode=0,
        stdout=json.dumps({
            "Result": "Success",
            "Data": {
                "found": False,
            }
        }),
        stderr="",
    )
    mock_run.return_value = mock_proc
    
    result = run_uip_rpa_find_activities(query="ui:FakeActivity")
    
    assert result["success"] is True
    assert result["found"] is False


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_run_uip_rpa_find_activities_empty_query(mock_run):
    """Test find-activities with empty query."""
    result = run_uip_rpa_find_activities(query="")
    
    assert result["success"] is True
    assert result["found"] is False
    mock_run.assert_not_called()


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_run_uip_rpa_find_activities_cli_not_found(mock_run):
    """Test find-activities when CLI is not installed."""
    mock_run.side_effect = FileNotFoundError()
    
    result = run_uip_rpa_find_activities(query="ui:LogMessage")
    
    assert result["success"] is False
    assert "uip CLI not found" in result["error"]
    assert result["found"] is False


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_run_uip_rpa_find_activities_timeout(mock_run):
    """Test find-activities timeout."""
    from subprocess import TimeoutExpired
    
    mock_run.side_effect = TimeoutExpired(cmd="uip", timeout=30)
    
    result = run_uip_rpa_find_activities(query="ui:LogMessage", timeout=30)
    
    assert result["success"] is False
    assert "timed out" in result["error"]
    assert result["found"] is False


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_run_uip_rpa_find_activities_command_error(mock_run):
    """Test find-activities when command returns error."""
    mock_proc = MagicMock(
        returncode=1,
        stdout=json.dumps({
            "Result": "Error",
            "Message": "Activity search failed",
        }),
        stderr="",
    )
    mock_run.return_value = mock_proc
    
    result = run_uip_rpa_find_activities(query="ui:LogMessage")
    
    assert result["success"] is False
    assert "Activity search failed" in result["error"]


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_run_uip_rpa_find_activities_invalid_json(mock_run):
    """Test find-activities with invalid JSON response."""
    mock_proc = MagicMock(
        returncode=0,
        stdout="not valid json",
        stderr="",
    )
    mock_run.return_value = mock_proc
    
    result = run_uip_rpa_find_activities(query="ui:LogMessage")
    
    assert result["success"] is False
    assert "error" in result
