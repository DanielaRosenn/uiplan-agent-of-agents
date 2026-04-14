"""Skill discovery from directories."""
from pathlib import Path
from typing import List, Dict, Any
import yaml


def _extract_frontmatter(content: str) -> str | None:
    """Extract YAML frontmatter from markdown with LF/CRLF support."""
    lines = content.splitlines()
    if not lines:
        return None
    if lines[0].lstrip("\ufeff").strip() != "---":
        return None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[1:index])
    return None


def discover_skills(skills_dir: str) -> List[Dict[str, Any]]:
    """
    Discover skills in a directory.
    
    Args:
        skills_dir: Path to skills directory
        
    Returns:
        List of skill metadata dictionaries
    """
    skills = []
    skills_path = Path(skills_dir)
    
    if not skills_path.exists():
        return skills
    
    for skill_file in skills_path.rglob("SKILL.md"):
        try:
            content = skill_file.read_text(encoding="utf-8")

            frontmatter_text = _extract_frontmatter(content)
            if not frontmatter_text:
                continue

            parsed = yaml.safe_load(frontmatter_text)
            if not isinstance(parsed, dict):
                continue

            name = parsed.get("name")
            if not name:
                continue

            metadata: Dict[str, Any] = {
                "name": str(name),
                "description": str(parsed.get("description", "")),
                "triggers": parsed.get("triggers", []),
                "path": str(skill_file.resolve()),
            }
            if "tags" in parsed:
                metadata["tags"] = parsed["tags"]

            skills.append(metadata)
        except Exception:
            continue

    return skills
