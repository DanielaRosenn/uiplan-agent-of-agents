"""UiPath CLI management utilities."""
import subprocess
import shutil
from typing import Tuple

from rich.console import Console
from rich.prompt import Confirm


def is_uip_installed() -> bool:
    """Check if uip CLI is available in PATH."""
    return shutil.which("uip") is not None or shutil.which("uip.cmd") is not None


def get_uip_version() -> str | None:
    """Get installed uip CLI version, or None if not installed."""
    if not is_uip_installed():
        return None
    try:
        result = subprocess.run(
            ["uip", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None


def install_uip_cli(console: Console | None = None) -> Tuple[bool, str]:
    """
    Install @uipath/cli globally via npm.

    Returns:
        Tuple of (success, message)
    """
    console = console or Console()
    try:
        result = subprocess.run(
            ["npm", "install", "-g", "@uipath/cli"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            return True, "UiPath CLI installed successfully"
        return False, f"Installation failed: {result.stderr}"
    except FileNotFoundError:
        return False, "npm not found. Please install Node.js first."
    except subprocess.TimeoutExpired:
        return False, "Installation timed out"
    except Exception as e:
        return False, f"Installation failed: {e}"


def prompt_install_cli(console: Console | None = None) -> bool:
    """
    Prompt user to install UiPath CLI if missing.

    Returns:
        True if installed successfully, False otherwise
    """
    console = console or Console()

    if is_uip_installed():
        return True

    console.print("[yellow]UiPath CLI (uip) is not installed.[/yellow]")
    console.print("The CLI is required for workflow validation and execution.")
    console.print("")

    if Confirm.ask("Install @uipath/cli now?", default=True):
        console.print("[dim]Running: npm install -g @uipath/cli[/dim]")
        success, message = install_uip_cli(console)
        if success:
            console.print(f"[green]+[/green] {message}")
            return True
        else:
            console.print(f"[red]x[/red] {message}")
            return False
    else:
        console.print("[dim]Skipping CLI installation. Some features may not work.[/dim]")
        return False
