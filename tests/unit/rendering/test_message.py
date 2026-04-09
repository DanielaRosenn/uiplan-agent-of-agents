"""Test message rendering."""
from uipath_claude.rendering.message import render_message, MessageType


def test_render_user_message():
    """Test rendering user message."""
    output = render_message("Hello", MessageType.USER)
    assert "Hello" in output
    assert "User" in output or "user" in output


def test_render_assistant_message():
    """Test rendering assistant message."""
    output = render_message("Hi there", MessageType.ASSISTANT)
    assert "Hi there" in output


def test_render_system_message():
    """Test rendering system message."""
    output = render_message("System info", MessageType.SYSTEM)
    assert "System info" in output


def test_render_tool_result():
    """Test rendering tool result."""
    output = render_message("Tool output", MessageType.TOOL)
    assert "Tool output" in output
