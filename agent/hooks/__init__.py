"""Hooks system for event-driven actions."""

from agent.hooks.config import HookConfig, HookEvent
from agent.hooks.manager import HooksManager

__all__ = ["HookConfig", "HookEvent", "HooksManager"]
