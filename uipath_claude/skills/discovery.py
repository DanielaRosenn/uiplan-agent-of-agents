"""Skill discovery from directories."""
import re
from pathlib import Path
from typing import List, Dict, Any
import yaml


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
            content = skill_file.read_text()

            frontmatter_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
            if not frontmatter_match:
                continue

            parsed = yaml.safe_load(frontmatter_match.group(1))
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
