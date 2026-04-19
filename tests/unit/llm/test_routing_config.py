"""Tests for uipath_claude.llm.routing.config."""
from __future__ import annotations

import pytest

from uipath_claude.llm.routing.config import (
    DEFAULT_FALLBACK_HEAVY_MODEL,
    DEFAULT_FALLBACK_LIGHT_MODEL,
    DEFAULT_HEAVY_MODEL,
    DEFAULT_LIGHT_MODEL,
    ModelTier,
    load_config,
)


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
    ):
        monkeypatch.delenv(var, raising=False)
    yield


def test_defaults_when_no_env():
    cfg = load_config()
    assert cfg.heavy == DEFAULT_HEAVY_MODEL
    assert cfg.light == DEFAULT_LIGHT_MODEL
    assert cfg.fallback_heavy == DEFAULT_FALLBACK_HEAVY_MODEL
    assert cfg.fallback_light == DEFAULT_FALLBACK_LIGHT_MODEL
    assert cfg.routing_dynamic is False
    assert cfg.fallback_enabled is False


def test_tier_specific_overrides_beat_global(monkeypatch):
    monkeypatch.setenv("UIPATH_CLAUDE_MODEL", "global-model")
    monkeypatch.setenv("UIPATH_CLAUDE_MODEL_HEAVY", "heavy-model")
    cfg = load_config()
    assert cfg.heavy == "heavy-model"
    assert cfg.light == "global-model"


def test_global_override_applies_to_both(monkeypatch):
    monkeypatch.setenv("UIPATH_CLAUDE_MODEL", "global-model")
    cfg = load_config()
    assert cfg.heavy == "global-model"
    assert cfg.light == "global-model"


def test_fallback_overrides_only_affect_fallback_slot(monkeypatch):
    monkeypatch.setenv("UIPATH_CLAUDE_MODEL_FALLBACK_HEAVY", "fb-heavy")
    cfg = load_config()
    assert cfg.fallback_heavy == "fb-heavy"
    assert cfg.fallback_light == DEFAULT_FALLBACK_LIGHT_MODEL
    assert cfg.heavy == DEFAULT_HEAVY_MODEL


def test_flags_parse_truthy_values(monkeypatch):
    monkeypatch.setenv("UIPATH_CLAUDE_ROUTING_DYNAMIC", "true")
    monkeypatch.setenv("UIPATH_CLAUDE_FALLBACK_ENABLED", "1")
    cfg = load_config()
    assert cfg.routing_dynamic is True
    assert cfg.fallback_enabled is True


def test_primary_and_fallback_for_helpers(monkeypatch):
    monkeypatch.setenv("UIPATH_CLAUDE_MODEL_HEAVY", "h")
    monkeypatch.setenv("UIPATH_CLAUDE_MODEL_LIGHT", "l")
    monkeypatch.setenv("UIPATH_CLAUDE_MODEL_FALLBACK_HEAVY", "fh")
    monkeypatch.setenv("UIPATH_CLAUDE_MODEL_FALLBACK_LIGHT", "fl")
    cfg = load_config()
    assert cfg.primary_for(ModelTier.HEAVY) == "h"
    assert cfg.primary_for(ModelTier.LIGHT) == "l"
    assert cfg.fallback_for(ModelTier.HEAVY) == "fh"
    assert cfg.fallback_for(ModelTier.LIGHT) == "fl"
