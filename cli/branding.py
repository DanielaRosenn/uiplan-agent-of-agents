# cli/branding.py
"""Branding and welcome banner for UiPath Claude Code."""

import shutil

ROBOT_ASCII = r"""
       ┌─────────┐
       │  o   o  │
       │    ▼    │
       │  └───┘  │
       └────┬────┘
          ┌─┴─┐
         ─┤   ├─
          └───┘
"""

COMPACT_LOGO = "[o_o] UiPath Claude Code"


def get_terminal_width() -> int:
    """Get terminal width, default to 80 if unavailable."""
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 80


def get_compact_logo() -> str:
    """Return compact single-line logo."""
    return COMPACT_LOGO


def print_welcome_banner(
    version: str,
    cwd: str,
    model: str,
    project_name: str | None = None,
) -> None:
    """
    Print the welcome banner with robot logo.

    Args:
        version: Application version
        cwd: Current working directory
        model: Active model name
        project_name: Detected UiPath project name (if any)
    """
    width = get_terminal_width()

    if width < 60:
        print(f"\n{COMPACT_LOGO} v{version}")
        print(f"  Model: {model}")
        if project_name:
            print(f"  Project: {project_name}")
        print()
        return

    # Full banner
    border = "═" * 55

    print(f"\n  ╔{border}╗")
    print(f"  ║{' ' * 55}║")

    # Robot art lines
    robot_lines = ROBOT_ASCII.strip().split("\n")
    info_lines = [
        "UiPath Claude Code",
        f"v{version}",
        "",
        f"Working in: {_truncate_path(cwd, 30)}",
        f"Model: {model}",
    ]
    if project_name:
        info_lines.insert(3, f"Project: {project_name}")

    max_lines = max(len(robot_lines), len(info_lines))

    for i in range(max_lines):
        robot_part = robot_lines[i] if i < len(robot_lines) else ""
        info_part = info_lines[i] if i < len(info_lines) else ""

        robot_padded = f"{robot_part:<20}"
        info_padded = f"{info_part:<33}"

        print(f"  ║ {robot_padded} {info_padded}║")

    print(f"  ║{' ' * 55}║")
    print(f"  ╚{border}╝\n")


def _truncate_path(path: str, max_len: int) -> str:
    """Truncate path in the middle if too long."""
    if len(path) <= max_len:
        return path

    half = (max_len - 3) // 2
    return f"{path[:half]}...{path[-half:]}"
