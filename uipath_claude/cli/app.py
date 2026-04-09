"""CLI application entry point."""
import typer
from pathlib import Path
from uipath_claude.rendering.branding import print_welcome_banner
from uipath_claude.context.project import detect_uipath_project
from uipath_claude.memory.loader import load_memory


app = typer.Typer(help="UiPath Claude Code - Conversational AI for UiPath")


@app.command()
def chat(
    no_banner: bool = typer.Option(False, "--no-banner", help="Skip welcome banner"),
):
    """Start conversational chat mode."""
    if not no_banner:
        print_welcome_banner()
    
    project_context = detect_uipath_project(str(Path.cwd()))
    if project_context:
        print(f"📁 Detected UiPath project: {project_context['project_name']}\n")
    
    memory = load_memory(
        project_path=project_context["project_path"] if project_context else None
    )
    
    print("Chat mode (to be implemented)")


@app.command()
def start_project(
    project_name: str = typer.Argument(..., help="Project name"),
):
    """Start bootstrap flow for new project."""
    print(f"Starting bootstrap flow for: {project_name}")


if __name__ == "__main__":
    app()
