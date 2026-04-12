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
    
    # Build the content
    content = Text()
    content.append("\n")
    content.append("Conversational AI for UiPath Automation", style="dim")
    content.append("\n\n")
    content.append(f"Version: {get_version()}", style="dim italic")
    content.append("\n")
    
    # Create panel with styled border
    panel = Panel(
        content,
        title=title,
        border_style="bright_blue",
        padding=(1, 2),
    )
    
    return panel


def print_welcome_banner() -> None:
    """Print welcome banner with modern styled panel."""
    console = Console()
    console.print(create_welcome_panel())
    console.print("Type [bold cyan]/help[/bold cyan] for available commands, or just start chatting!\n")
