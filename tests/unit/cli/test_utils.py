"""Test CLI utilities."""
from uipath_claude.cli.utils import parse_slash_command


def test_parse_slash_command():
    """Test parsing slash commands."""
    cmd, args = parse_slash_command("/help")
    assert cmd == "help"
    assert args == []


def test_parse_slash_command_with_args():
    """Test parsing slash commands with arguments."""
    cmd, args = parse_slash_command("/analyze /path/to/project")
    assert cmd == "analyze"
    assert args == ["/path/to/project"]


def test_parse_slash_command_not_command():
    """Test parsing non-command input."""
    cmd, args = parse_slash_command("regular message")
    assert cmd is None
    assert args == []
