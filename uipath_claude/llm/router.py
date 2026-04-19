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

# Inference-profile region prefixes accepted by Bedrock Converse for cross-region
# routing (e.g. ``us.anthropic.claude-sonnet-4-5-...``).
_INFERENCE_PROFILE_PREFIXES = ("us.", "eu.", "apac.", "us-gov.")

# Anthropic model families on Bedrock that are *not* available with on-demand
# throughput and therefore require an inference-profile id or a customer ARN.
# Sonnet 4.x and Opus 4.x both fall in this bucket today (2026-04). Sonnet 3.5
# and Haiku 3.5 are on-demand-eligible and excluded.
_REQUIRES_INFERENCE_PROFILE_PREFIXES = (
    "anthropic.claude-sonnet-4",
    "anthropic.claude-opus-4",
)

_warned_models: set[str] = set()
_rewritten_models: set[str] = set()

# Direct AWS docs links for operators verifying model IDs.
AWS_SUPPORTED_MODELS_URL = (
    "https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html"
)
AWS_INFERENCE_PROFILES_URL = (
    "https://docs.aws.amazon.com/bedrock/latest/userguide/"
    "cross-region-inference-support.html"
)

# Default cross-region prefix used when auto-rewriting profile-required ids.
# Override via ``UIPATH_CLAUDE_INFERENCE_PROFILE_REGION`` (e.g. ``eu``, ``apac``).
_DEFAULT_INFERENCE_REGION = "us"


def _looks_like_arn(model_id: str) -> bool:
    return model_id.startswith("arn:")


def requires_inference_profile(model_id: str) -> bool:
    """Return True when ``model_id`` must be invoked via an inference profile.

    Heuristic: matches raw Anthropic Sonnet/Opus 4.x ids that lack a regional
    inference-profile prefix (``us.``, ``eu.``, ``apac.``) and are not ARNs.
    """
    if not model_id:
        return False
    if _looks_like_arn(model_id):
        return False
    if model_id.startswith(_INFERENCE_PROFILE_PREFIXES):
        return False
    return any(model_id.startswith(p) for p in _REQUIRES_INFERENCE_PROFILE_PREFIXES)


def inference_profile_hint(model_id: str) -> str:
    """Return an operator hint for a model that needs a profile."""
    suggested = f"{_DEFAULT_INFERENCE_REGION}.{model_id}"
    return (
        f"Model '{model_id}' requires a Bedrock inference profile (no on-demand "
        f"throughput). Set UIPATH_CLAUDE_MODEL_HEAVY='{suggested}' (or another "
        f"regional profile / customer ARN). "
        f"Supported model IDs: {AWS_SUPPORTED_MODELS_URL} | "
        f"Cross-region profiles: {AWS_INFERENCE_PROFILES_URL}"
    )


def _autorewrite_enabled() -> bool:
    val = os.environ.get("UIPATH_CLAUDE_AUTO_INFERENCE_PROFILE", "1").strip().lower()
    return val in ("1", "true", "yes", "on")


def _profile_region() -> str:
    val = os.environ.get("UIPATH_CLAUDE_INFERENCE_PROFILE_REGION", "").strip().lower()
    return val or _DEFAULT_INFERENCE_REGION


def _maybe_rewrite_to_profile(model_id: str) -> str:
    """Rewrite a profile-required raw id to its cross-region profile form.

    Returns the original id when auto-rewrite is disabled or the id does not
    require a profile. Logs once per rewritten id so operators see what changed.
    """
    if not requires_inference_profile(model_id):
        return model_id
    if not _autorewrite_enabled():
        return model_id
    rewritten = f"{_profile_region()}.{model_id}"
    if model_id not in _rewritten_models:
        _rewritten_models.add(model_id)
        logger.warning(
            "Auto-rewriting Bedrock model id '%s' -> '%s' (profile required). "
            "Set UIPATH_CLAUDE_AUTO_INFERENCE_PROFILE=0 to disable. Refs: %s , %s",
            model_id,
            rewritten,
            AWS_SUPPORTED_MODELS_URL,
            AWS_INFERENCE_PROFILES_URL,
        )
    return rewritten


def _maybe_warn(model_id: str) -> None:
    if model_id in _warned_models:
        return
    if requires_inference_profile(model_id):
        _warned_models.add(model_id)
        logger.warning(inference_profile_hint(model_id))


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
    """Return the Bedrock model id to use for HEAVY-tier tasks.

    Inference-profile ids (``us.<model>``) and customer ARNs are passed through
    untouched. Raw model ids that require a profile (Sonnet/Opus 4.x) are
    auto-rewritten to their cross-region profile form (e.g. ``us.<model>``)
    so Bedrock accepts the call. Disable via
    ``UIPATH_CLAUDE_AUTO_INFERENCE_PROFILE=0``; configure region via
    ``UIPATH_CLAUDE_INFERENCE_PROFILE_REGION`` (``us`` | ``eu`` | ``apac``).
    """
    model = (
        os.environ.get("UIPATH_CLAUDE_MODEL_HEAVY", "").strip()
        or _legacy_override()
        or DEFAULT_HEAVY_MODEL
    )
    _maybe_warn(model)
    return _maybe_rewrite_to_profile(model)


def light_model() -> str:
    """Return the Bedrock model id to use for LIGHT-tier tasks.

    See :func:`heavy_model` for inference-profile handling.
    """
    model = (
        os.environ.get("UIPATH_CLAUDE_MODEL_LIGHT", "").strip()
        or _legacy_override()
        or DEFAULT_LIGHT_MODEL
    )
    _maybe_warn(model)
    return _maybe_rewrite_to_profile(model)


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
