"""Shared LLM construction + invocation helper.

Single choke point that every chat-facing call site uses to build a
``ChatBedrockConverse`` and call it. Construction goes through
:func:`uipath_claude.llm.router.select_model_for_task` so dynamic routing
applies when enabled. Invocation goes through
:func:`uipath_claude.llm.router.invoke_with_fallback` so a single-shot
fallback retry on model-related failures is transparent to callers.

Why a wrapper class
-------------------
LangChain agents (and our own conversation engine) call ``invoke`` /
``ainvoke`` / ``astream`` repeatedly on the same model object. We can't
re-route every internal call from the outside, so :class:`FallbackChatModel`
proxies attribute access to an underlying ``ChatBedrockConverse`` and
intercepts the four call methods to wrap each in
:func:`invoke_with_fallback`. ``bind_tools`` rebinds onto a fresh proxy so
tool-bound chains stay fallback-aware.
"""
from __future__ import annotations

import os
from typing import Any, Callable, Iterable

from langchain_aws import ChatBedrockConverse

from uipath_claude.llm.router import (
    invoke_with_fallback,
    select_model_for_task,
)
from uipath_claude.llm.routing.complexity import ComplexitySignals
from uipath_claude.llm.routing.telemetry import EventSink

_DEFAULT_REGION = "us-east-1"


def _resolve_region(region: str | None) -> str:
    if region:
        return region
    return os.getenv("AWS_REGION", _DEFAULT_REGION)


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
    treats it like a normal chat model. Intercepts ``invoke``, ``ainvoke``,
    ``stream``, ``astream`` to route through
    :func:`uipath_claude.llm.router.invoke_with_fallback`. ``bind_tools``
    returns a new proxy whose underlying client has the tools bound, so the
    wrapper is preserved across the LangChain agent loop.
    """

    __slots__ = (
        "_task_id",
        "_signals",
        "_region",
        "_extra_kwargs",
        "_sink",
        "_chat_cls",
        "_inner",
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
    ) -> None:
        self._task_id = task_id
        self._signals = signals
        self._region = region
        self._extra_kwargs = dict(extra_kwargs) if extra_kwargs else None
        self._sink = sink
        self._chat_cls = chat_cls
        self._inner = inner

    def _build(self, model_id: str) -> Any:
        return _build_underlying(
            model_id,
            region=self._region,
            extra_kwargs=self._extra_kwargs,
            chat_cls=self._chat_cls,
        )

    def _ensure_inner(self) -> Any:
        if self._inner is None:
            primary = select_model_for_task(self._task_id, self._signals)
            self._inner = self._build(primary)
        return self._inner

    def _replace_inner_with(self, model_id: str, *, source: Any | None = None) -> Any:
        """Build a new underlying for ``model_id``; if ``source`` has tools bound, rebind."""
        new = self._build(model_id)
        bound_tools = None
        if source is not None:
            bound_tools = getattr(source, "_uipath_bound_tools", None)
            if bound_tools and hasattr(new, "bind_tools"):
                new = new.bind_tools(bound_tools)
                try:
                    setattr(new, "_uipath_bound_tools", bound_tools)
                except Exception:
                    pass
        self._inner = new
        return new

    def _route(self, op: Callable[[Any], Any]) -> Any:
        """Run ``op(inner)`` through the fallback invoker.

        On a model-related failure the invoker calls the closure again with
        the fallback model id; we rebuild ``self._inner`` for that id and
        re-run the same op so callers see one consistent client.
        """
        starting = self._ensure_inner()

        def call(model_id: str) -> Any:
            current = self._inner
            if current is None or getattr(current, "_uipath_model_id", None) != model_id:
                if (
                    starting is not None
                    and getattr(starting, "_uipath_model_id", None) == model_id
                ):
                    target = starting
                else:
                    target = self._replace_inner_with(model_id, source=starting)
            else:
                target = current
            try:
                setattr(target, "_uipath_model_id", model_id)
            except Exception:
                pass
            self._inner = target
            return op(target)

        result = invoke_with_fallback(
            call,
            task_id=self._task_id,
            signals=self._signals,
            sink=self._sink,
        )
        return result.value

    async def _route_async(self, op: Callable[[Any], Any]) -> Any:
        starting = self._ensure_inner()
        invocation_state: dict[str, Any] = {}

        def sync_call(model_id: str) -> Any:
            current = self._inner
            if current is None or getattr(current, "_uipath_model_id", None) != model_id:
                if (
                    starting is not None
                    and getattr(starting, "_uipath_model_id", None) == model_id
                ):
                    target = starting
                else:
                    target = self._replace_inner_with(model_id, source=starting)
            else:
                target = current
            try:
                setattr(target, "_uipath_model_id", model_id)
            except Exception:
                pass
            self._inner = target
            invocation_state["coro"] = op(target)
            return invocation_state

        # Resolve coroutine for primary; on model error, the invoker will call
        # sync_call again with the fallback id. We await the final coroutine
        # outside the invoker so exceptions surface in the right loop.
        try:
            invoke_with_fallback(
                sync_call,
                task_id=self._task_id,
                signals=self._signals,
                sink=self._sink,
            )
        except Exception:
            raise

        coro = invocation_state.get("coro")
        try:
            return await coro
        except Exception as primary_err:
            from uipath_claude.llm.routing.config import ModelTier, load_config
            from uipath_claude.llm.routing.failures import classify_failure

            cfg = load_config()
            classified = classify_failure(primary_err)
            if not (classified.model_related and cfg.fallback_enabled):
                raise

            primary_id = getattr(self._inner, "_uipath_model_id", None)
            tier = ModelTier.HEAVY if "heavy" in self._task_id else ModelTier.LIGHT
            from uipath_claude.llm.router import _TASK_TIERS  # type: ignore

            tier = _TASK_TIERS.get(self._task_id, tier)
            fallback_id = cfg.fallback_for(tier)
            if not fallback_id or fallback_id == primary_id:
                raise

            fallback_inner = self._replace_inner_with(fallback_id, source=starting)
            try:
                setattr(fallback_inner, "_uipath_model_id", fallback_id)
            except Exception:
                pass
            return await op(fallback_inner)

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        return self._route(lambda inner: inner.invoke(*args, **kwargs))

    async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:
        return await self._route_async(lambda inner: inner.ainvoke(*args, **kwargs))

    def stream(self, *args: Any, **kwargs: Any) -> Any:
        return self._route(lambda inner: inner.stream(*args, **kwargs))

    def astream(self, *args: Any, **kwargs: Any) -> Any:
        # ``astream`` returns an async iterator synchronously; just delegate
        # to the underlying client and let exceptions surface to the caller.
        # Fallback for streaming is best-effort: wrap one yield's worth.
        return self._ensure_inner().astream(*args, **kwargs)

    def bind_tools(self, tools: Iterable[Any], **kwargs: Any) -> "FallbackChatModel":
        inner = self._ensure_inner()
        bound = inner.bind_tools(tools, **kwargs)
        try:
            setattr(bound, "_uipath_model_id", getattr(inner, "_uipath_model_id", None))
            setattr(bound, "_uipath_bound_tools", list(tools))
        except Exception:
            pass
        new = FallbackChatModel(
            task_id=self._task_id,
            signals=self._signals,
            region=self._region,
            extra_kwargs=self._extra_kwargs,
            sink=self._sink,
            chat_cls=self._chat_cls,
            inner=bound,
        )
        return new

    def __getattr__(self, name: str) -> Any:
        # Slots fields handled normally; everything else proxies.
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
    and routes every call through
    :func:`uipath_claude.llm.router.invoke_with_fallback`.
    """
    return FallbackChatModel(
        task_id=task_id,
        signals=signals,
        region=_resolve_region(region),
        extra_kwargs=extra_kwargs,
        sink=sink,
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

    Note: streaming uses the resolved primary model only. Fallback is not
    attempted mid-stream; if the primary fails before producing a chunk the
    caller should retry via :func:`ainvoke_chat`.
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


__all__ = [
    "FallbackChatModel",
    "ainvoke_chat",
    "astream_chat",
    "build_chat_model",
    "invoke_chat",
]
