"""Help command implementation."""

from cli.commands import register_command, COMMANDS


@register_command(
    name="help",
    description="Show available commands",
    aliases=["h", "?"],
)
def help_command(args: str, context: dict) -> str:
    """Show help for available commands."""
    lines = ["Available commands:", ""]

    seen = set()
    for name, cmd in sorted(COMMANDS.items()):
        if cmd.name in seen:
            continue
        seen.add(cmd.name)

        alias_str = ""
        if cmd.aliases:
            alias_str = f" (aliases: {', '.join('/' + a for a in cmd.aliases)})"

        lines.append(f"  /{cmd.name} - {cmd.description}{alias_str}")

    return "\n".join(lines)
