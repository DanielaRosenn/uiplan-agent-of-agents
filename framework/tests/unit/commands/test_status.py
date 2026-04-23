"""Test status command."""

from uipath_claude.commands.registry import CommandRegistry
from uipath_claude.commands.status import register_status_command


def test_status_command_renders_session_details():
    """Test /status includes runtime details."""
    registry = CommandRegistry()
    register_status_command(
        registry,
        get_status=lambda: {
            "model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "region": "us-east-1",
            "project_detected": True,
            "project_name": "DemoProject",
            "memory_loaded": True,
            "skill_count": 42,
            "tool_profile": "safe",
        },
    )
    out = registry.execute("status")
    lines = out.splitlines()
    assert lines == [
        "Session status:",
        "- model: anthropic.claude-3-sonnet-20240229-v1:0",
        "- region: us-east-1",
        "- project_detected: True",
        "- project_name: DemoProject",
        "- memory_loaded: True",
        "- skill_count: 42",
        "- tool_profile: safe",
    ]

