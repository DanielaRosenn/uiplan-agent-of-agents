"""Tests for skill discovery system."""

import pytest
from pathlib import Path
from agent.skill_discovery import SkillMetadata, SkillDiscovery


def test_skill_metadata_stores_basic_info(temp_skills_repo):
    """SkillMetadata should store name, description, and prompt."""
    # This will fail until we implement SkillMetadata
    meta = SkillMetadata(
        name="test-skill",
        description="Test description",
        trigger_patterns=["test"],
        references=[],
        assets=[],
        full_prompt="# Test Skill",
        skill_dir=Path("/tmp/test"),
    )

    assert meta.name == "test-skill"
    assert meta.description == "Test description"
    assert meta.trigger_patterns == ["test"]
    assert meta.full_prompt == "# Test Skill"
    assert isinstance(meta.skill_dir, Path)


def test_skill_discovery_finds_all_skills(temp_skills_repo):
    """SkillDiscovery should find all valid skills."""
    discovery = SkillDiscovery(temp_skills_repo)
    registry = discovery.discover_all_skills()

    # Should find test-skill-1 and test-skill-2, but not invalid-skill
    assert len(registry) == 2
    assert "test-skill-1" in registry
    assert "test-skill-2" in registry
    assert "invalid-skill" not in registry


def test_extract_triggers_from_description():
    """Should extract trigger patterns from TRIGGER when: section."""
    discovery = SkillDiscovery(Path("/tmp"))

    description = """
    Test skill description.
    TRIGGER when: coded workflow projects detected, .cs files present
    DO NOT TRIGGER when: pure XAML workflows
    """

    triggers = discovery._extract_triggers(description)

    assert len(triggers) == 2
    assert "coded workflow projects detected" in triggers
    assert ".cs files present" in triggers


def test_extract_triggers_handles_newlines():
    """Should handle newline-separated triggers."""
    discovery = SkillDiscovery(Path("/tmp"))

    description = """
    TRIGGER when:
      - coded workflow
      - C# activities
      - API integration
    """

    triggers = discovery._extract_triggers(description)

    assert len(triggers) >= 1
    # At least one trigger should be extracted


def test_extract_triggers_returns_empty_when_none():
    """Should return empty list when no TRIGGER when: section."""
    discovery = SkillDiscovery(Path("/tmp"))

    description = "Simple description without triggers"
    triggers = discovery._extract_triggers(description)

    assert triggers == []
