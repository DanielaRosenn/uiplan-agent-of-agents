"""Tests for uipath_claude.llm.routing.complexity."""
from __future__ import annotations

import pytest

from uipath_claude.llm.routing.complexity import (
    ComplexitySignals,
    score_complexity,
    select_model,
    tier_for_score,
)
from uipath_claude.llm.routing.config import ModelTier, RoutingConfig


def _cfg(**overrides) -> RoutingConfig:
    base = dict(
        heavy="HEAVY-MODEL",
        light="LIGHT-MODEL",
        fallback_heavy="FB-HEAVY",
        fallback_light="FB-LIGHT",
        routing_dynamic=True,
        fallback_enabled=False,
    )
    base.update(overrides)
    return RoutingConfig(**base)


def test_question_intent_scores_low():
    assert score_complexity(ComplexitySignals(intent="question")) == 0


def test_build_intent_scores_higher_than_question():
    q = score_complexity(ComplexitySignals(intent="question"))
    b = score_complexity(ComplexitySignals(intent="build"))
    assert b > q


def test_planner_pushes_above_threshold():
    sig = ComplexitySignals(intent="build", planner_triggered=True)
    assert score_complexity(sig) >= 7


def test_score_clamped_to_ten():
    sig = ComplexitySignals(
        intent="build",
        planner_triggered=True,
        estimated_steps=99,
        validation_error_count=99,
        files_affected=99,
    )
    assert score_complexity(sig) == 10


@pytest.mark.parametrize(
    "score,expected",
    [
        (0, ModelTier.LIGHT),
        (3, ModelTier.LIGHT),
        (6, ModelTier.LIGHT),
        (7, ModelTier.HEAVY),
        (10, ModelTier.HEAVY),
    ],
)
def test_tier_for_score_thresholds(score, expected):
    assert tier_for_score(score) == expected


def test_planner_forces_heavy_in_tier_helper():
    assert tier_for_score(0, planner_triggered=True) == ModelTier.HEAVY


def test_static_mode_ignores_signals():
    cfg = _cfg(routing_dynamic=False)
    decision = select_model(
        cfg,
        ComplexitySignals(intent="build", planner_triggered=True),
        default_tier=ModelTier.LIGHT,
    )
    assert decision.tier is ModelTier.LIGHT
    assert decision.model_id == "LIGHT-MODEL"
    assert decision.reason == "static_routing"


def test_dynamic_mode_uses_score():
    cfg = _cfg()
    light = select_model(cfg, ComplexitySignals(intent="question"))
    heavy = select_model(
        cfg, ComplexitySignals(intent="build", planner_triggered=True)
    )
    assert light.tier is ModelTier.LIGHT
    assert heavy.tier is ModelTier.HEAVY
    assert heavy.model_id == "HEAVY-MODEL"


def test_runtime_retries_escalate_to_heavy():
    cfg = _cfg()
    decision = select_model(
        cfg, ComplexitySignals(intent="question", runtime_retries=3)
    )
    assert decision.tier is ModelTier.HEAVY
    assert decision.escalated is True
    assert "runtime_retries" in decision.reason


def test_planner_escalation_marked_when_low_score():
    cfg = _cfg()
    decision = select_model(
        cfg, ComplexitySignals(intent="question", planner_triggered=True)
    )
    assert decision.tier is ModelTier.HEAVY
    assert decision.escalated is True
