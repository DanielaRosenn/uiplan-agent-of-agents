# tests/unit/test_branding.py
"""Tests for branding module."""

import pytest
from cli.branding import ROBOT_ASCII, print_welcome_banner, get_compact_logo


class TestBranding:
    def test_robot_logo_has_content(self):
        """Robot ASCII art is not empty."""
        assert ROBOT_ASCII is not None
        assert len(ROBOT_ASCII) > 0
        assert "o" in ROBOT_ASCII  # Eyes

    def test_welcome_banner_includes_version(self, capsys):
        """Banner includes version number."""
        print_welcome_banner(
            version="0.1.0",
            cwd="/path/to/project",
            model="claude-3-5-sonnet",
            project_name=None,
        )
        captured = capsys.readouterr()
        assert "0.1.0" in captured.out

    def test_welcome_banner_includes_project_name(self, capsys):
        """Banner shows detected UiPath project name."""
        print_welcome_banner(
            version="0.1.0",
            cwd="/path/to/project",
            model="claude-3-5-sonnet",
            project_name="MyRPAProject",
        )
        captured = capsys.readouterr()
        assert "MyRPAProject" in captured.out

    def test_compact_logo_for_narrow_terminal(self):
        """Uses compact logo when terminal is narrow."""
        compact = get_compact_logo()
        assert len(compact) < len(ROBOT_ASCII)
