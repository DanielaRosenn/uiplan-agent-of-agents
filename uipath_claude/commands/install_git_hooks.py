"""CLI command: ``/install-git-hooks`` — install submodule-autoupdate hooks."""
from __future__ import annotations

from uipath_claude.commands.registry import CommandRegistry
from uipath_claude.hooks.install_git_hooks import install


def register_install_git_hooks_command(registry: CommandRegistry) -> None:
    """Register the ``/install-git-hooks`` command."""

    def handle(*args: str) -> str:
        force = bool(args) and args[0] in ("--force", "-f")
        try:
            results = install(force=force)
        except RuntimeError as e:
            return f"Error: {e}"
        lines = ["Git hook installation:"]
        for name, status in results:
            lines.append(f"  {name}: {status}")
        return "\n".join(lines)

    registry.register(
        "install-git-hooks",
        "Install git hooks that auto-refresh the skills submodule",
        handle,
    )
