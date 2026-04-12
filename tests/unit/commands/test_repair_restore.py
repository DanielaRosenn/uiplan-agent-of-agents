"""Test repair-restore command."""

from uipath_claude.commands.registry import CommandRegistry
from uipath_claude.commands.repair_restore import register_repair_restore_command


def test_repair_restore_command_shows_steps():
    registry = CommandRegistry()
    register_repair_restore_command(registry)
    out = registry.execute("repair-restore")
    assert "restore repair checklist" in out.lower()
    assert "close uipath studio" in out.lower()
    assert ".nuget/packages" in out.lower()
