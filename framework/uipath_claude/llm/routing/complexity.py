"""Hybrid intent+complexity routing engine.

Builds a normalized 0-10 ``complexity_score`` from caller-supplied signals,
maps it to a :class:`ModelTier`, then resolves a concrete model id via
:class:`RoutingConfig`.

Escalation rules (applied AFTER score-to-tier mapping):
- ``planner_triggered`` forces ``HEAVY``.
- ``runtime_retries >= RETRY_ESCALATION_THRESHOLD`` forces ``HEAVY``.

When ``RoutingConfig.routing_dynamic`` is False, signals are ignored and the
caller-provided ``default_tier`` is used (static behavior).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from uipath_claude.llm.routing.config import ModelTier, RoutingConfig

Intent = Literal["question", "documentation", "build", "ambiguous"]


_INTENT_WEIGHT: dict[Intent, int] = {
    "question": 0,
    "documentation": 1,
    "ambiguous": 3,
    "build": 4,
}

RETRY_ESCALATION_THRESHOLD = 2
PLANNER_BONUS = 3
MULTI_STEP_BONUS_PER_STEP = 1
MAX_STEP_BONUS = 3
VALIDATION_ERROR_BONUS_PER_3 = 1
MAX_VALIDATION_BONUS = 2
MULTI_FILE_BONUS_PER_5 = 1
MAX_FILE_BONUS = 2


@dataclass(frozen=True)
class ComplexitySignals:
    """Inputs to :func:`score_complexity`. All fields optional."""

    intent: Intent = "ambiguous"
    planner_triggered: bool = False
    estimated_steps: int = 0
    validation_error_count: int = 0
    files_affected: int = 0
    runtime_retries: int = 0


@dataclass(frozen=True)
class RoutingDecision:
    tier: ModelTier
    model_id: str
    score: int
    reason: str
    escalated: bool = False
    signals: ComplexitySignals = field(default_factory=ComplexitySignals)


def score_complexity(signals: ComplexitySignals) -> int:
    """Return a clamped 0-10 complexity score from caller signals."""
    score = _INTENT_WEIGHT.get(signals.intent, 3)
    if signals.planner_triggered:
        score += PLANNER_BONUS
    if signals.estimated_steps > 0:
        score += min(MAX_STEP_BONUS, signals.estimated_steps * MULTI_STEP_BONUS_PER_STEP)
    if signals.validation_error_count > 0:
        score += min(
            MAX_VALIDATION_BONUS,
            signals.validation_error_count // 3 * VALIDATION_ERROR_BONUS_PER_3
            or (1 if signals.validation_error_count >= 3 else 0),
        )
    if signals.files_affected > 0:
        score += min(
            MAX_FILE_BONUS,
            signals.files_affected // 5 * MULTI_FILE_BONUS_PER_5
            or (1 if signals.files_affected >= 5 else 0),
        )
    return max(0, min(10, score))


def tier_for_score(score: int, *, planner_triggered: bool = False) -> ModelTier:
    """Map a 0-10 score to a tier, honoring the planner override."""
    if planner_triggered:
        return ModelTier.HEAVY
    if score >= 7:
        return ModelTier.HEAVY
    return ModelTier.LIGHT


def select_model(
    config: RoutingConfig,
    signals: ComplexitySignals | None = None,
    *,
    default_tier: ModelTier = ModelTier.LIGHT,
) -> RoutingDecision:
    """Pick a primary model id given config + signals.

    Static mode (``config.routing_dynamic`` False) returns ``default_tier``
    immediately. Dynamic mode applies score+escalation rules.
    """
    sig = signals or ComplexitySignals()

    if not config.routing_dynamic:
        return RoutingDecision(
            tier=default_tier,
            model_id=config.primary_for(default_tier),
            score=0,
            reason="static_routing",
            escalated=False,
            signals=sig,
        )

    score = score_complexity(sig)
    base_tier = tier_for_score(score, planner_triggered=sig.planner_triggered)
    escalated = False
    reason = f"score={score}"

    if sig.planner_triggered and base_tier is ModelTier.HEAVY and score < 7:
        escalated = True
        reason = f"planner_triggered (score={score})"

    if (
        base_tier is ModelTier.LIGHT
        and sig.runtime_retries >= RETRY_ESCALATION_THRESHOLD
    ):
        base_tier = ModelTier.HEAVY
        escalated = True
        reason = f"runtime_retries={sig.runtime_retries}"

    return RoutingDecision(
        tier=base_tier,
        model_id=config.primary_for(base_tier),
        score=score,
        reason=reason,
        escalated=escalated,
        signals=sig,
    )
