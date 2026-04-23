"""Routing configuration contract.

Reads UIPATH_*-prefixed environment variables to keep parity with the rest
of the codebase. Precedence per tier:

  1. Tier-specific override (``UIPATH_CLAUDE_MODEL_HEAVY`` / ``_LIGHT``)
  2. Global override (``UIPATH_CLAUDE_MODEL``)
  3. Built-in default

Fallback resolution per tier:

  1. Tier-specific fallback override (``UIPATH_CLAUDE_MODEL_FALLBACK_HEAVY`` /
     ``_FALLBACK_LIGHT``)
  2. Built-in fallback default

Feature flags:
  - ``UIPATH_CLAUDE_ROUTING_DYNAMIC`` (default **on**) - enable complexity-
    driven routing in :func:`uipath_claude.llm.routing.complexity.select_model`.
    Set to ``0`` to fall back to static tier-only routing.
  - ``UIPATH_CLAUDE_FALLBACK_ENABLED`` (default **on**) - enable single-shot
    fallback retry in :class:`uipath_claude.llm.routing.invoker.Invoker`.
    Set to ``0`` to disable.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum


class ModelTier(str, Enum):
    """Capability tier for a Bedrock model selection."""

    HEAVY = "heavy"
    LIGHT = "light"


DEFAULT_HEAVY_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"
DEFAULT_LIGHT_MODEL = "anthropic.claude-3-5-haiku-20241022-v1:0"

DEFAULT_FALLBACK_HEAVY_MODEL = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
DEFAULT_FALLBACK_LIGHT_MODEL = "us.anthropic.claude-3-5-haiku-20241022-v1:0"

_TRUE = {"1", "true", "yes", "on"}


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE


@dataclass(frozen=True)
class RoutingConfig:
    """Resolved per-tier model IDs and feature flags."""

    heavy: str
    light: str
    fallback_heavy: str
    fallback_light: str
    routing_dynamic: bool
    fallback_enabled: bool

    def primary_for(self, tier: ModelTier) -> str:
        return self.heavy if tier is ModelTier.HEAVY else self.light

    def fallback_for(self, tier: ModelTier) -> str:
        return (
            self.fallback_heavy if tier is ModelTier.HEAVY else self.fallback_light
        )


def _resolve(env_tier: str, env_global: str, default: str) -> str:
    val = (os.environ.get(env_tier) or "").strip()
    if val:
        return val
    val = (os.environ.get(env_global) or "").strip()
    if val:
        return val
    return default


def _resolve_fallback(env_tier: str, default: str) -> str:
    val = (os.environ.get(env_tier) or "").strip()
    return val or default


def load_config() -> RoutingConfig:
    """Load configuration from environment using deterministic precedence."""
    return RoutingConfig(
        heavy=_resolve(
            "UIPATH_CLAUDE_MODEL_HEAVY", "UIPATH_CLAUDE_MODEL", DEFAULT_HEAVY_MODEL
        ),
        light=_resolve(
            "UIPATH_CLAUDE_MODEL_LIGHT", "UIPATH_CLAUDE_MODEL", DEFAULT_LIGHT_MODEL
        ),
        fallback_heavy=_resolve_fallback(
            "UIPATH_CLAUDE_MODEL_FALLBACK_HEAVY", DEFAULT_FALLBACK_HEAVY_MODEL
        ),
        fallback_light=_resolve_fallback(
            "UIPATH_CLAUDE_MODEL_FALLBACK_LIGHT", DEFAULT_FALLBACK_LIGHT_MODEL
        ),
        routing_dynamic=_flag("UIPATH_CLAUDE_ROUTING_DYNAMIC", default=True),
        fallback_enabled=_flag("UIPATH_CLAUDE_FALLBACK_ENABLED", default=True),
    )
