"""Tests for uipath_claude.llm.routing.invoker."""
from __future__ import annotations

import pytest

from uipath_claude.llm.routing.complexity import ComplexitySignals
from uipath_claude.llm.routing.config import ModelTier, RoutingConfig
from uipath_claude.llm.routing.invoker import FallbackError, Invoker
from uipath_claude.llm.routing.telemetry import RecordingSink


def _cfg(**overrides) -> RoutingConfig:
    base = dict(
        heavy="HEAVY-MODEL",
        light="LIGHT-MODEL",
        fallback_heavy="FB-HEAVY",
        fallback_light="FB-LIGHT",
        routing_dynamic=True,
        fallback_enabled=True,
    )
    base.update(overrides)
    return RoutingConfig(**base)


class _Counter:
    def __init__(self):
        self.calls: list[str] = []


def test_primary_success_no_fallback():
    sink = RecordingSink()
    inv = Invoker(_cfg(), sink=sink)
    counter = _Counter()

    def call(model_id: str) -> str:
        counter.calls.append(model_id)
        return f"ok:{model_id}"

    result = inv.invoke(call, ComplexitySignals(intent="question"))
    assert result.used_fallback is False
    assert result.value == "ok:LIGHT-MODEL"
    assert counter.calls == ["LIGHT-MODEL"]
    assert "fallback_triggered" not in sink.names()


def test_model_related_failure_triggers_fallback_once():
    sink = RecordingSink()
    inv = Invoker(_cfg(), sink=sink)
    counter = _Counter()

    def call(model_id: str) -> str:
        counter.calls.append(model_id)
        if model_id == "LIGHT-MODEL":
            raise RuntimeError("on-demand throughput isn't supported")
        return f"ok:{model_id}"

    result = inv.invoke(call, ComplexitySignals(intent="question"))
    assert result.used_fallback is True
    assert result.value == "ok:FB-LIGHT"
    assert counter.calls == ["LIGHT-MODEL", "FB-LIGHT"]
    assert "fallback_triggered" in sink.names()
    assert "fallback_result" in sink.names()


def test_non_model_failure_does_not_fallback():
    sink = RecordingSink()
    inv = Invoker(_cfg(), sink=sink)
    counter = _Counter()

    def call(model_id: str) -> str:
        counter.calls.append(model_id)
        raise ValueError("prompt parsing failed")

    with pytest.raises(ValueError):
        inv.invoke(call, ComplexitySignals(intent="question"))
    assert counter.calls == ["LIGHT-MODEL"]
    assert "fallback_triggered" not in sink.names()


def test_fallback_disabled_propagates_error():
    sink = RecordingSink()
    inv = Invoker(_cfg(fallback_enabled=False), sink=sink)
    counter = _Counter()

    def call(model_id: str) -> str:
        counter.calls.append(model_id)
        raise RuntimeError("on-demand throughput isn't supported")

    with pytest.raises(RuntimeError):
        inv.invoke(call, ComplexitySignals(intent="question"))
    assert counter.calls == ["LIGHT-MODEL"]


def test_fallback_failure_wraps_with_hint():
    sink = RecordingSink()
    inv = Invoker(_cfg(), sink=sink)

    def call(model_id: str) -> str:
        raise RuntimeError("on-demand throughput isn't supported")

    with pytest.raises(FallbackError) as exc:
        inv.invoke(call, ComplexitySignals(intent="question"))
    assert "Hint" in str(exc.value)


def test_no_loop_when_fallback_id_matches_primary():
    cfg = _cfg(fallback_light="LIGHT-MODEL")
    sink = RecordingSink()
    inv = Invoker(cfg, sink=sink)
    counter = _Counter()

    def call(model_id: str) -> str:
        counter.calls.append(model_id)
        raise RuntimeError("on-demand throughput isn't supported")

    with pytest.raises(RuntimeError):
        inv.invoke(call, ComplexitySignals(intent="question"))
    assert counter.calls == ["LIGHT-MODEL"]
    assert "fallback_skipped_same_id" in sink.names()


def test_telemetry_records_model_selected():
    sink = RecordingSink()
    inv = Invoker(_cfg(), sink=sink)

    inv.invoke(lambda m: "ok", ComplexitySignals(intent="question"))
    payloads = [p for name, p in sink.events if name == "model_selected"]
    assert payloads
    assert payloads[0]["tier"] == "light"
    assert payloads[0]["model_id"] == "LIGHT-MODEL"


def test_dynamic_routing_picks_heavy_for_complex_signal():
    sink = RecordingSink()
    inv = Invoker(_cfg(), sink=sink)

    result = inv.invoke(
        lambda m: m,
        ComplexitySignals(intent="build", planner_triggered=True),
    )
    assert result.decision.tier is ModelTier.HEAVY
    assert result.value == "HEAVY-MODEL"
