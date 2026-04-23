"""Tests for uipath_claude.llm.invoke (FallbackChatModel + helpers)."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from uipath_claude.llm.invoke import FallbackChatModel, build_chat_model
from uipath_claude.llm.routing.complexity import ComplexitySignals
from uipath_claude.llm.routing.telemetry import RecordingSink


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in (
        "UIPATH_CLAUDE_MODEL",
        "UIPATH_CLAUDE_MODEL_HEAVY",
        "UIPATH_CLAUDE_MODEL_LIGHT",
        "UIPATH_CLAUDE_MODEL_FALLBACK_HEAVY",
        "UIPATH_CLAUDE_MODEL_FALLBACK_LIGHT",
        "UIPATH_CLAUDE_ROUTING_DYNAMIC",
        "UIPATH_CLAUDE_FALLBACK_ENABLED",
        "UIPATH_CLAUDE_AUTO_INFERENCE_PROFILE",
        "UIPATH_CLAUDE_INFERENCE_PROFILE_REGION",
        "UIPATH_CLAUDE_ROUTING_TELEMETRY",
        "AWS_REGION",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("UIPATH_CLAUDE_MODEL_HEAVY", "PRIMARY-HEAVY")
    monkeypatch.setenv("UIPATH_CLAUDE_MODEL_LIGHT", "PRIMARY-LIGHT")
    monkeypatch.setenv("UIPATH_CLAUDE_MODEL_FALLBACK_HEAVY", "FB-HEAVY")
    monkeypatch.setenv("UIPATH_CLAUDE_MODEL_FALLBACK_LIGHT", "FB-LIGHT")
    monkeypatch.setenv("UIPATH_CLAUDE_ROUTING_TELEMETRY", "0")
    yield


class _FakeChat:
    """Records constructor model id and exposes invoke/ainvoke/astream/bind_tools."""

    instances: list["_FakeChat"] = []

    def __init__(self, *, model: str, region_name: str, **kwargs: Any) -> None:
        self.model = model
        self.region_name = region_name
        self.kwargs = kwargs
        self.invoke_calls: list[Any] = []
        self.ainvoke_calls: list[Any] = []
        self._invoke_side_effect: Any = None
        self._ainvoke_side_effect: Any = None
        _FakeChat.instances.append(self)

    def invoke(self, messages: Any) -> Any:
        self.invoke_calls.append(messages)
        if self._invoke_side_effect is not None:
            err = self._invoke_side_effect
            self._invoke_side_effect = None
            raise err
        return MagicMock(content=f"ok:{self.model}")

    async def ainvoke(self, messages: Any) -> Any:
        self.ainvoke_calls.append(messages)
        if self._ainvoke_side_effect is not None:
            err = self._ainvoke_side_effect
            self._ainvoke_side_effect = None
            raise err
        return MagicMock(content=f"ok:{self.model}")

    def bind_tools(self, tools: list[Any], **kwargs: Any) -> "_FakeChat":
        bound = _FakeChat(model=self.model, region_name=self.region_name, **kwargs)
        bound.tools = tools
        return bound

    def astream(self, messages: Any):
        async def _gen():
            chunk = MagicMock()
            chunk.content = f"chunk:{self.model}"
            yield chunk

        return _gen()


@pytest.fixture(autouse=True)
def _reset_fakes():
    _FakeChat.instances.clear()
    yield
    _FakeChat.instances.clear()


def test_build_chat_model_uses_resolved_primary_id():
    model = build_chat_model(
        task_id="planner",
        signals=ComplexitySignals(intent="build", planner_triggered=True),
        chat_cls=_FakeChat,
    )
    result = model.invoke([{"role": "user", "content": "hi"}])
    assert result.content == "ok:PRIMARY-HEAVY"
    assert _FakeChat.instances[0].model == "PRIMARY-HEAVY"


def test_invoke_falls_back_on_model_error():
    sink = RecordingSink()
    model = build_chat_model(
        task_id="planner",
        signals=ComplexitySignals(intent="question"),
        chat_cls=_FakeChat,
        sink=sink,
    )
    inner = model._ensure_inner()
    inner._invoke_side_effect = RuntimeError(
        "ResourceNotFoundException: model version has reached the end of its life"
    )

    result = model.invoke([{"role": "user", "content": "hi"}])
    assert result.content == "ok:FB-HEAVY"
    assert "fallback_triggered" in sink.names()
    assert "fallback_result" in sink.names()
    assert model.used_fallback is True


@pytest.mark.asyncio
async def test_ainvoke_falls_back_on_model_error():
    sink = RecordingSink()
    model = build_chat_model(
        task_id="planner",
        signals=ComplexitySignals(intent="question"),
        chat_cls=_FakeChat,
        sink=sink,
    )
    inner = model._ensure_inner()
    inner._ainvoke_side_effect = RuntimeError(
        "on-demand throughput isn't supported"
    )
    result = await model.ainvoke([{"role": "user", "content": "hi"}])
    assert result.content == "ok:FB-HEAVY"
    assert model.used_fallback is True


def test_non_model_error_does_not_trigger_fallback():
    sink = RecordingSink()
    model = build_chat_model(
        task_id="planner",
        signals=ComplexitySignals(intent="question"),
        chat_cls=_FakeChat,
        sink=sink,
    )
    inner = model._ensure_inner()
    inner._invoke_side_effect = ValueError("prompt parsing failed")
    with pytest.raises(ValueError):
        model.invoke([{"role": "user", "content": "hi"}])
    assert "fallback_triggered" not in sink.names()
    assert model.used_fallback is False


def test_fallback_disabled_propagates_error(monkeypatch):
    monkeypatch.setenv("UIPATH_CLAUDE_FALLBACK_ENABLED", "0")
    model = build_chat_model(
        task_id="planner",
        signals=ComplexitySignals(intent="question"),
        chat_cls=_FakeChat,
    )
    inner = model._ensure_inner()
    inner._invoke_side_effect = RuntimeError("ResourceNotFoundException")
    with pytest.raises(RuntimeError):
        model.invoke([{"role": "user", "content": "hi"}])
    assert model.used_fallback is False


def test_bind_tools_returns_wrapper_with_bound_inner():
    model = build_chat_model(
        task_id="agentic_executor",
        signals=ComplexitySignals(intent="build", planner_triggered=True),
        chat_cls=_FakeChat,
    )
    bound = model.bind_tools([{"name": "t1"}])
    assert isinstance(bound, FallbackChatModel)
    result = bound.invoke([{"role": "user", "content": "hi"}])
    assert result.content == "ok:PRIMARY-HEAVY"


def test_bind_tools_then_fallback_keeps_tools():
    """When fallback fires after bind_tools, the rebuilt inner must rebind tools."""
    sink = RecordingSink()
    model = build_chat_model(
        task_id="agentic_executor",
        signals=ComplexitySignals(intent="build", planner_triggered=True),
        chat_cls=_FakeChat,
        sink=sink,
    )
    bound = model.bind_tools([{"name": "t1"}])
    bound._inner._invoke_side_effect = RuntimeError("model not found")
    result = bound.invoke([{"role": "user", "content": "hi"}])
    assert result.content == "ok:FB-HEAVY"
    # The fallback inner should have tools bound (via _build's bound_tools branch)
    assert getattr(bound._inner, "tools", None) == [{"name": "t1"}]


def test_defaults_flipped(monkeypatch):
    """Both routing flags default to on."""
    from uipath_claude.llm.routing.config import load_config

    for var in (
        "UIPATH_CLAUDE_ROUTING_DYNAMIC",
        "UIPATH_CLAUDE_FALLBACK_ENABLED",
    ):
        monkeypatch.delenv(var, raising=False)
    cfg = load_config()
    assert cfg.routing_dynamic is True
    assert cfg.fallback_enabled is True

    monkeypatch.setenv("UIPATH_CLAUDE_ROUTING_DYNAMIC", "0")
    monkeypatch.setenv("UIPATH_CLAUDE_FALLBACK_ENABLED", "0")
    cfg = load_config()
    assert cfg.routing_dynamic is False
    assert cfg.fallback_enabled is False


def test_simple_answer_uses_helper(monkeypatch):
    """simple_llm_answer must construct via the fallback helper."""
    from uipath_claude.query import simple_answer as sa

    captured: dict[str, Any] = {}

    def fake_build(**kwargs):
        captured.update(kwargs)
        m = MagicMock()
        resp = MagicMock(content="answer")
        m.ainvoke = AsyncMock(return_value=resp)
        return m

    monkeypatch.setattr(sa, "build_chat_model", fake_build)
    import asyncio

    asyncio.run(sa.simple_llm_answer("q?", history=[], region="us-east-1"))
    assert captured["task_id"] == "planner"


def test_conversation_engine_uses_helper(monkeypatch):
    """ConversationEngine._get_llm must construct via the fallback helper."""
    from uipath_claude.query import conversation as conv

    captured: dict[str, Any] = {}

    def fake_build(**kwargs):
        captured.update(kwargs)
        return MagicMock()

    monkeypatch.setattr(conv, "build_chat_model", fake_build)
    eng = conv.ConversationEngine(model_name=None, region="us-east-1")
    eng._get_llm()
    assert captured["task_id"] == "conversation"


def test_clarifier_uses_helper(monkeypatch):
    from uipath_claude.query import clarifier as cl

    captured: dict[str, Any] = {}

    def fake_build(**kwargs):
        captured.update(kwargs)
        m = MagicMock()
        resp = MagicMock(content="clarify?")
        m.ainvoke = AsyncMock(return_value=resp)
        return m

    monkeypatch.setattr(cl, "build_chat_model", fake_build)
    import asyncio

    asyncio.run(cl.run_clarifier_agent("automate email", region="us-east-1"))
    assert captured["task_id"] == "clarifier"


def test_agentic_executor_uses_helper(monkeypatch):
    from uipath_claude.query import agentic_executor as ae

    captured: dict[str, Any] = {}

    def fake_build(**kwargs):
        captured.update(kwargs)
        m = MagicMock()
        m.bind_tools.return_value = m
        return m

    monkeypatch.setattr(ae, "build_chat_model", fake_build)
    ex = ae.AgenticExecutor(region="us-east-1")
    ex._get_llm()
    assert captured["task_id"] == "agentic_executor"
