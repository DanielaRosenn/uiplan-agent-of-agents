"""Help command implementation."""
from uipath_claude.commands.registry import CommandRegistry, register_command


def register_help_command(registry: CommandRegistry) -> None:
    """Register the /help command."""
    
    @register_command(registry, name="help", description="Show available commands")
    def help_command() -> str:
        """Show all available commands."""
        lines = ["Available commands:\n"]
        
        for name, info in sorted(registry.commands.items()):
            lines.append(f"  /{name} - {info['description']}")
        
        return "\n".join(lines)
