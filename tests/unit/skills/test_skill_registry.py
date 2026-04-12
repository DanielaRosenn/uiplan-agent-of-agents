"""Test skill registry."""
from pathlib import Path
from uipath_claude.skills.registry import SkillRegistry


def test_skill_registry_load_from_multiple_sources(tmp_path):
    """Test loading skills from multiple sources with precedence."""
    # Create source 1 (higher priority)
    source1 = tmp_path / "source1"
    source1.mkdir()
    skill1_dir = source1 / "skill-a"
    skill1_dir.mkdir()
    (skill1_dir / "SKILL.md").write_text("""---
name: skill-a
description: From source 1
triggers: ["a"]
---
""")
    
    # Create source 2 (lower priority, has duplicate)
    source2 = tmp_path / "source2"
    source2.mkdir()
    skill2_dir = source2 / "skill-a"
    skill2_dir.mkdir()
    (skill2_dir / "SKILL.md").write_text("""---
name: skill-a
description: From source 2
triggers: ["a"]
---
""")
    skill3_dir = source2 / "skill-b"
    skill3_dir.mkdir()
    (skill3_dir / "SKILL.md").write_text("""---
name: skill-b
description: Unique skill
triggers: ["b"]
---
""")
    
    registry = SkillRegistry(sources=[str(source1), str(source2)])
    skills = registry.load_skills()
    
    # Should have 2 skills (skill-a from source1, skill-b from source2)
    assert len(skills) == 2
    
    # skill-a should be from source1 (higher priority)
    skill_a = [s for s in skills if s["name"] == "skill-a"][0]
    assert skill_a["description"] == "From source 1"
    
    # skill-b should exist
    skill_b = [s for s in skills if s["name"] == "skill-b"][0]
    assert skill_b["description"] == "Unique skill"
    assert skill_a["source_root"] == str(source1)
    assert skill_b["source_root"] == str(source2)


def test_skill_registry_filter_by_agent():
    """Test filtering skills by agent role."""
    registry = SkillRegistry(sources=[])
    registry.skills = [
        {"name": "pdd-creation", "description": "PDD"},
        {"name": "uipath-rpa-workflows", "description": "RPA"},
        {"name": "uipath-code-reviewer", "description": "Review"},
    ]
    
    # BA agent should get pdd-creation
    ba_skills = registry.filter_by_agent("ba")
    assert any(s["name"] == "pdd-creation" for s in ba_skills)
    assert not any(s["name"] == "uipath-rpa-workflows" for s in ba_skills)
    
    # Developer agent should get uipath-rpa-workflows
    dev_skills = registry.filter_by_agent("developer")
    assert any(s["name"] == "uipath-rpa-workflows" for s in dev_skills)
    assert not any(s["name"] == "pdd-creation" for s in dev_skills)
