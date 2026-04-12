"""Command to update the UiPath skills submodule."""
from uipath_claude.commands.registry import CommandRegistry
from uipath_claude.skills.updater import (
    check_for_updates,
    update_skills,
    get_skills_info,
)


def register_update_skills_command(registry: CommandRegistry) -> None:
    """Register the /update-skills command."""

    def handle_update_skills(args: str) -> str:
        args = args.strip().lower()
        
        # Check-only mode
        if args in ("--check", "-c", "check"):
            has_updates, message, current, remote = check_for_updates()
            if has_updates:
                return f"Updates available for UiPath skills:\n  Current: {current}\n  Latest:  {remote}\n\nRun `/update-skills` to update."
            return message
        
        # Info mode
        if args in ("--info", "-i", "info"):
            info = get_skills_info()
            lines = [
                "UiPath Skills Info:",
                f"  Path: {info['path']}",
                f"  Current commit: {info['current_commit'] or 'unknown'}",
                f"  Remote commit:  {info['remote_commit'] or 'unknown'}",
                f"  Has updates: {info['has_updates']}",
                f"  Skills count: {info['skills_count']}",
            ]
            if info["skills"]:
                lines.append("  Available skills:")
                for skill in info["skills"]:
                    lines.append(f"    - {skill}")
            return "\n".join(lines)
        
        # Update mode (default)
        has_updates, message, current, remote = check_for_updates()
        
        if not has_updates and args != "--force":
            return message
        
        success, result = update_skills()
        if success:
            return f"Skills updated successfully.\n{result}"
        return f"Failed to update skills: {result}"
    
    registry.register(
        "update-skills",
        "Update UiPath skills from the official repository",
        handle_update_skills,
    )
