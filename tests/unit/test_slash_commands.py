# tests/unit/test_slash_commands.py
"""Tests for slash command registry and execution."""

import pytest

from cli.commands import parse_slash_command, execute_command, COMMANDS, register_command


class TestSlashCommandParsing:
    """Tests for slash command parsing."""

    def test_parses_slash_command(self):
        """Parses /command args format."""
        result = parse_slash_command("/help")
        assert result is not None
        assert result["command"] == "help"
        assert result["args"] == ""

    def test_parses_command_with_args(self):
        """Parses command with arguments."""
        result = parse_slash_command("/status verbose")
        assert result["command"] == "status"
        assert result["args"] == "verbose"

    def test_returns_none_for_non_command(self):
        """Returns None for regular text."""
        result = parse_slash_command("Hello world")
        assert result is None


class TestSlashCommandExecution:
    """Tests for slash command execution."""

    def test_help_command_lists_commands(self):
        """Help command shows available commands."""
        context = {}
        result = execute_command("help", "", context)
        assert "help" in result.lower()
        assert "status" in result.lower()

    def test_status_command_shows_info(self):
        """Status command shows session info."""
        context = {"session_id": "test-123", "model": "claude-3-5-sonnet"}
        result = execute_command("status", "", context)
        assert "test-123" in result or "session" in result.lower()
