"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path


@pytest.fixture
def temp_skills_repo(tmp_path):
    """
    Create a temporary skills repository structure for testing.

    Structure:
    skills/
      ├── test-skill-1/
      │   └── SKILL.md (with YAML frontmatter)
      ├── test-skill-2/
      │   ├── SKILL.md
      │   ├── references/
      │   │   └── guide.md
      │   └── assets/
      │       └── template.py
      └── invalid-skill/  (no SKILL.md)
    """
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    # Skill 1: Minimal SKILL.md
    skill1 = skills_dir / "test-skill-1"
    skill1.mkdir()
    (skill1 / "SKILL.md").write_text("""---
name: test-skill-1
description: |
  Test skill for unit testing.
  TRIGGER when: test mode activated
  DO NOT TRIGGER when: production mode
---

# Test Skill 1

This is a test skill.
""")

    # Skill 2: Full structure with references and assets
    skill2 = skills_dir / "test-skill-2"
    skill2.mkdir()
    (skill2 / "SKILL.md").write_text("""---
name: test-skill-2
description: Test skill with references
---

# Test Skill 2

Another test skill.
""")

    (skill2 / "references").mkdir()
    (skill2 / "references" / "guide.md").write_text("# Guide\n\nTest guide content.")

    (skill2 / "assets").mkdir()
    (skill2 / "assets" / "template.py").write_text("# Template\nprint('test')")

    # Invalid skill: no SKILL.md
    invalid = skills_dir / "invalid-skill"
    invalid.mkdir()
    (invalid / "README.md").write_text("# Not a skill")

    return skills_dir
