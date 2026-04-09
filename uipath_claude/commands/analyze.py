"""Analyze command implementation."""
from uipath_claude.commands.registry import CommandRegistry, register_command


def register_analyze_command(registry: CommandRegistry) -> None:
    """Register the /analyze command."""
    
    @register_command(registry, name="analyze", description="Analyze UiPath project")
    def analyze_command(project_path: str = ".") -> str:
        """Analyze a UiPath project."""
        return f"Analyzing project: {project_path}"
