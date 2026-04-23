"""Tests for skill insights - runtime learning system."""
import json
from pathlib import Path

import pytest

from uipath_claude.skills.insights import (
    SkillInsight,
    SkillInsightsStore,
    SkillInsightsFile,
    InsightType,
    InsightLayer,
)


class TestInsightType:
    """Tests for InsightType enum."""
    
    def test_insight_types_enum(self):
        """Verify all InsightType values are valid."""
        assert InsightType.SUCCESS_PATTERN.value == "success_pattern"
        assert InsightType.FAILURE_PATTERN.value == "failure_pattern"
        assert InsightType.EDGE_CASE.value == "edge_case"
        assert InsightType.GOTCHA.value == "gotcha"
        assert InsightType.IMPROVEMENT.value == "improvement"
        assert InsightType.CONTEXT_TIP.value == "context_tip"
    
    def test_all_insight_types_exist(self):
        """Verify we have 6 insight types."""
        assert len(list(InsightType)) == 6


class TestSkillInsight:
    """Tests for SkillInsight dataclass."""
    
    def test_insight_creation(self):
        """Test creating a SkillInsight."""
        insight = SkillInsight(
            skill_name="test-skill",
            insight_type=InsightType.GOTCHA,
            content="Test content",
        )
        assert insight.skill_name == "test-skill"
        assert insight.insight_type == InsightType.GOTCHA
        assert insight.content == "Test content"
        assert insight.source == "agent"
    
    def test_confidence_calculation(self):
        """Test confidence score calculation."""
        insight = SkillInsight(
            skill_name="test",
            insight_type=InsightType.GOTCHA,
            content="Test",
            success_count=8,
            failure_count=2,
        )
        assert insight.confidence == 0.8
    
    def test_confidence_no_data(self):
        """Test confidence with no usage data."""
        insight = SkillInsight(
            skill_name="test",
            insight_type=InsightType.GOTCHA,
            content="Test",
        )
        assert insight.confidence == 1.0
    
    def test_content_hash_deterministic(self):
        """Test content hash is deterministic."""
        insight1 = SkillInsight(
            skill_name="test",
            insight_type=InsightType.GOTCHA,
            content="Same content",
        )
        insight2 = SkillInsight(
            skill_name="test",
            insight_type=InsightType.GOTCHA,
            content="Same content",
        )
        assert insight1.content_hash == insight2.content_hash
    
    def test_content_hash_case_insensitive(self):
        """Test content hash ignores case."""
        insight1 = SkillInsight(
            skill_name="test",
            insight_type=InsightType.GOTCHA,
            content="Same Content",
        )
        insight2 = SkillInsight(
            skill_name="test",
            insight_type=InsightType.GOTCHA,
            content="same content",
        )
        assert insight1.content_hash == insight2.content_hash
    
    def test_to_dict_and_from_dict(self):
        """Test serialization round-trip."""
        insight = SkillInsight(
            skill_name="test-skill",
            insight_type=InsightType.SUCCESS_PATTERN,
            content="It works!",
            context="After fixing bug",
            success_count=5,
            failure_count=1,
        )
        
        d = insight.to_dict()
        restored = SkillInsight.from_dict(d)
        
        assert restored.skill_name == insight.skill_name
        assert restored.insight_type == insight.insight_type
        assert restored.content == insight.content
        assert restored.context == insight.context
        assert restored.success_count == insight.success_count


class TestSkillInsightsStore:
    """Tests for SkillInsightsStore."""
    
    @pytest.fixture
    def store(self, tmp_path):
        """Create a store with tmp_path as project root."""
        return SkillInsightsStore(tmp_path)
    
    def test_add_insight_to_layer(self, store, tmp_path):
        """Test adding insight to user/project/shared layer."""
        insight = SkillInsight(
            skill_name="test-skill",
            insight_type=InsightType.GOTCHA,
            content="Test insight",
        )
        
        # Add to project layer
        result = store.add_insight(insight, InsightLayer.PROJECT)
        assert result is True
        
        # Verify file was created
        path = tmp_path / ".uipath-claude" / "skill-insights" / "test-skill.json"
        assert path.exists()
        
        data = json.loads(path.read_text())
        assert data["skill_name"] == "test-skill"
        assert len(data["insights"]) == 1
    
    def test_deduplication(self, store):
        """Test duplicate insights are rejected."""
        insight1 = SkillInsight(
            skill_name="test-skill",
            insight_type=InsightType.GOTCHA,
            content="Same content",
        )
        insight2 = SkillInsight(
            skill_name="test-skill",
            insight_type=InsightType.GOTCHA,
            content="Same content",
        )
        
        result1 = store.add_insight(insight1, InsightLayer.PROJECT)
        result2 = store.add_insight(insight2, InsightLayer.PROJECT)
        
        assert result1 is True
        assert result2 is False  # Duplicate rejected
    
    def test_layered_resolution(self, store, tmp_path):
        """Test user insight overrides project insight."""
        # Add insight to project layer
        project_insight = SkillInsight(
            skill_name="test-skill",
            insight_type=InsightType.GOTCHA,
            content="Project version",
        )
        store.add_insight(project_insight, InsightLayer.PROJECT)
        
        # Add same-hash insight to user layer
        user_insight = SkillInsight(
            skill_name="test-skill",
            insight_type=InsightType.GOTCHA,
            content="User version",
        )
        
        # Manually create user layer file
        user_path = tmp_path / "home" / ".cursor" / "skill-insights"
        user_path.mkdir(parents=True)
        
        # Update store's layers to use our mock home
        store.layers[InsightLayer.USER] = user_path
        store.add_insight(user_insight, InsightLayer.USER)
        
        # Get merged insights - user should come first
        insights = store.get_insights("test-skill")
        
        # Should have both (different content hashes)
        assert len(insights) == 2
        # User layer comes first
        assert insights[0].content == "User version"
    
    def test_get_summary_token_bounded(self, store):
        """Test summary respects max_tokens parameter."""
        # Add multiple insights
        for i in range(10):
            insight = SkillInsight(
                skill_name="test-skill",
                insight_type=InsightType.GOTCHA,
                content=f"This is insight number {i} with some extra text to take up space",
            )
            store.add_insight(insight, InsightLayer.PROJECT)
        
        # Get summary with small token limit
        summary = store.get_summary("test-skill", max_tokens=50)
        
        # Should be bounded (50 tokens * 4 chars = 200 chars max)
        assert len(summary) <= 250  # Some buffer for formatting
    
    def test_get_summary_empty_skill(self, store):
        """Test summary for skill with no insights."""
        summary = store.get_summary("nonexistent-skill")
        assert summary == ""
    
    def test_get_summary_prioritizes_gotchas(self, store):
        """Test summary shows gotchas before other types."""
        # Add different types
        store.add_insight(SkillInsight(
            skill_name="test-skill",
            insight_type=InsightType.SUCCESS_PATTERN,
            content="Success pattern",
        ), InsightLayer.PROJECT)
        
        store.add_insight(SkillInsight(
            skill_name="test-skill",
            insight_type=InsightType.GOTCHA,
            content="Important gotcha",
        ), InsightLayer.PROJECT)
        
        summary = store.get_summary("test-skill")
        
        # Gotcha should appear before success pattern
        gotcha_pos = summary.find("Important gotcha")
        success_pos = summary.find("Success pattern")
        
        assert gotcha_pos < success_pos
    
    def test_update_insight_stats(self, store):
        """Test updating success/failure counts."""
        insight = SkillInsight(
            skill_name="test-skill",
            insight_type=InsightType.GOTCHA,
            content="Test content",
        )
        store.add_insight(insight, InsightLayer.PROJECT)
        
        # Update stats
        store.update_insight_stats(
            "test-skill",
            insight.content_hash,
            success=True,
            layer=InsightLayer.PROJECT,
        )
        
        # Get insights and check stats
        insights = store.get_insights("test-skill")
        assert insights[0].success_count == 1
        assert insights[0].failure_count == 0
    
    def test_propose_insight(self, store, tmp_path):
        """Test proposing insight for human review."""
        insight = SkillInsight(
            skill_name="test-skill",
            insight_type=InsightType.IMPROVEMENT,
            content="Add more examples",
        )
        
        path = store.propose_insight(insight)
        
        assert path.exists()
        assert "proposals" in str(path)
        
        data = json.loads(path.read_text())
        assert data["insights"][0]["source"] == "proposal"


class TestSkillInsightsFile:
    """Tests for SkillInsightsFile dataclass."""
    
    def test_to_dict_and_from_dict(self):
        """Test serialization round-trip."""
        file = SkillInsightsFile(
            skill_name="test-skill",
            insights=[
                SkillInsight(
                    skill_name="test-skill",
                    insight_type=InsightType.GOTCHA,
                    content="Test",
                )
            ],
            stats={"total_uses": 10},
        )
        
        d = file.to_dict()
        restored = SkillInsightsFile.from_dict(d)
        
        assert restored.skill_name == file.skill_name
        assert len(restored.insights) == 1
        assert restored.stats["total_uses"] == 10