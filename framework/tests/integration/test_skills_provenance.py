"""Integration tests for skill provenance and learning system."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from uipath_claude.skills.registry import SkillRegistry
from uipath_claude.skills.sources import SkillOrigin, build_skill_sources
from uipath_claude.skills.insights import (
    SkillInsight,
    SkillInsightsStore,
    InsightType,
    InsightLayer,
)
from uipath_claude.skills.usage_tracker import (
    SkillUsageTracker,
    SkillUsageEvent,
    create_usage_tracker,
)
from uipath_claude.skills.execution_hook import (
    track_skill_execution,
    post_skill_execution_hook,
)
from uipath_claude.commands.skills import generate_skills_manifest


@pytest.fixture
def project_with_skills(tmp_path):
    """Create a project structure with skills in multiple locations."""
    # Create extensions skills
    ext_skills = tmp_path / "extensions" / "skills"
    ext_skills.mkdir(parents=True)
    (ext_skills / "team-workflow").mkdir()
    (ext_skills / "team-workflow" / "SKILL.md").write_text("""---
name: team-workflow
description: Team workflow skill
---
# Team Workflow
""")
    
    # Create mock UiPath submodule skills
    submod_skills = tmp_path / "skills" / "skills"
    submod_skills.mkdir(parents=True)
    (submod_skills / "uipath-rpa").mkdir()
    (submod_skills / "uipath-rpa" / "SKILL.md").write_text("""---
name: uipath-rpa
description: UiPath RPA skill
---
# UiPath RPA
""")
    
    # Create project-local skills
    project_skills = tmp_path / ".uipath-claude" / "skills"
    project_skills.mkdir(parents=True)
    (project_skills / "local-override").mkdir()
    (project_skills / "local-override" / "SKILL.md").write_text("""---
name: local-override
description: Local override skill
---
# Local Override
""")
    
    # Create skill-insights directories
    (tmp_path / ".uipath-claude" / "skill-insights").mkdir(parents=True)
    (tmp_path / "extensions" / "skill-insights").mkdir(parents=True)
    
    return tmp_path


class TestSkillsProvenance:
    """Integration tests for skill provenance tracking."""
    
    def test_extensions_folder_discovery(self, project_with_skills):
        """Skills in extensions/skills/ discovered with correct origin."""
        sources = build_skill_sources(project_with_skills)
        registry = SkillRegistry(sources=sources, project_root=project_with_skills)
        registry.load_skills()
        
        # Find the team-workflow skill
        team_skill = registry.get_skill("team-workflow")
        assert team_skill is not None
        assert team_skill["origin"] == "extensions"
    
    def test_user_override_uipath_skill(self, project_with_skills):
        """Create user skill with same name as UiPath skill; verify user wins."""
        # Create a user skill with same name as submodule skill
        user_skills = project_with_skills / "user-skills"
        user_skills.mkdir()
        (user_skills / "uipath-rpa").mkdir()
        (user_skills / "uipath-rpa" / "SKILL.md").write_text("""---
name: uipath-rpa
description: User's custom RPA skill
---
# Custom RPA
""")
        
        # Build sources with user dir first
        sources = [
            (str(user_skills), SkillOrigin.USER),
            (str(project_with_skills / "skills" / "skills"), SkillOrigin.UIPATH_SUBMODULE),
        ]
        
        registry = SkillRegistry(sources=sources, project_root=project_with_skills)
        registry.load_skills()
        
        rpa_skill = registry.get_skill("uipath-rpa")
        assert rpa_skill is not None
        assert rpa_skill["origin"] == "user"
        assert "custom" in rpa_skill["description"].lower()
    
    def test_manifest_generation(self, project_with_skills):
        """Test generating manifest with provenance."""
        manifest = generate_skills_manifest(
            output_path=str(project_with_skills / "skills-manifest.json"),
            project_root=project_with_skills,
        )
        
        # Check manifest was created
        manifest_path = project_with_skills / "skills-manifest.json"
        assert manifest_path.exists()
        
        # Check manifest content
        assert manifest["total_skills"] >= 2
        assert "by_origin" in manifest
        assert "extensions" in manifest["by_origin"]
        assert "team-workflow" in manifest["by_origin"]["extensions"]


class TestSkillLearning:
    """Integration tests for skill learning system."""
    
    def test_insight_injected_on_skill_load(self, project_with_skills):
        """Loading skill includes insights_summary when insights exist."""
        # Add an insight for the team-workflow skill
        store = SkillInsightsStore(project_with_skills)
        insight = SkillInsight(
            skill_name="team-workflow",
            insight_type=InsightType.GOTCHA,
            content="Always check prerequisites first",
        )
        store.add_insight(insight, InsightLayer.PROJECT)
        
        # Get summary
        summary = store.get_summary("team-workflow")
        
        assert "prerequisites" in summary.lower()
        assert "Gotcha" in summary or "gotcha" in summary.lower()
    
    def test_auto_capture_on_failure(self, project_with_skills):
        """Execute skill, fail, verify insight created."""
        tracker = create_usage_tracker(project_with_skills)
        
        # Record a failure
        event = SkillUsageEvent(
            skill_name="team-workflow",
            started_at="2026-04-15T10:00:00Z",
            ended_at="2026-04-15T10:01:00Z",
            success=False,
            tool_calls=3,
            error_message="Connection timeout",
            context_summary="Trying to connect to service",
        )
        
        insight = tracker.record_usage(event)
        
        # Should have auto-captured a failure_pattern
        assert insight is not None
        assert insight.insight_type == InsightType.FAILURE_PATTERN
        assert "timeout" in insight.content.lower()
    
    def test_cross_session_persistence(self, project_with_skills):
        """Insight from session 1 visible in session 2."""
        # Session 1: Add insight
        store1 = SkillInsightsStore(project_with_skills)
        insight = SkillInsight(
            skill_name="team-workflow",
            insight_type=InsightType.SUCCESS_PATTERN,
            content="Use retry logic for network calls",
        )
        store1.add_insight(insight, InsightLayer.PROJECT)
        
        # Session 2: New store instance should see the insight
        store2 = SkillInsightsStore(project_with_skills)
        insights = store2.get_insights("team-workflow")
        
        assert len(insights) >= 1
        assert any("retry" in i.content.lower() for i in insights)
    
    def test_execution_context_tracking(self, project_with_skills):
        """Test tracking skill execution with context manager."""
        from uipath_claude.skills.execution_hook import SkillExecutionContext
        
        tracker = create_usage_tracker(project_with_skills)
        
        # Use the context manager with our tracker
        with SkillExecutionContext("team-workflow", tracker=tracker) as ctx:
            ctx.add_tool_call()
            ctx.add_tool_call()
            ctx.add_tool_call()
            ctx.set_context("Processing data")
        
        # Check stats from our tracker instance
        stats = tracker.get_skill_stats("team-workflow")
        assert stats["total_uses"] >= 1
    
    def test_complex_success_captures_edge_case(self, project_with_skills):
        """Complex success (5+ tool calls) should capture edge_case."""
        tracker = create_usage_tracker(project_with_skills)
        
        # Record a complex success
        event = SkillUsageEvent(
            skill_name="team-workflow",
            started_at="2026-04-15T10:00:00Z",
            ended_at="2026-04-15T10:05:00Z",
            success=True,
            tool_calls=7,
            context_summary="Handled complex data transformation",
        )
        
        insight = tracker.record_usage(event)
        
        # Should have auto-captured an edge_case
        assert insight is not None
        assert insight.insight_type == InsightType.EDGE_CASE
    
    def test_insight_stats_update(self, project_with_skills):
        """Test that insight stats are updated on usage."""
        store = SkillInsightsStore(project_with_skills)
        
        # Add an insight
        insight = SkillInsight(
            skill_name="team-workflow",
            insight_type=InsightType.GOTCHA,
            content="Check permissions first",
        )
        store.add_insight(insight, InsightLayer.PROJECT)
        
        # Update stats (simulating the insight was used and helped)
        store.update_insight_stats(
            "team-workflow",
            insight.content_hash,
            success=True,
            layer=InsightLayer.PROJECT,
        )
        
        # Verify stats were updated
        insights = store.get_insights("team-workflow")
        updated = next(i for i in insights if i.content_hash == insight.content_hash)
        assert updated.success_count == 1


class TestEndToEnd:
    """End-to-end integration tests."""
    
    def test_full_workflow(self, project_with_skills):
        """Test complete workflow: load skills, use, learn, query."""
        # 1. Load skills with provenance
        sources = build_skill_sources(project_with_skills)
        registry = SkillRegistry(sources=sources, project_root=project_with_skills)
        registry.load_skills()
        
        # 2. Verify provenance
        team_skill = registry.get_skill("team-workflow")
        assert team_skill["origin"] == "extensions"
        
        # 3. Use skill and capture insight
        tracker = create_usage_tracker(project_with_skills)
        event = SkillUsageEvent(
            skill_name="team-workflow",
            started_at="2026-04-15T10:00:00Z",
            ended_at="2026-04-15T10:01:00Z",
            success=False,
            tool_calls=2,
            error_message="Missing configuration",
        )
        insight = tracker.record_usage(event)
        
        assert insight is not None
        
        # 4. Query insights
        store = SkillInsightsStore(project_with_skills)
        summary = store.get_summary("team-workflow")
        
        assert "configuration" in summary.lower() or "Missing" in summary
        
        # 5. Generate manifest
        manifest = registry.generate_manifest()
        assert "team-workflow" in manifest["by_origin"]["extensions"]
