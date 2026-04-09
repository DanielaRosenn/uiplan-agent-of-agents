"""Hook manager for event-driven shell command execution."""
import subprocess
from typing import Dict, List


class HookManager:
    """Manages event hooks and executes shell commands."""
    
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
                subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    timeout=30,
                )
            except Exception:
                # Silently ignore hook failures
                pass
