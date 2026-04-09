"""Status command implementation."""

from cli.commands import register_command


@register_command(
    name="status",
    description="Show current session status",
)
def status_command(args: str, context: dict) -> str:
    """Show current session status."""
    lines = ["Session Status:", ""]

    session_id = context.get("session_id", "N/A")
    model = context.get("model", "N/A")
    project = context.get("project_name", "None detected")
    cwd = context.get("cwd", "N/A")

    lines.append(f"  Session ID: {session_id}")
    lines.append(f"  Model: {model}")
    lines.append(f"  Project: {project}")
    lines.append(f"  Working Dir: {cwd}")

    return "\n".join(lines)
