"""Test skill discovery."""
from pathlib import Path
from uipath_claude.skills.discovery import discover_skills


def test_discover_skills(tmp_path):
    """Test discovering skills in a directory."""
    # Create test skill
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("""---
name: test-skill
description: Test skill
triggers: ["test"]
---

# Test Skill
""")
    
    skills = discover_skills(str(tmp_path))
    
    assert len(skills) == 1
    assert skills[0]["name"] == "test-skill"
    assert skills[0]["description"] == "Test skill"
    assert "test" in skills[0]["triggers"]


def test_discover_skills_empty_dir(tmp_path):
    """Test discovering skills in empty directory."""
    skills = discover_skills(str(tmp_path))
    assert len(skills) == 0
