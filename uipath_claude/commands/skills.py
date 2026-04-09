"""Skills command implementation."""
from uipath_claude.commands.registry import CommandRegistry, register_command


def register_skills_command(registry: CommandRegistry) -> None:
    """Register the /skills command."""
    
    @register_command(registry, name="skills", description="List available skills")
    def skills_command() -> str:
        """List all available skills."""
        return "Skills: (to be implemented)"
