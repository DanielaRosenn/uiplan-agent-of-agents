"""Integration tests for skill discovery with real UiPath skills repo."""

import pytest
from pathlib import Path
from agent.skill_discovery import SkillDiscovery


@pytest.mark.skipif(
    not (Path(__file__).parent.parent.parent / "skills").exists(),
    reason="UiPath skills submodule not initialized"
)
def test_discover_real_uipath_skills():
    """
    Integration test: discover skills from real UiPath repo.

    This test requires git submodule init.
    """
    skills_path = Path(__file__).parent.parent.parent / "skills"
    discovery = SkillDiscovery(skills_path)
    registry = discovery.discover_all_skills()

    # Should find at least the known skills
    assert len(registry) >= 5, f"Expected at least 5 skills, found {len(registry)}"

    # Check for known skills (as of design spec)
    expected_skills = [
        "uipath-rpa-workflows",
        "uipath-coded-workflows",
        "uipath-platform",
    ]

    for skill_name in expected_skills:
        assert skill_name in registry, f"Expected skill '{skill_name}' not found"

        skill = registry[skill_name]
        assert skill.name == skill_name
        assert skill.full_prompt  # SKILL.md loaded
        assert skill.skill_dir.exists()


@pytest.mark.skipif(
    not (Path(__file__).parent.parent.parent / "skills").exists(),
    reason="UiPath skills submodule not initialized"
)
def test_rpa_workflows_skill_has_references():
    """
    Integration test: uipath-rpa-workflows should have reference docs.
    """
    skills_path = Path(__file__).parent.parent.parent / "skills"
    discovery = SkillDiscovery(skills_path)
    registry = discovery.discover_all_skills()

    if "uipath-rpa-workflows" in registry:
        skill = registry["uipath-rpa-workflows"]

        # Should have references
        assert len(skill.references) > 0, "Expected reference docs in uipath-rpa-workflows"

        # Check reference files exist
        for ref in skill.references:
            assert ref.exists(), f"Reference file missing: {ref}"
