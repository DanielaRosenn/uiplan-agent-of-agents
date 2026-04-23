"""Test command registry."""
from uipath_claude.commands.registry import CommandRegistry, register_command


def test_register_command():
    """Test registering a command."""
    registry = CommandRegistry()
    
    @register_command(registry, name="test", description="Test command")
    def test_command():
        return "test result"
    
    assert "test" in registry.commands
    assert registry.commands["test"]["description"] == "Test command"
    result = registry.execute("test")
    assert result == "test result"


def test_execute_nonexistent_command():
    """Test executing nonexistent command."""
    registry = CommandRegistry()
    result = registry.execute("nonexistent")
    assert "Unknown command" in result
