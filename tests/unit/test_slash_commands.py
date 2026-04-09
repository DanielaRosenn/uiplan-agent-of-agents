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


class TestSkillsCommand:
    """Tests for skills command."""

    def test_skills_command_registered(self):
        """Skills command is registered."""
        assert "skills" in COMMANDS
        assert COMMANDS["skills"].name == "skills"

    def test_skills_command_lists_skills(self, tmp_path):
        """Skills command shows available skills."""
        # Create mock skills directory structure
        skill1 = tmp_path / "skill-one"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("# Skill One")
        
        skill2 = tmp_path / "skill-two"
        skill2.mkdir()
        (skill2 / "SKILL.md").write_text("# Skill Two")
        
        context = {"skills_dir": str(tmp_path)}
        result = execute_command("skills", "", context)
        
        assert "Available Skills" in result
        assert "skill-one" in result
        assert "skill-two" in result

    def test_skills_command_no_dir_configured(self):
        """Skills command handles missing configuration."""
        context = {}
        result = execute_command("skills", "", context)
        assert "No skills directory configured" in result

    def test_skills_command_dir_not_found(self):
        """Skills command handles non-existent directory."""
        context = {"skills_dir": "/nonexistent/path"}
        result = execute_command("skills", "", context)
        assert "not found" in result.lower()

    def test_skills_command_no_skills_found(self, tmp_path):
        """Skills command handles empty skills directory."""
        context = {"skills_dir": str(tmp_path)}
        result = execute_command("skills", "", context)
        assert "No skills found" in result

    def test_skills_command_alias(self):
        """Skills command has sk alias."""
        assert "sk" in COMMANDS
        assert COMMANDS["sk"].name == "skills"


class TestAnalyzeCommand:
    """Tests for analyze command."""

    def test_analyze_command_registered(self):
        """Analyze command is registered."""
        assert "analyze" in COMMANDS

    def test_analyze_requires_project(self):
        """Analyze requires UiPath project context."""
        context = {}
        result = execute_command("analyze", "", context)
        assert "project" in result.lower() or "not found" in result.lower()
