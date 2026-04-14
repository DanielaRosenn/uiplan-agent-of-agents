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
    mock_proc.stderr = ""
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
    mock_proc.stderr = ""
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
    mock_proc.stderr = ""
    mock_proc.returncode = 0
    mock_run.return_value = mock_proc
    
    result = run_uip_rpa_find_activities("LogMessage")
    
    assert result["success"] is False
    assert len(result["activities"]) == 0


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_find_activities_parses_json_with_telemetry_prefix(mock_run):
    """Test parser handles telemetry prefix before JSON payload."""
    payload = {
        "Result": "Success",
        "Data": {
            "Activities": [{"ClassName": "UiPath.Core.Activities.LogMessage", "ActivityTypeId": "LogMessage"}]
        },
    }
    mock_proc = MagicMock()
    mock_proc.stdout = (
        "[Telemetry Request] Completed: ProjectPackager.Validate (1.85ms)\n"
        + json.dumps(payload)
    )
    mock_proc.stderr = ""
    mock_proc.returncode = 0
    mock_run.return_value = mock_proc

    result = run_uip_rpa_find_activities("LogMessage")

    assert result["success"] is True
    assert len(result["activities"]) == 1


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_get_errors_parses_json_from_stderr(mock_run):
    """Test get-errors parsing when JSON is emitted on stderr."""
    payload = {"Result": "Success", "Data": {"message": "No diagnostics found."}}
    mock_proc = MagicMock()
    mock_proc.stdout = ""
    mock_proc.stderr = "[Telemetry] noisy line\n" + json.dumps(payload)
    mock_proc.returncode = 0
    mock_run.return_value = mock_proc

    result = run_uip_rpa_get_errors("C:/tmp/project")

    assert result["success"] is True
    assert result["errors"] == []
    cmd = mock_run.call_args[0][0]
    assert "--use-studio" in cmd


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
@patch("uipath_claude.tools.uipath.cli_runner.run_uip_rpa_get_errors")
def test_analyze_falls_back_when_missing_project_message_on_stderr(
    mock_get_errors, mock_run
):
    """Test analyze fallback path when message is in stderr JSON."""
    payload = {
        "Result": "Analyze failed",
        "Message": "Project validate failed: No project.uiproj or webAppManifest.json found in directory: C:/tmp/x",
    }
    mock_proc = MagicMock()
    mock_proc.stdout = ""
    mock_proc.stderr = "[Telemetry Request] Completed\n" + json.dumps(payload)
    mock_proc.returncode = 1
    mock_run.return_value = mock_proc
    mock_get_errors.return_value = {"success": True, "errors": [], "raw_output": "{}"}

    result = run_uip_rpa_analyze("C:/tmp/x")

    assert result["success"] is True
    mock_get_errors.assert_called_once()
