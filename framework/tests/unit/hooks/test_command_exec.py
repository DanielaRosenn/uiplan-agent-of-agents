"""Tests for safe hook command execution helpers."""

import pytest
from unittest.mock import MagicMock

from uipath_claude.hooks.command_exec import parse_command, run_command


def test_parse_command_shell_string_to_argv():
    """Parses shell-like string commands into argv."""
    assert parse_command("python -m pytest -q") == ["python", "-m", "pytest", "-q"]


def test_parse_command_preserves_quoted_path_as_single_arg():
    """Parses quoted paths without retaining quote characters."""
    assert parse_command('bash "C:/Program Files/uip/hook.sh"') == [
        "bash",
        "C:/Program Files/uip/hook.sh",
    ]


def test_parse_command_preserves_windows_backslashes():
    """Preserves backslashes in unquoted Windows paths."""
    assert parse_command(r"python C:\Users\foo\bar.py") == [
        "python",
        r"C:\Users\foo\bar.py",
    ]


def test_parse_command_rejects_empty_command():
    """Rejects empty command strings."""
    with pytest.raises(ValueError, match="empty command"):
        parse_command("   ")


def test_run_command_rejects_empty_sequence():
    """Rejects empty sequence commands."""
    with pytest.raises(ValueError, match="empty command"):
        run_command([])


def test_run_command_uses_argv_shell_false_by_default(monkeypatch):
    """Runs standard command via argv with shell disabled."""
    call_args = {}

    def fake_run(command, **kwargs):
        call_args["command"] = command
        call_args["kwargs"] = kwargs
        return MagicMock(returncode=0)

    monkeypatch.setattr("uipath_claude.hooks.command_exec.subprocess.run", fake_run)

    run_command("python -V")

    assert call_args["command"] == ["python", "-V"]
    assert call_args["kwargs"]["shell"] is False


def test_run_command_uses_shell_fallback_for_shell_syntax(monkeypatch):
    """Runs shell-style command string through shell when enabled."""
    call_args = {}

    def fake_run(command, **kwargs):
        call_args["command"] = command
        call_args["kwargs"] = kwargs
        return MagicMock(returncode=0)

    monkeypatch.setattr("uipath_claude.hooks.command_exec.subprocess.run", fake_run)

    run_command("echo hi && echo bye", allow_shell_fallback=True)

    assert call_args["command"] == "echo hi && echo bye"
    assert call_args["kwargs"]["shell"] is True
