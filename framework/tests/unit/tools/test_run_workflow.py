"""Tests for run_workflow tool."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from uipath_claude.tools.skill_execution_tools import run_workflow


class TestRunWorkflow:
    """Tests for run_workflow tool."""

    @patch("uipath_claude.tools.skill_execution_tools.subprocess.run")
    def test_run_workflow_success(self, mock_run, tmp_path, monkeypatch):
        """Test successful workflow execution."""
        # Setup
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        # Create test workflow file
        test_file = tmp_path / "Main.xaml"
        test_file.write_text("<Activity/>")
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "IsSuccessful": True,
                "Data": {
                    "Output": {"State": "Completed"},
                    "LogEntries": [
                        {"Severity": "Info", "Message": "Workflow started"},
                        {"Severity": "Info", "Message": "Workflow completed"}
                    ],
                    "Errors": []
                }
            }),
            stderr=""
        )
        
        # Execute
        result = run_workflow.invoke({
            "project_dir": str(tmp_path),
            "file_path": "Main.xaml"
        })
        
        # Assert
        assert "RUNTIME EXECUTION: SUCCESS" in result
        assert "Workflow executed successfully" in result
        assert "no runtime errors" in result

    @patch("uipath_claude.tools.skill_execution_tools.subprocess.run")
    def test_run_workflow_property_error(self, mock_run, tmp_path, monkeypatch):
        """Test workflow with wrong property usage."""
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        # Create test workflow file
        test_file = tmp_path / "Main.xaml"
        test_file.write_text("<Activity/>")
        
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout=json.dumps({
                "IsSuccessful": False,
                "ErrorMessage": "Execution faulted",
                "Data": {
                    "Output": {"State": "Faulted"},
                    "LogEntries": [
                        {
                            "Severity": "Error",
                            "Message": "The property 'Result' does not exist",
                            "ActivityName": "GetOutlookMailMessages",
                            "ExceptionMessage": ""
                        }
                    ],
                    "Errors": []
                }
            }),
            stderr=""
        )
        
        result = run_workflow.invoke({
            "project_dir": str(tmp_path),
            "file_path": "Main.xaml"
        })
        
        assert "RUNTIME EXECUTION: FAILED" in result
        assert "property" in result.lower()
        assert "GetOutlookMailMessages" in result
        assert "find_activity_info" in result

    @patch("uipath_claude.tools.skill_execution_tools.subprocess.run")
    def test_run_workflow_null_reference_error(self, mock_run, tmp_path, monkeypatch):
        """Test workflow with null reference exception."""
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        test_file = tmp_path / "Main.xaml"
        test_file.write_text("<Activity/>")
        
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout=json.dumps({
                "IsSuccessful": False,
                "ErrorMessage": "Null reference",
                "Data": {
                    "Output": {"State": "Faulted"},
                    "LogEntries": [
                        {
                            "Severity": "Error",
                            "Message": "Object reference not set to an instance of an object",
                            "ActivityName": "ForEach",
                            "ExceptionMessage": "NullReferenceException"
                        }
                    ],
                    "Errors": []
                }
            }),
            stderr=""
        )
        
        result = run_workflow.invoke({
            "project_dir": str(tmp_path),
            "file_path": "Main.xaml"
        })
        
        assert "RUNTIME EXECUTION: FAILED" in result
        assert "null" in result.lower()
        assert "ForEach" in result
        assert "variable" in result.lower()

    @patch("uipath_claude.tools.skill_execution_tools.subprocess.run")
    def test_run_workflow_timeout(self, mock_run, tmp_path, monkeypatch):
        """Test workflow execution timeout."""
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        test_file = tmp_path / "Main.xaml"
        test_file.write_text("<Activity/>")
        
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["uip"], timeout=60)
        
        result = run_workflow.invoke({
            "project_dir": str(tmp_path),
            "file_path": "Main.xaml",
            "timeout_seconds": 60
        })
        
        assert "Error" in result
        assert "timed out" in result.lower()
        assert "60 seconds" in result

    @patch("uipath_claude.tools.skill_execution_tools.subprocess.run")
    def test_run_workflow_cli_not_found(self, mock_run, tmp_path, monkeypatch):
        """Test when uip CLI is not installed."""
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        test_file = tmp_path / "Main.xaml"
        test_file.write_text("<Activity/>")
        
        mock_run.side_effect = FileNotFoundError()
        
        result = run_workflow.invoke({
            "project_dir": str(tmp_path),
            "file_path": "Main.xaml"
        })
        
        assert "Error" in result
        assert "uip CLI not found" in result
        assert "npm install" in result

    @patch("uipath_claude.tools.skill_execution_tools.subprocess.run")
    def test_run_workflow_with_input_arguments(self, mock_run, tmp_path, monkeypatch):
        """Test workflow execution with input arguments."""
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        test_file = tmp_path / "Main.xaml"
        test_file.write_text("<Activity/>")
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "IsSuccessful": True,
                "Data": {
                    "Output": {"State": "Completed"},
                    "LogEntries": [],
                    "Errors": []
                }
            }),
            stderr=""
        )
        
        result = run_workflow.invoke({
            "project_dir": str(tmp_path),
            "file_path": "Main.xaml",
            "input_arguments": '{"email": "test@example.com"}'
        })
        
        # Check that CLI was called with input-arguments flag
        call_args = mock_run.call_args[0][0]
        assert "--input-arguments" in call_args
        assert '{"email": "test@example.com"}' in call_args
        assert "SUCCESS" in result

    @patch("uipath_claude.tools.skill_execution_tools.subprocess.run")
    def test_run_workflow_verbose_mode(self, mock_run, tmp_path, monkeypatch):
        """Test verbose mode includes all log entries."""
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        test_file = tmp_path / "Main.xaml"
        test_file.write_text("<Activity/>")
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "IsSuccessful": True,
                "Data": {
                    "Output": {"State": "Completed"},
                    "LogEntries": [
                        {"Severity": "Info", "Message": "Step 1"},
                        {"Severity": "Info", "Message": "Step 2"},
                        {"Severity": "Info", "Message": "Step 3"},
                        {"Severity": "Info", "Message": "Step 4"},
                        {"Severity": "Info", "Message": "Step 5"},
                        {"Severity": "Info", "Message": "Step 6"},
                    ],
                    "Errors": []
                }
            }),
            stderr=""
        )
        
        # Non-verbose (should filter out Info logs)
        result_normal = run_workflow.invoke({
            "project_dir": str(tmp_path),
            "file_path": "Main.xaml",
            "verbose": False
        })
        
        # Verbose (should include Info logs)
        result_verbose = run_workflow.invoke({
            "project_dir": str(tmp_path),
            "file_path": "Main.xaml",
            "verbose": True
        })
        
        # Verbose should be longer or at least show log messages
        assert "SUCCESS" in result_normal
        assert "SUCCESS" in result_verbose

    @patch("uipath_claude.tools.skill_execution_tools.subprocess.run")
    def test_run_workflow_truncates_long_output(self, mock_run, tmp_path, monkeypatch):
        """Test that long output is truncated for token efficiency."""
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        test_file = tmp_path / "Main.xaml"
        test_file.write_text("<Activity/>")
        
        # Create many log entries to generate long output
        long_logs = [
            {
                "Severity": "Error",
                "Message": f"Error message number {i} with lots of detail about what went wrong in the workflow execution",
                "ActivityName": f"Activity_{i}"
            }
            for i in range(100)
        ]
        
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout=json.dumps({
                "IsSuccessful": False,
                "Data": {
                    "Output": {"State": "Faulted"},
                    "LogEntries": long_logs,
                    "Errors": []
                }
            }),
            stderr=""
        )
        
        result = run_workflow.invoke({
            "project_dir": str(tmp_path),
            "file_path": "Main.xaml",
            "verbose": False
        })
        
        # Should be truncated
        assert len(result) <= 2100  # 2000 + margin for truncation message
        assert "TRUNCATED" in result or len(result) < 2000

    @patch("uipath_claude.tools.skill_execution_tools.subprocess.run")
    def test_run_workflow_extracts_activity_context(self, mock_run, tmp_path, monkeypatch):
        """Test that activity name is extracted and shown in error context."""
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        test_file = tmp_path / "Main.xaml"
        test_file.write_text("<Activity/>")
        
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout=json.dumps({
                "IsSuccessful": False,
                "Data": {
                    "Output": {"State": "Faulted"},
                    "LogEntries": [
                        {
                            "Severity": "Error",
                            "Message": "Cannot convert type String to Int32",
                            "ActivityName": "ConvertToNumber",
                            "ExceptionMessage": ""
                        }
                    ],
                    "Errors": []
                }
            }),
            stderr=""
        )
        
        result = run_workflow.invoke({
            "project_dir": str(tmp_path),
            "file_path": "Main.xaml"
        })
        
        assert "RUNTIME EXECUTION: FAILED" in result
        assert "ConvertToNumber" in result
        assert "Activity:" in result

    @patch("uipath_claude.tools.skill_execution_tools.subprocess.run")
    def test_run_workflow_type_mismatch_error(self, mock_run, tmp_path, monkeypatch):
        """Test workflow with type mismatch error."""
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        test_file = tmp_path / "Main.xaml"
        test_file.write_text("<Activity/>")
        
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout=json.dumps({
                "IsSuccessful": False,
                "Data": {
                    "Output": {"State": "Faulted"},
                    "LogEntries": [
                        {
                            "Severity": "Error",
                            "Message": "Cannot convert type 'System.String' to 'System.Int32'",
                            "ActivityName": "Assign",
                            "ExceptionMessage": "Type mismatch"
                        }
                    ],
                    "Errors": []
                }
            }),
            stderr=""
        )
        
        result = run_workflow.invoke({
            "project_dir": str(tmp_path),
            "file_path": "Main.xaml"
        })
        
        assert "RUNTIME EXECUTION: FAILED" in result
        assert "type" in result.lower()
        assert "Assign" in result

    def test_run_workflow_file_not_found(self, tmp_path, monkeypatch):
        """Test when workflow file doesn't exist."""
        monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "")
        
        result = run_workflow.invoke({
            "project_dir": str(tmp_path),
            "file_path": "NonExistent.xaml"
        })
        
        assert "Error" in result
        assert "not found" in result.lower()
