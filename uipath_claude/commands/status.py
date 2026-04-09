"""Status command implementation."""
from uipath_claude.commands.registry import CommandRegistry, register_command


def register_status_command(registry: CommandRegistry) -> None:
    """Register the /status command."""
    
    @register_command(registry, name="status", description="Show session status")
    def status_command() -> str:
        """Show current session status."""
        return "Session active. Type /help for commands."
