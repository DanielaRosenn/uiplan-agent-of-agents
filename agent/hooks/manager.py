"""Hooks manager for executing event-driven commands."""

import fnmatch
import subprocess
from collections import defaultdict
from typing import Any

from agent.hooks.config import HookConfig, HookEvent


class HooksManager:
    """
    Manages and executes hooks for various events.

    Similar to Claude Code's hooks system.
    """

    def __init__(self):
        self.hooks: dict[HookEvent, list[HookConfig]] = defaultdict(list)

    def register(self, config: HookConfig) -> None:
        """Register a hook configuration."""
        self.hooks[config.event].append(config)

    def fire(self, event: HookEvent, context: dict[str, Any]) -> list[dict]:
        """
        Fire all hooks for an event.

        Args:
            event: The event type
            context: Context data (file paths, tool names, etc.)

        Returns:
            List of results for each hook
        """
        results = []

        for hook in self.hooks[event]:
            if not self._matches_pattern(hook, context):
                continue

            result = self._execute_hook(hook, context)
            results.append(result)

        return results

    def _matches_pattern(self, hook: HookConfig, context: dict) -> bool:
        """Check if hook pattern matches context."""
        if not hook.pattern:
            return True

        if hook.event == HookEvent.FILE_CHANGED:
            file_path = context.get("file", "")
            return fnmatch.fnmatch(file_path, hook.pattern)

        if hook.event in (HookEvent.PRE_TOOL_USE, HookEvent.POST_TOOL_USE):
            tool_name = context.get("tool", "")
            return fnmatch.fnmatch(tool_name, hook.pattern)

        return True

    def _execute_hook(self, hook: HookConfig, context: dict) -> dict:
        """Execute a single hook command."""
        try:
            command = hook.command
            for key, value in context.items():
                command = command.replace(f"${{{key}}}", str(value))

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=hook.timeout,
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Hook timed out after {hook.timeout}s",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
