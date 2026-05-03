"""Hook manager for event-driven command execution."""

from typing import Dict, List

from uipath_claude.hooks.command_exec import run_command


class HookManager:
    """Manages event hooks and executes commands."""
    
    def __init__(self, hooks_config: Dict[str, List[str]]):
        """
        Initialize hook manager.
        
        Args:
            hooks_config: Dictionary mapping event names to shell commands
        """
        self.hooks_config = hooks_config
    
    def run_hooks(self, event: str) -> None:
        """
        Run all hooks for the given event.
        
        Args:
            event: Event name (e.g., "session_start", "pre_tool_use")
        """
        commands = self.hooks_config.get(event, [])
        
        for cmd in commands:
            try:
                run_command(cmd, timeout=30, allow_shell_fallback=True)
            except Exception:
                # Silently ignore hook failures
                pass
