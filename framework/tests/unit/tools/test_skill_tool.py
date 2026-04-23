"""Test skill tool."""
from pathlib import Path
from uipath_claude.tools.skill_tool import create_skill_tool


def test_create_skill_tool(tmp_path):
    """Test creating a skill tool."""
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("""---
name: test-skill
description: Test skill
---

# Test Skill
""")
    
    skill_metadata = {
        "name": "test-skill",
        "description": "Test skill",
        "path": str(skill_file),
    }
    
    tool = create_skill_tool(skill_metadata)
    
    assert tool.name == "test-skill"
    assert "Test skill" in tool.description
