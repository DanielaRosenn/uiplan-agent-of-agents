"""Skills command implementation."""

from pathlib import Path

from cli.commands import register_command


@register_command(
    name="skills",
    description="List available skills",
    aliases=["sk"],
)
def skills_command(args: str, context: dict) -> str:
    """List available skills from configured directories."""
    skills_dir = context.get("skills_dir")

    if not skills_dir:
        return "No skills directory configured."

    skills_path = Path(skills_dir)
    if not skills_path.exists():
        return f"Skills directory not found: {skills_dir}"

    skills = []
    for skill_dir in skills_path.iterdir():
        if skill_dir.is_dir():
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                skills.append(skill_dir.name)

    if not skills:
        return "No skills found."

    lines = ["Available Skills:", ""]
    for skill in sorted(skills):
        lines.append(f"  - {skill}")

    return "\n".join(lines)
