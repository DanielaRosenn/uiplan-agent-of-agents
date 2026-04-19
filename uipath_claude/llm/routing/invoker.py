"""Single-shot fallback invoker.

Wires routing + failure classifier + telemetry together. Calls the supplied
``ModelCall`` with the primary model id; on a model-related failure (and only
when ``UIPATH_CLAUDE_FALLBACK_ENABLED``), retries exactly once with the tier's
fallback model id. Non-model failures are re-raised immediately.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar

from uipath_claude.llm.routing.complexity import (
    ComplexitySignals,
    RoutingDecision,
    select_model,
)
from uipath_claude.llm.routing.config import ModelTier, RoutingConfig, load_config
from uipath_claude.llm.routing.failures import classify_failure
from uipath_claude.llm.routing.telemetry import EventSink, NullSink

T = TypeVar("T")

ModelCall = Callable[[str], T]


@dataclass(frozen=True)
class InvocationResult(Generic[T]):
    value: T
    decision: RoutingDecision
    used_fallback: bool
    fallback_reason: str | None = None


class FallbackError(RuntimeError):
    """Raised when both primary and fallback model calls fail."""


def _wrap_with_hint(err: BaseException, hint: str | None) -> FallbackError:
    base = f"Primary and fallback model calls both failed: {err}"
    if hint:
        return FallbackError(f"{base}\n\nHint: {hint}")
    return FallbackError(base)


class Invoker:
    """Stateless orchestrator; one instance can serve many calls."""

    def __init__(
        self,
        config: RoutingConfig | None = None,
        *,
        sink: EventSink | None = None,
    ) -> None:
        self.config = config or load_config()
        self.sink = sink or NullSink()

    def invoke(
        self,
        call: ModelCall[T],
        signals: ComplexitySignals | None = None,
        *,
        default_tier: ModelTier = ModelTier.LIGHT,
    ) -> InvocationResult[T]:
        decision = select_model(self.config, signals, default_tier=default_tier)
        self._emit(
            "model_selected",
            {
                "tier": decision.tier.value,
                "model_id": decision.model_id,
                "score": decision.score,
                "reason": decision.reason,
                "escalated": decision.escalated,
            },
        )

        try:
            value = call(decision.model_id)
            return InvocationResult(value=value, decision=decision, used_fallback=False)
        except Exception as primary_err:
            classified = classify_failure(primary_err)
            self._emit(
                "model_call_failed",
                {
                    "model_id": decision.model_id,
                    "category": classified.category.value,
                    "model_related": classified.model_related,
                },
            )

            if not (classified.model_related and self.config.fallback_enabled):
                raise

            fallback_model = self.config.fallback_for(decision.tier)
            if fallback_model == decision.model_id:
                self._emit(
                    "fallback_skipped_same_id",
                    {"model_id": decision.model_id, "tier": decision.tier.value},
                )
                raise

            self._emit(
                "fallback_triggered",
                {
                    "from_model": decision.model_id,
                    "to_model": fallback_model,
                    "category": classified.category.value,
                    "tier": decision.tier.value,
                },
            )

            try:
                value = call(fallback_model)
            except Exception as fb_err:
                self._emit(
                    "fallback_result",
                    {
                        "model_id": fallback_model,
                        "ok": False,
                        "error": str(fb_err),
                    },
                )
                raise _wrap_with_hint(fb_err, classified.hint) from fb_err

            self._emit(
                "fallback_result",
                {"model_id": fallback_model, "ok": True},
            )
            return InvocationResult(
                value=value,
                decision=decision,
                used_fallback=True,
                fallback_reason=classified.category.value,
            )

    def _emit(self, event: str, payload: dict[str, Any]) -> None:
        self.sink.emit(event, payload)
