"""Test recall command."""

from uipath_claude.commands.recall import register_recall_command
from uipath_claude.commands.registry import CommandRegistry


def test_recall_command_is_registered():
    """Register /recall command in command registry."""
    registry = CommandRegistry()
    register_recall_command(registry, get_history=lambda: [])

    assert "recall" in registry.commands


def test_recall_command_requires_query():
    """Show usage when no query is provided."""
    registry = CommandRegistry()
    register_recall_command(registry, get_history=lambda: [])

    result = registry.execute("recall")
    assert result == "Usage: /recall <query>"


def test_recall_command_returns_no_match_message():
    """Show no-match message when nothing is found."""
    registry = CommandRegistry()
    history = [{"role": "user", "content": "build invoice process"}]
    register_recall_command(registry, get_history=lambda: history)

    result = registry.execute("recall", "desktop")
    assert result == "No matches found for: desktop"


def test_recall_command_formats_role_and_content():
    """Render matching messages with role and content."""
    registry = CommandRegistry()
    history = [
        {"role": "user", "content": "first invoice note"},
        {"role": "assistant", "content": "second invoice note"},
        {"role": "user", "content": "third invoice note"},
    ]
    register_recall_command(registry, get_history=lambda: history)

    result = registry.execute("recall", "invoice")
    assert result.splitlines() == [
        "Recent matches:",
        "- [user] third invoice note",
        "- [assistant] second invoice note",
        "- [user] first invoice note",
    ]
