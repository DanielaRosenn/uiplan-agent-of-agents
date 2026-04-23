"""Test help command."""
from uipath_claude.commands.registry import CommandRegistry
from uipath_claude.commands.help import register_help_command


def test_help_command():
    """Test help command lists all commands."""
    registry = CommandRegistry()
    register_help_command(registry)
    
    # Register a test command
    registry.register("test", "Test command", lambda: "test")
    
    result = registry.execute("help")
    
    assert "/help" in result
    assert "/test" in result
    assert "Test command" in result
