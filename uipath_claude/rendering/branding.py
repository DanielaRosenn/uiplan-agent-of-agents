"""Branding and logo for CLI."""
from rich.console import Console


def get_robot_logo() -> str:
    """
    Get ASCII robot logo.
    
    Returns:
        ASCII art robot logo
    """
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


def print_welcome_banner() -> None:
    """Print welcome banner with robot logo."""
    console = Console()
    console.print(get_robot_logo(), style="bold cyan")
    console.print("\nType /help for available commands, or just start chatting!\n")
