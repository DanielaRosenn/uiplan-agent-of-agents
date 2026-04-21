"""Branding and logo for CLI."""
import warnings
from importlib.metadata import version, PackageNotFoundError

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


# UiPath brand colors
UIPATH_ORANGE = "#FA4616"
UIPATH_BLUE = "#0067B8"


def get_version() -> str:
    """Get package version or 'dev' if not installed."""
    try:
        return version("uipath-claude")
    except PackageNotFoundError:
        return "dev"


def get_robot_logo() -> str:
    """
    Get ASCII robot logo.
    
    .. deprecated::
        Use :func:`create_welcome_panel` instead for a modern styled banner.
    
    Returns:
        ASCII art robot logo
    """
    warnings.warn(
        "get_robot_logo() is deprecated, use create_welcome_panel() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return r"""
    ╔═══════════════════════════════════════╗
    ║                                       ║
    ║      _____                            ║
    ║     |     |                           ║
    ║     | O O |    UiPath Claude Code     ║
    ║     |  ^  |                           ║
    ║     |_____|    Conversational AI      ║
    ║      |   |     for UiPath Automation  ║
    ║     _|   |_                           ║
    ║    |_______|                          ║
    ║                                       ║
    ╚═══════════════════════════════════════╝
    """


def create_welcome_panel() -> Panel:
    """
    Create a modern styled welcome panel using UiPath brand colors.
    
    Returns:
        Rich Panel with styled banner content
    """
    # Build the title with brand colors
    title = Text()
    title.append("UiPath ", style=f"bold {UIPATH_ORANGE}")
    title.append("Claude Code", style=f"bold {UIPATH_BLUE}")
    
    # UiPath Robot with control panel
    robot = """
       ╔══════════════╗
       ║  ●●●   ●●●   ║
       ║      ▼▼      ║
       ║   \\_____/    ║
       ╚══════╤═══════╝
       ╔══════╧══════╗
    ╔══╝             ╚══╗
    ║   ●  ●●●●●  ●   ║
    ║  ┌───────────┐  ║
    ║  │  UiPath   │  ║
    ║  │  Agent    │  ║
    ║  └───────────┘  ║
    ╚══╗  [■][■][■] ╔══╝
       ╚═════╤═════╝
          ▓▓▓│▓▓▓
    """
    
    # Build the content with colored sections
    content = Text()
    content.append(robot, style=f"bold {UIPATH_ORANGE}")
    content.append("\n")
    content.append("Conversational AI for UiPath Automation", style="dim")
    content.append("\n\n")
    content.append(f"Version: {get_version()}", style="dim italic")
    content.append("\n")
    
    # Create panel with styled border
    panel = Panel(
        content,
        title=title,
        border_style=UIPATH_BLUE,
        padding=(1, 2),
    )
    
    return panel


def print_welcome_banner() -> None:
    """Print welcome banner.

    Writes directly to ``sys.stdout`` so output survives pipes, Studio's
    embedded terminal, and rich's legacy-Windows detection. The banner is
    the robot; we don't let rich's terminal heuristics suppress it.
    """
    import sys

    version_str = get_version()
    banner_lines = [
        "",
        "+------------------------------------------------------------+",
        "|                   UiPath Claude Code                       |",
        "+------------------------------------------------------------+",
        "",
        "             .-------------.",
        "             |  O       O  |      <-- sensors",
        "             |     ___     |",
        "             |    |___|    |      <-- head",
        "             '------|------'",
        "           .--------|--------.",
        "           |  [ UiPath Bot ] |    <-- body",
        "           |  .-----------.  |",
        "           |  | [#][#][#] |  |    <-- control panel",
        "           |  '-----------'  |",
        "           '--------|--------'",
        "              |||   |   |||       <-- legs",
        "",
        "    Conversational AI for UiPath Automation",
        "    Version: " + version_str,
        "",
    ]
    banner = "\n".join(banner_lines) + "\n"

    try:
        sys.stdout.write(banner)
        sys.stdout.flush()
    except Exception:
        pass

    # Follow-up hint uses rich if available (fine if it no-ops); fall back
    # to plain stdout so it always prints.
    try:
        Console().print(
            "Type [bold cyan]/help[/bold cyan] for available commands, "
            "or just start chatting!\n"
        )
    except Exception:
        try:
            sys.stdout.write(
                "Type /help for available commands, or just start chatting!\n\n"
            )
            sys.stdout.flush()
        except Exception:
            pass


def _print_plain_banner(console: Console) -> None:
    """Print plain ASCII-only banner for maximum compatibility."""
    banner = """
====================================================
    UiPath Claude Code - Version: {version}
====================================================
    Conversational AI for UiPath Automation
====================================================
""".format(version=get_version())
    try:
        # Try console.print first
        console.print(banner)
    except (UnicodeEncodeError, Exception):
        # Ultimate fallback - just print to stdout
        print(banner)
