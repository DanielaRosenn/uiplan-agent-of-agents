"""Test hook manager."""
from unittest.mock import MagicMock, patch

from uipath_claude.hooks.manager import HookManager


def test_hook_manager_run_hooks():
    """Test running hooks for an event."""
    manager = HookManager(hooks_config={
        "session_start": ["echo 'test'"]
    })
    
    with patch("uipath_claude.hooks.manager.run_command") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        manager.run_hooks("session_start")

        mock_run.assert_called_once_with(
            "echo 'test'", timeout=30, allow_shell_fallback=True
        )


def test_hook_manager_no_hooks():
    """Test running hooks when event has no hooks."""
    manager = HookManager(hooks_config={})
    
    with patch("uipath_claude.hooks.manager.run_command") as mock_run:
        manager.run_hooks("session_start")
        mock_run.assert_not_called()
