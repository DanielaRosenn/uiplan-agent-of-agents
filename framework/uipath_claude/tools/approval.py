"""Interactive and programmatic approval policy for destructive tools."""
from __future__ import annotations

import enum
from collections.abc import Callable
from dataclasses import dataclass, field


DESTRUCTIVE_TOOLS: frozenset[str] = frozenset(
    {
        "write_file",
        "write_documentation",
        "ensure_project_structure",
        "deploy_to_orchestrator",
        "run_workflow",
        "debug_workflow",
        "install_package",
        "run_uip_command",
    }
)


def is_destructive(tool_name: str) -> bool:
    return tool_name in DESTRUCTIVE_TOOLS


class ApprovalDecision(enum.Enum):
    ALLOW_ONCE = "allow_once"
    ALLOW_ALWAYS = "allow_always"
    DENY = "deny"


Prompter = Callable[[str, dict], ApprovalDecision]


@dataclass
class ApprovalPolicy:
    """Destructive tool gate. ``ALLOW_ONCE`` grants at most one passing ``check``
    per ``tool_name`` for this policy instance (evaluated before ``invoke``). A
    failed tool run still consumed that grant."""

    prompter: Prompter
    preapproved: set[str] = field(default_factory=set)
    _once_used: set[str] = field(default_factory=set)

    def check(self, tool_name: str, tool_args: dict) -> bool:
        if not is_destructive(tool_name):
            return True
        if tool_name in self.preapproved:
            return True
        decision = self.prompter(tool_name, tool_args)
        if decision is ApprovalDecision.ALLOW_ALWAYS:
            self.preapproved.add(tool_name)
            return True
        if decision is ApprovalDecision.ALLOW_ONCE:
            if tool_name in self._once_used:
                return False
            self._once_used.add(tool_name)
            return True
        return False
