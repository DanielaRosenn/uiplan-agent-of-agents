"""Tests for agentic tool success inference."""
from uipath_claude.query.agentic_executor import _tool_return_indicates_success


def test_zero_errors_validation_passed_is_success():
    assert _tool_return_indicates_success("Validation passed: 0 errors")


def test_real_error_is_failure():
    assert not _tool_return_indicates_success("Error: Workflow file not found: /tmp/x")


def test_failed_in_text_is_failure():
    assert not _tool_return_indicates_success("RUNTIME EXECUTION: FAILED\n\nbad")


def test_read_file_style_is_success():
    assert _tool_return_indicates_success("Contents of Main.xaml")
