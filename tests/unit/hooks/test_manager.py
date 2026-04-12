"""Test hook manager."""
import subprocess
from unittest.mock import patch, MagicMock
from uipath_claude.hooks.manager import HookManager


def test_hook_manager_run_hooks():
    """Test running hooks for an event."""
    manager = HookManager(hooks_config={
        "session_start": ["echo 'test'"]
    })
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        manager.run_hooks("session_start")
        
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "echo 'test'" in call_args[0][0]


def test_hook_manager_no_hooks():
    """Test running hooks when event has no hooks."""
    manager = HookManager(hooks_config={})
    
    with patch("subprocess.run") as mock_run:
        manager.run_hooks("session_start")
        mock_run.assert_not_called()
