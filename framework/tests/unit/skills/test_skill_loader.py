"""Test skill loader."""
from pathlib import Path
from uipath_claude.skills.loader import load_skill_content


def test_load_skill_content(tmp_path):
    """Test loading skill content."""
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("""---
name: test-skill
description: Test
---

# Test Skill

This is the skill content.
""")
    
    content = load_skill_content(str(skill_file))
    
    assert "Test Skill" in content
    assert "This is the skill content" in content


def test_load_skill_content_nonexistent():
    """Test loading nonexistent skill."""
    content = load_skill_content("/nonexistent/SKILL.md")
    assert content == ""
