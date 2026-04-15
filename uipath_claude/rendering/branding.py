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
    """Print welcome banner with modern styled panel or fallback for non-rich terminals."""
    console = Console()
    
    # Try rich panel first, fallback to plain text if terminal doesn't support it
    try:
        # Check if terminal supports rich rendering
        if console.is_terminal and not console.legacy_windows:
            console.print(create_welcome_panel())
        else:
            # Fallback for terminals that don't support rich properly
            _print_plain_banner(console)
    except Exception:
        # If anything fails, use plain fallback
        _print_plain_banner(console)
    
    console.print("Type [bold cyan]/help[/bold cyan] for available commands, or just start chatting!\n")


def _print_plain_banner(console: Console) -> None:
    """Print plain text banner for terminals that don't support rich formatting."""
    banner = """
╔════════════════════════════════════════════════════╗
║                                                    ║
║           ╔══════════════╗                         ║
║           ║  ●●●   ●●●   ║    UiPath Claude Code  ║
║           ║      ▼▼      ║    AI Workflow Builder ║
║           ║   \\_____/    ║    Version {version}   ║
║           ╚══════╤═══════╝                         ║
║           ╔══════╧══════╗                          ║
║        ╔══╝             ╚══╗                       ║
║        ║   ●  ●●●●●  ●   ║                       ║
║        ║  ┌───────────┐  ║  🟠 Natural language  ║
║        ║  │  UiPath   │  ║  🔵 XAML workflows    ║
║        ║  │  Agent    │  ║  ⚡ 25 iterations      ║
║        ║  └───────────┘  ║                        ║
║        ╚══╗  [■][■][■] ╔══╝  Type /help           ║
║           ╚═════╤═════╝                            ║
║              ▓▓▓│▓▓▓                               ║
║                                                    ║
╚════════════════════════════════════════════════════╝
""".format(version=get_version())
    console.print(banner)
