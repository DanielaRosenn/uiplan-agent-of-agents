"""Test skill registry."""
from pathlib import Path
from unittest.mock import patch

import pytest

from uipath_claude.skills.registry import SkillRegistry
from uipath_claude.skills.sources import SkillOrigin


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
    
    # Use tuples with origin for the new API
    sources = [
        (str(source1), SkillOrigin.USER),
        (str(source2), SkillOrigin.PROJECT),
    ]
    registry = SkillRegistry(sources=sources)
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
        {"name": "uipath-planner", "description": "Planning"},
        {"name": "uipath-rpa", "description": "RPA"},
        {"name": "uipath-servo", "description": "UI Automation"},
    ]
    
    # BA agent should get uipath-planner
    ba_skills = registry.filter_by_agent("ba")
    assert any(s["name"] == "uipath-planner" for s in ba_skills)
    assert not any(s["name"] == "uipath-rpa" for s in ba_skills)
    
    # Developer agent should get planner plus RPA skills
    dev_skills = registry.filter_by_agent("developer")
    assert any(s["name"] == "uipath-rpa" for s in dev_skills)
    assert any(s["name"] == "uipath-planner" for s in dev_skills)


class TestSkillOriginTracking:
    """Tests for origin/provenance tracking in registry."""
    
    def test_skill_origin_tracking(self, tmp_path):
        """Verify each loaded skill has correct origin field."""
        # Create skills in different "origins"
        user_dir = tmp_path / "user"
        user_dir.mkdir()
        (user_dir / "user-skill").mkdir()
        (user_dir / "user-skill" / "SKILL.md").write_text("""---
name: user-skill
description: User skill
---
""")
        
        ext_dir = tmp_path / "extensions"
        ext_dir.mkdir()
        (ext_dir / "ext-skill").mkdir()
        (ext_dir / "ext-skill" / "SKILL.md").write_text("""---
name: ext-skill
description: Extension skill
---
""")
        
        sources = [
            (str(user_dir), SkillOrigin.USER),
            (str(ext_dir), SkillOrigin.EXTENSIONS),
        ]
        registry = SkillRegistry(sources=sources)
        skills = registry.load_skills()
        
        user_skill = next(s for s in skills if s["name"] == "user-skill")
        ext_skill = next(s for s in skills if s["name"] == "ext-skill")
        
        assert user_skill["origin"] == "user"
        assert ext_skill["origin"] == "extensions"
    
    def test_override_preserves_origin(self, tmp_path):
        """User skill overrides UiPath skill; origin should be 'user'."""
        # Create same skill in both user and submodule dirs
        user_dir = tmp_path / "user"
        user_dir.mkdir()
        (user_dir / "shared-skill").mkdir()
        (user_dir / "shared-skill" / "SKILL.md").write_text("""---
name: shared-skill
description: User version
---
""")
        
        submod_dir = tmp_path / "submodule"
        submod_dir.mkdir()
        (submod_dir / "shared-skill").mkdir()
        (submod_dir / "shared-skill" / "SKILL.md").write_text("""---
name: shared-skill
description: UiPath version
---
""")
        
        sources = [
            (str(user_dir), SkillOrigin.USER),
            (str(submod_dir), SkillOrigin.UIPATH_SUBMODULE),
        ]
        registry = SkillRegistry(sources=sources)
        skills = registry.load_skills()
        
        # Should only have one skill (user version wins)
        assert len(skills) == 1
        skill = skills[0]
        assert skill["description"] == "User version"
        assert skill["origin"] == "user"
    
    def test_filter_by_origin(self, tmp_path):
        """Test filtering skills by their origin."""
        user_dir = tmp_path / "user"
        user_dir.mkdir()
        (user_dir / "skill-a").mkdir()
        (user_dir / "skill-a" / "SKILL.md").write_text("---\nname: skill-a\n---\n")
        
        ext_dir = tmp_path / "ext"
        ext_dir.mkdir()
        (ext_dir / "skill-b").mkdir()
        (ext_dir / "skill-b" / "SKILL.md").write_text("---\nname: skill-b\n---\n")
        
        sources = [
            (str(user_dir), SkillOrigin.USER),
            (str(ext_dir), SkillOrigin.EXTENSIONS),
        ]
        registry = SkillRegistry(sources=sources)
        registry.load_skills()
        
        user_skills = registry.filter_by_origin(SkillOrigin.USER)
        ext_skills = registry.filter_by_origin(SkillOrigin.EXTENSIONS)
        
        assert len(user_skills) == 1
        assert user_skills[0]["name"] == "skill-a"
        assert len(ext_skills) == 1
        assert ext_skills[0]["name"] == "skill-b"


class TestManifestGeneration:
    """Tests for manifest generation."""
    
    def test_generate_manifest_structure(self, tmp_path):
        """Verify manifest has required fields."""
        skill_dir = tmp_path / "skills"
        skill_dir.mkdir()
        (skill_dir / "test-skill").mkdir()
        (skill_dir / "test-skill" / "SKILL.md").write_text("""---
name: test-skill
description: Test skill
---
""")
        
        sources = [(str(skill_dir), SkillOrigin.PROJECT)]
        registry = SkillRegistry(sources=sources)
        registry.load_skills()
        
        manifest = registry.generate_manifest()
        
        # Check required fields
        assert "generated_at" in manifest
        assert "submodule_commit" in manifest
        assert "skills" in manifest
        assert "by_origin" in manifest
        assert "total_skills" in manifest
        assert "counts" in manifest
        
        # Check timestamp format
        assert manifest["generated_at"].endswith("Z")
    
    def test_manifest_by_origin_grouping(self, tmp_path):
        """Verify skills are grouped correctly by origin in manifest."""
        user_dir = tmp_path / "user"
        user_dir.mkdir()
        (user_dir / "skill-a").mkdir()
        (user_dir / "skill-a" / "SKILL.md").write_text("---\nname: skill-a\n---\n")
        (user_dir / "skill-b").mkdir()
        (user_dir / "skill-b" / "SKILL.md").write_text("---\nname: skill-b\n---\n")
        
        ext_dir = tmp_path / "ext"
        ext_dir.mkdir()
        (ext_dir / "skill-c").mkdir()
        (ext_dir / "skill-c" / "SKILL.md").write_text("---\nname: skill-c\n---\n")
        
        sources = [
            (str(user_dir), SkillOrigin.USER),
            (str(ext_dir), SkillOrigin.EXTENSIONS),
        ]
        registry = SkillRegistry(sources=sources)
        registry.load_skills()
        
        manifest = registry.generate_manifest()
        
        assert "skill-a" in manifest["by_origin"]["user"]
        assert "skill-b" in manifest["by_origin"]["user"]
        assert "skill-c" in manifest["by_origin"]["extensions"]
        
        assert manifest["counts"]["user"] == 2
        assert manifest["counts"]["extensions"] == 1
    
    def test_empty_sources_returns_empty_manifest(self):
        """No sources should return empty but valid manifest."""
        registry = SkillRegistry(sources=[])
        registry.load_skills()
        
        manifest = registry.generate_manifest()
        
        assert manifest["total_skills"] == 0
        assert manifest["skills"] == []
        assert "generated_at" in manifest
    
    def test_manifest_includes_skill_details(self, tmp_path):
        """Verify manifest includes skill name, origin, path, description."""
        skill_dir = tmp_path / "skills"
        skill_dir.mkdir()
        (skill_dir / "my-skill").mkdir()
        (skill_dir / "my-skill" / "SKILL.md").write_text("""---
name: my-skill
description: A test skill for testing
---
""")
        
        sources = [(str(skill_dir), SkillOrigin.PROJECT)]
        registry = SkillRegistry(sources=sources)
        registry.load_skills()
        
        manifest = registry.generate_manifest()
        
        skill_entry = manifest["skills"][0]
        assert skill_entry["name"] == "my-skill"
        assert skill_entry["origin"] == "project"
        assert "my-skill" in skill_entry["path"]
        assert "test skill" in skill_entry["description"]
