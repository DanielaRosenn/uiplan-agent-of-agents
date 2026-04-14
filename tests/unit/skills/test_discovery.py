"""Test skill discovery."""
from pathlib import Path
import inspect

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


def test_discover_skills_missing_frontmatter(tmp_path):
    """Test SKILL.md without frontmatter is ignored."""
    skill_dir = tmp_path / "bad-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# No frontmatter")
    skills = discover_skills(str(tmp_path))
    assert skills == []


def test_discover_skills_invalid_frontmatter(tmp_path):
    """Test invalid YAML frontmatter is ignored safely."""
    skill_dir = tmp_path / "broken-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: broken
triggers: [oops
---
""")
    skills = discover_skills(str(tmp_path))
    assert skills == []


def test_discover_skills_does_not_use_eval():
    """Test parser implementation does not use eval."""
    source = inspect.getsource(discover_skills)
    assert "eval(" not in source


def test_discover_skills_supports_crlf_frontmatter(tmp_path):
    skill_dir = tmp_path / "windows-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\r\n"
        "name: crlf-skill\r\n"
        "description: Works with CRLF\r\n"
        "triggers: [\"mail\"]\r\n"
        "---\r\n\r\n"
        "# Skill\r\n",
        encoding="utf-8",
    )
    skills = discover_skills(str(tmp_path))
    assert len(skills) == 1
    assert skills[0]["name"] == "crlf-skill"
