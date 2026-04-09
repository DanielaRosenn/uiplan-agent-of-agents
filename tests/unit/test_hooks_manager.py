# tests/unit/test_hooks_manager.py
"""Tests for the hooks manager system."""

import pytest
from unittest.mock import patch, MagicMock

from agent.hooks.manager import HooksManager
from agent.hooks.config import HookConfig, HookEvent


class TestHooksManager:
    @pytest.fixture
    def manager(self):
        return HooksManager()
    
    def test_registers_hook(self, manager):
        """Can register a hook for an event."""
        config = HookConfig(
            event=HookEvent.SESSION_START,
            command="echo 'session started'",
        )
        manager.register(config)
        assert len(manager.hooks[HookEvent.SESSION_START]) == 1
    
    def test_runs_hooks_for_event(self, manager):
        """Runs registered hooks when event fires."""
        config = HookConfig(
            event=HookEvent.SESSION_START,
            command="echo 'test'",
        )
        manager.register(config)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.fire(HookEvent.SESSION_START, {})
            mock_run.assert_called_once()
    
    def test_pattern_matching_for_file_hooks(self, manager):
        """File hooks only run for matching patterns."""
        config = HookConfig(
            event=HookEvent.FILE_CHANGED,
            command="echo 'xaml changed'",
            pattern="*.xaml",
        )
        manager.register(config)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            # Should run for .xaml files
            manager.fire(HookEvent.FILE_CHANGED, {"file": "Main.xaml"})
            assert mock_run.call_count == 1
            
            # Should not run for .py files
            manager.fire(HookEvent.FILE_CHANGED, {"file": "test.py"})
            assert mock_run.call_count == 1  # Still 1, not called again


class TestHookConfig:
    """Tests for HookConfig dataclass."""
    
    def test_creates_config_with_defaults(self):
        """HookConfig has sensible defaults."""
        config = HookConfig(
            event=HookEvent.SESSION_START,
            command="echo test",
        )
        assert config.pattern is None
        assert config.timeout == 30
    
    def test_creates_config_with_all_fields(self):
        """HookConfig accepts all fields."""
        config = HookConfig(
            event=HookEvent.FILE_CHANGED,
            command="echo ${file}",
            pattern="*.py",
            timeout=60,
        )
        assert config.event == HookEvent.FILE_CHANGED
        assert config.command == "echo ${file}"
        assert config.pattern == "*.py"
        assert config.timeout == 60


class TestHookEvent:
    """Tests for HookEvent enum."""
    
    def test_all_events_defined(self):
        """All expected events are defined."""
        assert HookEvent.SESSION_START.value == "session_start"
        assert HookEvent.PRE_TOOL_USE.value == "pre_tool_use"
        assert HookEvent.POST_TOOL_USE.value == "post_tool_use"
        assert HookEvent.FILE_CHANGED.value == "file_changed"


class TestHooksManagerAdvanced:
    """Advanced tests for HooksManager."""
    
    @pytest.fixture
    def manager(self):
        return HooksManager()
    
    def test_multiple_hooks_same_event(self, manager):
        """Multiple hooks can be registered for the same event."""
        config1 = HookConfig(event=HookEvent.SESSION_START, command="echo 1")
        config2 = HookConfig(event=HookEvent.SESSION_START, command="echo 2")
        
        manager.register(config1)
        manager.register(config2)
        
        assert len(manager.hooks[HookEvent.SESSION_START]) == 2
    
    def test_fire_returns_results(self, manager):
        """Fire returns results for each executed hook."""
        config = HookConfig(
            event=HookEvent.SESSION_START,
            command="echo test",
        )
        manager.register(config)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="test\n",
                stderr="",
            )
            results = manager.fire(HookEvent.SESSION_START, {})
            
            assert len(results) == 1
            assert results[0]["success"] is True
            assert results[0]["returncode"] == 0
    
    def test_context_variable_expansion(self, manager):
        """Context variables are expanded in commands."""
        config = HookConfig(
            event=HookEvent.FILE_CHANGED,
            command="echo ${file}",
        )
        manager.register(config)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            manager.fire(HookEvent.FILE_CHANGED, {"file": "test.xaml"})
            
            call_args = mock_run.call_args
            assert "test.xaml" in call_args[0][0]
    
    def test_tool_pattern_matching(self, manager):
        """Tool hooks match against tool name patterns."""
        config = HookConfig(
            event=HookEvent.PRE_TOOL_USE,
            command="echo 'file tool'",
            pattern="file_*",
        )
        manager.register(config)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            # Should match file_read
            manager.fire(HookEvent.PRE_TOOL_USE, {"tool": "file_read"})
            assert mock_run.call_count == 1
            
            # Should not match shell
            manager.fire(HookEvent.PRE_TOOL_USE, {"tool": "shell"})
            assert mock_run.call_count == 1
    
    def test_timeout_handling(self, manager):
        """Hooks that timeout return error result."""
        import subprocess
        
        config = HookConfig(
            event=HookEvent.SESSION_START,
            command="sleep 100",
            timeout=1,
        )
        manager.register(config)
        
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="sleep 100", timeout=1)
            results = manager.fire(HookEvent.SESSION_START, {})
            
            assert len(results) == 1
            assert results[0]["success"] is False
            assert "timed out" in results[0]["error"]
    
    def test_no_hooks_returns_empty(self, manager):
        """Firing event with no hooks returns empty list."""
        results = manager.fire(HookEvent.SESSION_START, {})
        assert results == []
