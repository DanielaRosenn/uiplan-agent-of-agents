"""Tests for UiPath CLI runner functions."""
import pytest
from unittest.mock import patch, MagicMock
import json

from uipath_claude.tools.uipath.cli_runner import (
    run_uip_rpa_find_activities,
    run_uip_rpa_get_errors,
    run_uip_rpa_analyze,
)


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_find_activities_success(mock_run):
    """Test successful activity search."""
    mock_result = {
        "Result": "Success",
        "Data": {
            "Activities": [
                {
                    "ClassName": "UiPath.Core.Activities.LogMessage",
                    "ActivityTypeId": "LogMessage",
                    "Description": "Writes a log message",
                }
            ]
        }
    }
    
    mock_proc = MagicMock()
    mock_proc.stdout = json.dumps(mock_result)
    mock_proc.returncode = 0
    mock_run.return_value = mock_proc
    
    result = run_uip_rpa_find_activities("LogMessage")
    
    assert result["success"] is True
    assert len(result["activities"]) == 1
    assert result["activities"][0]["ClassName"] == "UiPath.Core.Activities.LogMessage"


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_find_activities_not_found(mock_run):
    """Test activity not found."""
    mock_result = {
        "Result": "Success",
        "Data": {
            "Activities": []
        }
    }
    
    mock_proc = MagicMock()
    mock_proc.stdout = json.dumps(mock_result)
    mock_proc.returncode = 0
    mock_run.return_value = mock_proc
    
    result = run_uip_rpa_find_activities("FakeActivity")
    
    assert result["success"] is True
    assert len(result["activities"]) == 0


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_find_activities_cli_not_found(mock_run):
    """Test handling when CLI is not installed."""
    mock_run.side_effect = FileNotFoundError()
    
    result = run_uip_rpa_find_activities("LogMessage")
    
    assert result["success"] is False
    assert len(result["activities"]) == 0


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_find_activities_timeout(mock_run):
    """Test find-activities timeout."""
    from subprocess import TimeoutExpired
    
    mock_run.side_effect = TimeoutExpired(cmd="uip", timeout=30)
    
    result = run_uip_rpa_find_activities("LogMessage", timeout=30)
    
    assert result["success"] is False
    assert len(result["activities"]) == 0


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_find_activities_invalid_json(mock_run):
    """Test find-activities with invalid JSON response."""
    mock_proc = MagicMock()
    mock_proc.stdout = "not valid json"
    mock_proc.returncode = 0
    mock_run.return_value = mock_proc
    
    result = run_uip_rpa_find_activities("LogMessage")
    
    assert result["success"] is False
    assert len(result["activities"]) == 0
