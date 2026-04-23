"""Routing subpackage: complexity-driven model selection + fallback.

Backs the public API in :mod:`uipath_claude.llm.router`. New flags
(``UIPATH_CLAUDE_ROUTING_DYNAMIC``, ``UIPATH_CLAUDE_FALLBACK_ENABLED``) are
opt-in; default behavior matches the legacy static tier router.
"""
from uipath_claude.llm.routing.complexity import (
    ComplexitySignals,
    RoutingDecision,
    score_complexity,
    select_model,
    tier_for_score,
)
from uipath_claude.llm.routing.config import (
    DEFAULT_FALLBACK_HEAVY_MODEL,
    DEFAULT_FALLBACK_LIGHT_MODEL,
    DEFAULT_HEAVY_MODEL,
    DEFAULT_LIGHT_MODEL,
    ModelTier,
    RoutingConfig,
    load_config,
)
from uipath_claude.llm.routing.failures import (
    ClassifiedFailure,
    FailureCategory,
    classify_failure,
)
from uipath_claude.llm.routing.invoker import (
    FallbackError,
    InvocationResult,
    Invoker,
    ModelCall,
)
from uipath_claude.llm.routing.telemetry import EventSink, NullSink, RecordingSink

__all__ = [
    "ClassifiedFailure",
    "ComplexitySignals",
    "DEFAULT_FALLBACK_HEAVY_MODEL",
    "DEFAULT_FALLBACK_LIGHT_MODEL",
    "DEFAULT_HEAVY_MODEL",
    "DEFAULT_LIGHT_MODEL",
    "EventSink",
    "FailureCategory",
    "FallbackError",
    "InvocationResult",
    "Invoker",
    "ModelCall",
    "ModelTier",
    "NullSink",
    "RecordingSink",
    "RoutingConfig",
    "RoutingDecision",
    "classify_failure",
    "load_config",
    "score_complexity",
    "select_model",
    "tier_for_score",
]
