"""Test recall command Rich Table output."""
from uipath_claude.commands.recall import register_recall_command
from uipath_claude.commands.registry import CommandRegistry


def test_recall_output_contains_table_structure():
    """Output should contain table-like formatting."""
    registry = CommandRegistry()
    history = [
        {"role": "user", "content": "build invoice workflow"},
        {"role": "assistant", "content": "I will create an invoice workflow"},
    ]
    register_recall_command(registry, get_history=lambda: history)

    result = registry.execute("recall", "invoice")
    # Rich Table output contains box-drawing characters
    assert "│" in result or "Role" in result
