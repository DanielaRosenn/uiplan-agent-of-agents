"""Authentication check utilities for UiPath CLI."""
import subprocess
import os
from typing import Literal, Optional, Tuple

AuthPromptChoice = Literal["interactive_auth", "skip_auth"]


def check_uipath_cli_installed() -> bool:
    """Check if UiPath CLI is installed and accessible."""
    try:
        result = subprocess.run(
            ["uipath", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            stdin=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_uipath_auth_status() -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Check UiPath CLI authentication status by testing a command that requires auth.
    
    This is more reliable than checking token files, as it validates the token
    is actually valid for the configured Orchestrator.
    
    Returns:
        Tuple of (is_authenticated, account_name, error_message)
    """
    try:
        # Test with a lightweight command that requires authentication
        # Using 'processes list' with limit 1 is fast and requires auth
        result = subprocess.run(
            ["uipath", "processes", "list", "--limit", "1"],
            capture_output=True,
            text=True,
            timeout=10,
            stdin=subprocess.DEVNULL,
        )
        
        if result.returncode == 0:
            # Command succeeded - user is authenticated
            return True, None, None
        
        # Command failed - check if it's an auth error
        error_output = (result.stderr or result.stdout or "").lower()
        
        # Authentication-related keywords
        auth_keywords = [
            "not authenticated",
            "authentication required",
            "invalid token",
            "expired token",
            "unauthorized",
            "401",
            "403"
        ]
        
        if any(keyword in error_output for keyword in auth_keywords):
            return False, None, "Not authenticated with UiPath Orchestrator"
        
        # Other error (CLI works but command failed for different reason)
        # Be conservative - assume not authenticated
        return False, None, "Unable to verify authentication status. Please authenticate to enable deployment features."
        
    except subprocess.TimeoutExpired:
        return False, None, "Authentication check timed out (Orchestrator unreachable?)"
    except FileNotFoundError:
        return False, None, "UiPath CLI not found"
    except Exception as e:
        return False, None, f"Error checking authentication: {str(e)}"


def get_auth_instructions(orchestrator_url: Optional[str] = None) -> str:
    """
    Get authentication instructions based on the Orchestrator URL.
    
    Args:
        orchestrator_url: Optional Orchestrator URL from environment
    
    Returns:
        Formatted authentication instructions
    """
    # Get orchestrator URL from environment if provided
    orch_url = orchestrator_url or os.getenv("UIPATH_ORCHESTRATOR_URL")
    tenant = os.getenv("UIPATH_TENANT_NAME")
    
    if orch_url and tenant:
        # Have both URL and tenant - provide specific instructions
        if "cloud.uipath.com" in orch_url:
            # Cloud Orchestrator
            return f"""
To authenticate with UiPath Cloud Orchestrator, run:

    uipath auth --cloud --tenant {tenant}

This will open a browser for interactive authentication.
Or choose option 1 in this chat to run the same command here.
"""
        else:
            # On-premise or custom
            return f"""
To authenticate with your Orchestrator, run:

    uipath auth --base-url {orch_url} --tenant {tenant}

This will open a browser for interactive authentication.
Or choose option 1 in this chat to run the same command here.
"""
    elif tenant:
        # Have tenant but no URL - assume cloud
        return f"""
To authenticate with UiPath Cloud Orchestrator, run:

    uipath auth --cloud --tenant {tenant}

This will open a browser for interactive authentication.
Or choose option 1 in this chat to run the same command here.
"""
    else:
        # No configuration - provide generic instructions
        return """
To authenticate with UiPath Orchestrator:

For Cloud Orchestrator:
    uipath auth --cloud --tenant [your-tenant]

For On-Premise Orchestrator:
    uipath auth --base-url [orchestrator-url] --tenant [tenant-name]

Set environment variables for your Orchestrator:
    UIPATH_ORCHESTRATOR_URL=https://cloud.uipath.com/[org]/[tenant]/orchestrator_
    UIPATH_TENANT_NAME=[tenant]

Then restart the chat.
"""


def resolve_uipath_auth_argv(
    orchestrator_url: Optional[str] = None,
) -> tuple[Optional[list[str]], Optional[str]]:
    """Build ``uipath auth ...`` argv from environment (same rules as printed instructions).

    Returns:
        (argv, None) on success, or (None, error_message) if tenant is missing.
    """
    orch_url = (orchestrator_url or os.getenv("UIPATH_ORCHESTRATOR_URL") or "").strip()
    tenant = (os.getenv("UIPATH_TENANT_NAME") or "").strip()
    if not tenant:
        return None, (
            "Set UIPATH_TENANT_NAME (and optionally UIPATH_ORCHESTRATOR_URL) "
            "so the CLI knows which tenant to authenticate against."
        )
    orch_lower = orch_url.lower()
    if orch_url and "cloud.uipath.com" in orch_lower:
        return ["uipath", "auth", "--cloud", "--tenant", tenant], None
    if orch_url:
        return ["uipath", "auth", "--base-url", orch_url, "--tenant", tenant], None
    return ["uipath", "auth", "--cloud", "--tenant", tenant], None


def run_uipath_interactive_auth(console, argv: list[str]) -> int:
    """Run ``uipath auth`` with inherited stdio so the browser/device flow works in this terminal.

    Returns:
        Process return code (0 = CLI reported success).
    """
    display = " ".join(argv)
    console.print(f"\n[bold]Running[/bold] [cyan]{display}[/cyan]\n")
    console.print(
        "[dim]If a browser window opens, complete sign-in there, then return here.[/dim]\n"
    )
    try:
        proc = subprocess.run(argv)
    except FileNotFoundError:
        console.print("[red]uipath CLI not found on PATH.[/red]\n")
        return 127
    except OSError as e:
        console.print(f"[red]Could not start uipath auth: {e}[/red]\n")
        return 1
    return int(proc.returncode)


def prompt_for_authentication(console, orchestrator_url: Optional[str] = None) -> AuthPromptChoice:
    """
    Prompt user to authenticate and provide instructions.
    
    Args:
        console: Rich console for output
        orchestrator_url: Optional Orchestrator URL
    
    Returns:
        ``skip_auth`` to continue chat without Orchestrator auth, or
        ``interactive_auth`` to run ``uipath auth`` in this session.
    """
    from rich.panel import Panel
    
    instructions = get_auth_instructions(orchestrator_url)
    
    console.print(Panel(
        "[yellow]⚠ UiPath CLI Authentication Required[/yellow]\n\n"
        "You are not authenticated with UiPath Orchestrator.\n"
        "Authentication is required for deployment features.\n"
        + instructions +
        "\n[dim]You can still use the chat for workflow creation (without deployment).[/dim]",
        title="Authentication Status",
        border_style="yellow"
    ))
    
    console.print("\nOptions:")
    console.print(
        "  1. Run [cyan]uipath auth[/cyan] now in this terminal "
        "[dim](uses UIPATH_TENANT_NAME / UIPATH_ORCHESTRATOR_URL; browser may open)[/dim]"
    )
    console.print("  2. Continue without authentication (deployment disabled)")
    
    from rich.prompt import Prompt
    choice = Prompt.ask("\nChoose an option", choices=["1", "2"], default="1")
    
    return "skip_auth" if choice == "2" else "interactive_auth"
