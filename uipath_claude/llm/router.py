"""Tier-based Bedrock model router.

Single source of truth for model selection. Call sites pick a tier
(``HEAVY`` for BA/SA/Dev/QA/planner/agentic executor, ``LIGHT`` for
distillation/classification/short-text tasks) or a task id; resolution
walks per-tier env overrides, then the legacy global override, then a
hard-coded default.
"""
from __future__ import annotations

import logging
import os
from enum import Enum


logger = logging.getLogger(__name__)


class ModelTier(str, Enum):
    """Capability tier for a Bedrock model selection."""

    HEAVY = "heavy"
    LIGHT = "light"


DEFAULT_HEAVY_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"
DEFAULT_LIGHT_MODEL = "anthropic.claude-3-5-haiku-20241022-v1:0"


_TASK_TIERS: dict[str, ModelTier] = {
    "ba_agent": ModelTier.HEAVY,
    "solution_architect": ModelTier.HEAVY,
    "developer": ModelTier.HEAVY,
    "qa": ModelTier.HEAVY,
    "planner": ModelTier.HEAVY,
    "agentic_executor": ModelTier.HEAVY,
    "distiller": ModelTier.LIGHT,
    "intent_classifier": ModelTier.LIGHT,
    "doc_need_detector": ModelTier.LIGHT,
    "rename_summary": ModelTier.LIGHT,
}


def _legacy_override() -> str | None:
    val = os.environ.get("UIPATH_CLAUDE_MODEL", "").strip()
    return val or None


def heavy_model() -> str:
    """Return the Bedrock model id to use for HEAVY-tier tasks."""
    return (
        os.environ.get("UIPATH_CLAUDE_MODEL_HEAVY", "").strip()
        or _legacy_override()
        or DEFAULT_HEAVY_MODEL
    )


def light_model() -> str:
    """Return the Bedrock model id to use for LIGHT-tier tasks."""
    return (
        os.environ.get("UIPATH_CLAUDE_MODEL_LIGHT", "").strip()
        or _legacy_override()
        or DEFAULT_LIGHT_MODEL
    )


def model_for(tier: ModelTier | str) -> str:
    """Return the model id for a given tier."""
    resolved = tier if isinstance(tier, ModelTier) else ModelTier(str(tier).lower())
    return heavy_model() if resolved is ModelTier.HEAVY else light_model()


def model_for_task(task_id: str) -> str:
    """Return the model id for a named task.

    Unknown task ids fall back to HEAVY (safe default). Each resolution
    emits one debug line so routing is observable in logs.
    """
    tier = _TASK_TIERS.get(task_id, ModelTier.HEAVY)
    model = model_for(tier)
    logger.debug("model_router task=%s tier=%s model=%s", task_id, tier.value, model)
    return model


def register_task(task_id: str, tier: ModelTier) -> None:
    """Register/override a task -> tier mapping (used by extensions/tests)."""
    _TASK_TIERS[task_id] = tier


def task_tiers() -> dict[str, ModelTier]:
    """Return a copy of the current task -> tier map."""
    return dict(_TASK_TIERS)
