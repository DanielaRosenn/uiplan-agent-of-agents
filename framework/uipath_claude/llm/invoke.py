"""Shared LLM construction + invocation helper.

Single choke point that every chat-facing call site uses to build a
``ChatBedrockConverse`` and call it. Construction goes through
:func:`uipath_claude.llm.router.select_model_for_task` so dynamic routing
applies when enabled. Invocation goes through the routing
:class:`Invoker` so a single-shot fallback retry on model-related
failures is transparent to callers.

Why a wrapper class
-------------------
LangChain agents (and our own conversation engine) call ``invoke`` /
``ainvoke`` / ``astream`` repeatedly on the same model object. We can't
re-route every internal call from the outside, so :class:`FallbackChatModel`
holds an underlying ``ChatBedrockConverse`` and intercepts the call methods.
On a model-related failure it rebuilds the underlying with the tier's
fallback id and retries the same call once. ``bind_tools`` returns a fresh
proxy whose underlying client has the tools bound, so the wrapper survives
LangChain's tool-binding step.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Callable, Iterable

from langchain_aws import ChatBedrockConverse

from uipath_claude.llm.routing.complexity import ComplexitySignals, select_model
from uipath_claude.llm.routing.config import ModelTier, load_config
from uipath_claude.llm.routing.failures import classify_failure
from uipath_claude.llm.routing.telemetry import EventSink, NullSink

logger = logging.getLogger(__name__)

_DEFAULT_REGION = "us-east-1"


def _resolve_region(region: str | None) -> str:
    if region:
        return region
    return os.getenv("AWS_REGION", _DEFAULT_REGION)


def _tier_for(task_id: str) -> ModelTier:
    # Imported lazily to avoid circular import with router.py
    from uipath_claude.llm.router import _TASK_TIERS  # type: ignore

    return _TASK_TIERS.get(task_id, ModelTier.HEAVY)


def _resolve_primary_id(task_id: str, signals: ComplexitySignals | None) -> str:
    """Resolve the primary model id, honoring dynamic routing + auto-rewrite."""
    from uipath_claude.llm.router import _maybe_rewrite_to_profile, _maybe_warn  # type: ignore

    cfg = load_config()
    decision = select_model(cfg, signals, default_tier=_tier_for(task_id))
    _maybe_warn(decision.model_id)
    return _maybe_rewrite_to_profile(decision.model_id)


def _resolve_fallback_id(task_id: str) -> str:
    from uipath_claude.llm.router import _maybe_rewrite_to_profile  # type: ignore

    cfg = load_config()
    return _maybe_rewrite_to_profile(cfg.fallback_for(_tier_for(task_id)))


def _build_underlying(
    model_id: str,
    *,
    region: str,
    extra_kwargs: dict[str, Any] | None = None,
    chat_cls: type | None = None,
) -> Any:
    """Construct the raw ``ChatBedrockConverse`` (or test double) for ``model_id``."""
    cls = chat_cls or ChatBedrockConverse
    kwargs: dict[str, Any] = {"model": model_id, "region_name": region}
    if extra_kwargs:
        kwargs.update(extra_kwargs)
    return cls(**kwargs)


class FallbackChatModel:
    """Proxy around ``ChatBedrockConverse`` that adds single-shot fallback.

    Forwards arbitrary attribute access to the underlying client so LangChain
    treats it like a normal chat model. Intercepts ``invoke`` / ``ainvoke`` /
    ``stream`` / ``astream`` to apply fallback on model-related failures.
    ``bind_tools`` returns a new proxy whose underlying client has the tools
    bound, so the wrapper is preserved across the LangChain agent loop.
    """

    __slots__ = (
        "_task_id",
        "_signals",
        "_region",
        "_extra_kwargs",
        "_sink",
        "_chat_cls",
        "_inner",
        "_bound_tools",
        "_bind_kwargs",
        "_primary_id",
        "_used_fallback",
    )

    def __init__(
        self,
        *,
        task_id: str,
        signals: ComplexitySignals | None,
        region: str,
        extra_kwargs: dict[str, Any] | None,
        sink: EventSink | None,
        chat_cls: type | None,
        inner: Any | None = None,
        bound_tools: list[Any] | None = None,
        bind_kwargs: dict[str, Any] | None = None,
        primary_id: str | None = None,
    ) -> None:
        self._task_id = task_id
        self._signals = signals
        self._region = region
        self._extra_kwargs = dict(extra_kwargs) if extra_kwargs else None
        self._sink = sink or NullSink()
        self._chat_cls = chat_cls
        self._inner = inner
        self._bound_tools = list(bound_tools) if bound_tools else None
        self._bind_kwargs = dict(bind_kwargs) if bind_kwargs else None
        self._primary_id = primary_id
        self._used_fallback = False

    @property
    def model_id(self) -> str | None:
        """Resolved model id currently in use (after fallback if any)."""
        if self._used_fallback:
            return _resolve_fallback_id(self._task_id)
        return self._primary_id

    @property
    def used_fallback(self) -> bool:
        return self._used_fallback

    def _build(self, model_id: str) -> Any:
        underlying = _build_underlying(
            model_id,
            region=self._region,
            extra_kwargs=self._extra_kwargs,
            chat_cls=self._chat_cls,
        )
        if self._bound_tools:
            underlying = underlying.bind_tools(
                self._bound_tools, **(self._bind_kwargs or {})
            )
        return underlying

    def _ensure_inner(self) -> Any:
        if self._inner is None:
            self._primary_id = _resolve_primary_id(self._task_id, self._signals)
            self._sink.emit(
                "model_selected",
                {
                    "task_id": self._task_id,
                    "model_id": self._primary_id,
                    "tier": _tier_for(self._task_id).value,
                },
            )
            self._inner = self._build(self._primary_id)
        return self._inner

    def _swap_to_fallback(self) -> Any | None:
        cfg = load_config()
        if not cfg.fallback_enabled:
            return None
        fallback_id = _resolve_fallback_id(self._task_id)
        if not fallback_id or fallback_id == self._primary_id:
            self._sink.emit(
                "fallback_skipped_same_id",
                {"task_id": self._task_id, "model_id": self._primary_id},
            )
            return None
        self._sink.emit(
            "fallback_triggered",
            {
                "task_id": self._task_id,
                "from_model": self._primary_id,
                "to_model": fallback_id,
            },
        )
        self._inner = self._build(fallback_id)
        self._used_fallback = True
        return self._inner

    def _on_failure(self, err: BaseException) -> Any | None:
        """Return a rebuilt inner if fallback should be tried, else None."""
        classified = classify_failure(err)
        self._sink.emit(
            "model_call_failed",
            {
                "task_id": self._task_id,
                "model_id": self._primary_id,
                "category": classified.category.value,
                "model_related": classified.model_related,
            },
        )
        if not classified.model_related:
            return None
        if self._used_fallback:
            return None
        return self._swap_to_fallback()

    def _record_fallback_result(self, ok: bool, err: BaseException | None = None) -> None:
        payload: dict[str, Any] = {
            "task_id": self._task_id,
            "model_id": _resolve_fallback_id(self._task_id),
            "ok": ok,
        }
        if err is not None:
            payload["error"] = str(err)
        self._sink.emit("fallback_result", payload)

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        inner = self._ensure_inner()
        try:
            return inner.invoke(*args, **kwargs)
        except Exception as err:
            new_inner = self._on_failure(err)
            if new_inner is None:
                raise
            try:
                result = new_inner.invoke(*args, **kwargs)
            except Exception as fb_err:
                self._record_fallback_result(False, fb_err)
                raise
            self._record_fallback_result(True)
            return result

    async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:
        inner = self._ensure_inner()
        try:
            return await inner.ainvoke(*args, **kwargs)
        except Exception as err:
            new_inner = self._on_failure(err)
            if new_inner is None:
                raise
            try:
                result = await new_inner.ainvoke(*args, **kwargs)
            except Exception as fb_err:
                self._record_fallback_result(False, fb_err)
                raise
            self._record_fallback_result(True)
            return result

    def stream(self, *args: Any, **kwargs: Any) -> Any:
        inner = self._ensure_inner()
        try:
            return inner.stream(*args, **kwargs)
        except Exception as err:
            new_inner = self._on_failure(err)
            if new_inner is None:
                raise
            return new_inner.stream(*args, **kwargs)

    def astream(self, *args: Any, **kwargs: Any):
        # Returns an async iterator. Fallback only fires if construction of
        # the iterator (the synchronous part) raises; per-chunk failures mid
        # stream surface to the caller.
        inner = self._ensure_inner()
        try:
            return inner.astream(*args, **kwargs)
        except Exception as err:
            new_inner = self._on_failure(err)
            if new_inner is None:
                raise
            return new_inner.astream(*args, **kwargs)

    def bind_tools(self, tools: Iterable[Any], **kwargs: Any) -> "FallbackChatModel":
        tool_list = list(tools)
        inner = self._ensure_inner()
        bound = inner.bind_tools(tool_list, **kwargs)
        return FallbackChatModel(
            task_id=self._task_id,
            signals=self._signals,
            region=self._region,
            extra_kwargs=self._extra_kwargs,
            sink=self._sink,
            chat_cls=self._chat_cls,
            inner=bound,
            bound_tools=tool_list,
            bind_kwargs=kwargs,
            primary_id=self._primary_id,
        )

    def __getattr__(self, name: str) -> Any:
        # __slots__ entries handled normally; everything else proxies.
        inner = self._ensure_inner()
        return getattr(inner, name)


def build_chat_model(
    task_id: str,
    *,
    region: str | None = None,
    signals: ComplexitySignals | None = None,
    extra_kwargs: dict[str, Any] | None = None,
    sink: EventSink | None = None,
    chat_cls: type | None = None,
) -> FallbackChatModel:
    """Build a fallback-aware chat model for ``task_id``.

    The returned object behaves like ``ChatBedrockConverse`` for callers
    (``invoke`` / ``ainvoke`` / ``stream`` / ``astream`` / ``bind_tools``)
    and applies single-shot fallback on model-related failures when
    ``UIPATH_CLAUDE_FALLBACK_ENABLED`` is on (default on).
    """
    return FallbackChatModel(
        task_id=task_id,
        signals=signals,
        region=_resolve_region(region),
        extra_kwargs=extra_kwargs,
        sink=sink or default_sink(),
        chat_cls=chat_cls,
    )


async def ainvoke_chat(
    task_id: str,
    messages: Any,
    *,
    region: str | None = None,
    signals: ComplexitySignals | None = None,
    extra_kwargs: dict[str, Any] | None = None,
    sink: EventSink | None = None,
    chat_cls: type | None = None,
) -> Any:
    """Async one-shot invocation through fallback."""
    model = build_chat_model(
        task_id,
        region=region,
        signals=signals,
        extra_kwargs=extra_kwargs,
        sink=sink,
        chat_cls=chat_cls,
    )
    return await model.ainvoke(messages)


def invoke_chat(
    task_id: str,
    messages: Any,
    *,
    region: str | None = None,
    signals: ComplexitySignals | None = None,
    extra_kwargs: dict[str, Any] | None = None,
    sink: EventSink | None = None,
    chat_cls: type | None = None,
) -> Any:
    """Synchronous one-shot invocation through fallback."""
    model = build_chat_model(
        task_id,
        region=region,
        signals=signals,
        extra_kwargs=extra_kwargs,
        sink=sink,
        chat_cls=chat_cls,
    )
    return model.invoke(messages)


async def astream_chat(
    task_id: str,
    messages: Any,
    *,
    region: str | None = None,
    signals: ComplexitySignals | None = None,
    extra_kwargs: dict[str, Any] | None = None,
    sink: EventSink | None = None,
    chat_cls: type | None = None,
):
    """Async streaming generator. Yields chunks from the underlying model.

    Note: streaming uses the resolved primary model. Fallback only fires if
    constructing the iterator fails; per-chunk failures mid-stream surface
    to the caller (re-call via :func:`ainvoke_chat` to retry with fallback).
    """
    model = build_chat_model(
        task_id,
        region=region,
        signals=signals,
        extra_kwargs=extra_kwargs,
        sink=sink,
        chat_cls=chat_cls,
    )
    async for chunk in model.astream(messages):
        yield chunk


# --- Telemetry sink -----------------------------------------------------

class _StructuredLoggerSink:
    """EventSink adapter that emits routing events via :class:`StructuredLogger`."""

    def __init__(self) -> None:
        # Lazy import to keep the module light at import time.
        from uipath_claude.observability.logger import StructuredLogger

        self._log = StructuredLogger()

    def emit(self, event: str, payload: dict[str, Any]) -> None:
        try:
            self._log.emit(event=f"llm_routing.{event}", **payload)
        except Exception:
            pass


def default_sink() -> EventSink:
    """Return the default telemetry sink (NDJSON via StructuredLogger).

    Disable by setting ``UIPATH_CLAUDE_ROUTING_TELEMETRY=0``.
    """
    raw = os.environ.get("UIPATH_CLAUDE_ROUTING_TELEMETRY", "1").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return NullSink()
    try:
        return _StructuredLoggerSink()
    except Exception:
        return NullSink()


__all__ = [
    "FallbackChatModel",
    "ainvoke_chat",
    "astream_chat",
    "build_chat_model",
    "default_sink",
    "invoke_chat",
]
