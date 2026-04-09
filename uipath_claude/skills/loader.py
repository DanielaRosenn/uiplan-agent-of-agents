"""Skill content loading."""
from pathlib import Path


def load_skill_content(skill_path: str) -> str:
    """
    Load skill content from SKILL.md file.
    
    Args:
        skill_path: Path to SKILL.md file
        
    Returns:
        Skill content (empty string if file doesn't exist)
    """
    skill_file = Path(skill_path)
    
    if not skill_file.exists():
        return ""
    
    try:
        return skill_file.read_text()
    except Exception:
        return ""
