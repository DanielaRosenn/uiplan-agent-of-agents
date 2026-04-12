"""Approval guard for potentially sensitive UiPath CLI operations."""
from __future__ import annotations

import os


def _truthy(value: str | None) -> bool:
    """Return True for common truthy string values."""
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on", "y"}


def check_cli_approval(env: dict[str, str] | None = None) -> tuple[bool, str]:
    """
    Check whether UiPath CLI execution is approved.

    Approval is only required when UIPATH_CLAUDE_REQUIRE_APPROVAL is truthy.
    """
    source = env if env is not None else os.environ
    if not _truthy(source.get("UIPATH_CLAUDE_REQUIRE_APPROVAL")):
        return True, ""

    approval_vars = ("UIPATH_CLAUDE_CLI_APPROVED", "UIPATH_CLAUDE_APPROVED")
    explicit_approval = any(_truthy(source.get(var_name)) for var_name in approval_vars)
    if explicit_approval:
        return True, ""

    return (
        False,
        "CLI operation blocked: approval required. Set UIPATH_CLAUDE_CLI_APPROVED=true "
        "or UIPATH_CLAUDE_APPROVED=true when UIPATH_CLAUDE_REQUIRE_APPROVAL=true.",
    )
