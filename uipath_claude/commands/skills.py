"""Skills command implementation."""
from collections import defaultdict
from typing import Callable

from uipath_claude.commands.registry import CommandRegistry, register_command


def register_skills_command(
    registry: CommandRegistry,
    list_skills: Callable[[], list[dict]],
    filter_skills_by_role: Callable[[str], list[dict]],
) -> None:
    """Register the /skills command."""

    @register_command(registry, name="skills", description="List available skills")
    def skills_command(role: str = "conversational") -> str:
        """List all available skills."""
        all_skills = list_skills()
        role_skills = filter_skills_by_role(role)

        if not all_skills:
            return "No skills found in configured sources."

        grouped = defaultdict(list)
        for skill in role_skills:
            src = skill.get("source_root") or skill.get("path", "")
            grouped[str(src)].append(skill)

        lines = [f"Skills for role '{role}' ({len(role_skills)} of {len(all_skills)} total):", ""]
        for source, skills in sorted(grouped.items()):
            lines.append(f"Source: {source} ({len(skills)})")
            for skill in sorted(skills, key=lambda s: s.get("name", ""))[:20]:
                lines.append(f"  - {skill.get('name', 'unknown')}")
            lines.append("")

        if not role_skills:
            lines.append(
                "No skills matched that role. Try /skills conversational "
                "or one of: ba, sa, developer, qa."
            )

        return "\n".join(lines).strip()
