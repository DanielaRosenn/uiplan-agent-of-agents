"""Skill discovery from directories."""
import re
from pathlib import Path
from typing import List, Dict, Any


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
            
            # Extract frontmatter
            frontmatter_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
            if not frontmatter_match:
                continue
            
            frontmatter = frontmatter_match.group(1)
            
            # Parse frontmatter
            metadata = {}
            for line in frontmatter.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Parse triggers as list
                    if key == 'triggers':
                        value = eval(value)  # Safe for controlled input
                    
                    metadata[key] = value
            
            if 'name' in metadata:
                skills.append(metadata)
        
        except Exception:
            continue
    
    return skills
