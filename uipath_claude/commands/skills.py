"""Skills command implementation."""
import json
from collections import defaultdict
from pathlib import Path
from typing import Callable, Optional

from uipath_claude.commands.registry import CommandRegistry, register_command
from uipath_claude.skills.registry import SkillRegistry
from uipath_claude.skills.sources import SkillOrigin


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
                origin = skill.get("origin", "unknown")
                lines.append(f"  - {skill.get('name', 'unknown')} [{origin}]")
            lines.append("")

        if not role_skills:
            lines.append(
                "No skills matched that role. Try /skills conversational "
                "or one of: ba, sa, developer, qa."
            )

        return "\n".join(lines).strip()


def generate_skills_manifest(
    output_path: Optional[str] = None,
    project_root: Optional[Path] = None,
) -> dict:
    """
    Generate skills manifest with provenance information.
    
    Args:
        output_path: Path to write manifest JSON. If None, only returns dict.
        project_root: Root path for the project. Defaults to cwd.
        
    Returns:
        Manifest dictionary with skill provenance info.
    """
    root = project_root or Path.cwd()
    registry = SkillRegistry(project_root=root)
    registry.load_skills()
    manifest = registry.generate_manifest()
    
    if output_path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(manifest, indent=2))
    
    return manifest


def print_skills_manifest(output_path: str = "skills-manifest.json") -> str:
    """
    Generate and save skills manifest, return summary.
    
    Args:
        output_path: Path to write manifest JSON.
        
    Returns:
        Summary string for CLI output.
    """
    manifest = generate_skills_manifest(output_path=output_path)
    
    lines = [
        f"Skills manifest generated: {output_path}",
        f"Total skills: {manifest['total_skills']}",
        "",
        "By origin:",
    ]
    
    for origin in SkillOrigin:
        count = manifest["counts"].get(origin.value, 0)
        if count > 0:
            lines.append(f"  {origin.value}: {count}")
    
    if manifest.get("submodule_commit"):
        lines.append(f"\nUiPath submodule commit: {manifest['submodule_commit']}")
    
    return "\n".join(lines)
