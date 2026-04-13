"""Tests for UiPath CLI runner functions."""
import pytest
from unittest.mock import patch, MagicMock
import json
from pathlib import Path

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


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_get_errors_parses_nested_error_messages(mock_run):
    """Parse nested get-errors payload into individual diagnostics."""
    mock_proc = MagicMock()
    mock_proc.stdout = json.dumps(
        {
            "Result": "Success",
            "Data": {
                "message": {
                    "message": "Errors\n- Main.xaml: Missing argument\n- Flow.xaml: Invalid type"
                }
            },
        }
    )
    mock_proc.returncode = 0
    mock_run.return_value = mock_proc

    result = run_uip_rpa_get_errors("C:/tmp/project")

    assert result["success"] is False
    assert result["diagnostics_ran"] is True
    assert result["errors"] == [
        "Main.xaml: Missing argument",
        "Flow.xaml: Invalid type",
    ]


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_get_errors_adds_file_path_argument(mock_run):
    """Run file-scoped diagnostics with --file-path when provided."""
    mock_proc = MagicMock()
    mock_proc.stdout = json.dumps(
        {"Result": "Success", "Data": {"message": "No diagnostics found"}}
    )
    mock_proc.returncode = 0
    mock_run.return_value = mock_proc

    run_uip_rpa_get_errors("C:/tmp/project", file_path=Path("C:/tmp/project/Main.xaml"))

    command = mock_run.call_args.args[0]
    assert "--file-path" in command
    assert str(Path("C:/tmp/project/Main.xaml").resolve()) in command


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_get_errors_marks_studio_unavailable(mock_run):
    """Surface interop/autopilot/dependency exceptions as Studio unavailable."""
    mock_proc = MagicMock()
    mock_proc.stdout = json.dumps(
        {
            "Result": "Failed",
            "Message": (
                "Autopilot.Interop.DependencyException: Could not load file or assembly"
            ),
        }
    )
    mock_proc.returncode = 1
    mock_run.return_value = mock_proc

    result = run_uip_rpa_get_errors("C:/tmp/project")

    assert result["success"] is False
    assert result["diagnostics_ran"] is False
    assert "UiPath Studio is unavailable" in result["errors"][0]
    assert "interop/autopilot/dependency exception" in result["errors"][0]


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_get_errors_errors_prefix_without_bullets_is_failure(mock_run):
    """Treat generic 'Errors...' payload without bullets as validation failure."""
    mock_proc = MagicMock()
    mock_proc.stdout = json.dumps(
        {
            "Result": "Success",
            "Data": {"message": "Errors while validating project metadata"},
        }
    )
    mock_proc.returncode = 0
    mock_run.return_value = mock_proc

    result = run_uip_rpa_get_errors("C:/tmp/project")

    assert result["success"] is False
    assert result["diagnostics_ran"] is True
    assert result["errors"] == ["Errors while validating project metadata"]
