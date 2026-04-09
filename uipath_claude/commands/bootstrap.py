"""Bootstrap command implementation."""
from uipath_claude.commands.registry import CommandRegistry, register_command


def register_bootstrap_command(registry: CommandRegistry) -> None:
    """Register the /bootstrap command."""
    
    @register_command(registry, name="bootstrap", description="Start bootstrap flow")
    def bootstrap_command() -> str:
        """Start the bootstrap flow (BA -> SA -> Dev -> QA)."""
        return "Starting bootstrap flow..."
