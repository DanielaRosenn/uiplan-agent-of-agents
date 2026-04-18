"""Tests for the tier-based Bedrock model router."""
from __future__ import annotations

import pytest

from uipath_claude.llm import router
from uipath_claude.llm.router import (
    DEFAULT_HEAVY_MODEL,
    DEFAULT_LIGHT_MODEL,
    ModelTier,
    heavy_model,
    light_model,
    model_for,
    model_for_task,
)


@pytest.fixture(autouse=True)
def _clear_model_env(monkeypatch):
    """Ensure no outer env leaks into the router tests."""
    for var in (
        "UIPATH_CLAUDE_MODEL",
        "UIPATH_CLAUDE_MODEL_HEAVY",
        "UIPATH_CLAUDE_MODEL_LIGHT",
    ):
        monkeypatch.delenv(var, raising=False)
    yield


def test_heavy_model_defaults():
    assert heavy_model() == DEFAULT_HEAVY_MODEL


def test_light_model_defaults():
    assert light_model() == DEFAULT_LIGHT_MODEL


def test_heavy_env_override_only_affects_heavy(monkeypatch):
    monkeypatch.setenv("UIPATH_CLAUDE_MODEL_HEAVY", "custom-heavy")
    assert heavy_model() == "custom-heavy"
    assert light_model() == DEFAULT_LIGHT_MODEL


def test_light_env_override_only_affects_light(monkeypatch):
    monkeypatch.setenv("UIPATH_CLAUDE_MODEL_LIGHT", "custom-light")
    assert light_model() == "custom-light"
    assert heavy_model() == DEFAULT_HEAVY_MODEL


def test_legacy_env_applies_to_both_tiers(monkeypatch):
    monkeypatch.setenv("UIPATH_CLAUDE_MODEL", "legacy-model")
    assert heavy_model() == "legacy-model"
    assert light_model() == "legacy-model"


def test_per_tier_env_beats_legacy(monkeypatch):
    monkeypatch.setenv("UIPATH_CLAUDE_MODEL", "legacy-model")
    monkeypatch.setenv("UIPATH_CLAUDE_MODEL_HEAVY", "heavy-override")
    assert heavy_model() == "heavy-override"
    assert light_model() == "legacy-model"


def test_model_for_task_heavy_and_light():
    assert model_for_task("ba_agent") == DEFAULT_HEAVY_MODEL
    assert model_for_task("distiller") == DEFAULT_LIGHT_MODEL


def test_model_for_task_unknown_falls_back_to_heavy():
    assert model_for_task("made-up-task") == DEFAULT_HEAVY_MODEL


def test_model_for_accepts_str_and_enum():
    assert model_for("heavy") == DEFAULT_HEAVY_MODEL
    assert model_for(ModelTier.LIGHT) == DEFAULT_LIGHT_MODEL


def test_register_task_is_picked_up(monkeypatch):
    router.register_task("ad_hoc_task", ModelTier.LIGHT)
    try:
        assert model_for_task("ad_hoc_task") == DEFAULT_LIGHT_MODEL
    finally:
        # Clean up to avoid leaking registration into other tests.
        router._TASK_TIERS.pop("ad_hoc_task", None)
