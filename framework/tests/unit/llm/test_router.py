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
        "UIPATH_CLAUDE_AUTO_INFERENCE_PROFILE",
        "UIPATH_CLAUDE_INFERENCE_PROFILE_REGION",
    ):
        monkeypatch.delenv(var, raising=False)
    router._warned_models.clear()
    router._rewritten_models.clear()
    yield
    router._warned_models.clear()
    router._rewritten_models.clear()


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


def test_requires_inference_profile_for_sonnet_4():
    assert router.requires_inference_profile(
        "anthropic.claude-sonnet-4-5-20250929-v1:0"
    )


def test_requires_inference_profile_passes_through_us_prefix():
    assert not router.requires_inference_profile(
        "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    )


def test_requires_inference_profile_passes_through_arn():
    assert not router.requires_inference_profile(
        "arn:aws:bedrock:us-east-1:123:inference-profile/foo"
    )


def test_requires_inference_profile_false_for_sonnet_3_5():
    assert not router.requires_inference_profile(DEFAULT_HEAVY_MODEL)
    assert not router.requires_inference_profile(DEFAULT_LIGHT_MODEL)


def test_heavy_model_warns_for_raw_sonnet_4(monkeypatch, caplog):
    monkeypatch.setenv(
        "UIPATH_CLAUDE_MODEL_HEAVY", "anthropic.claude-sonnet-4-5-20250929-v1:0"
    )
    with caplog.at_level("WARNING", logger=router.__name__):
        heavy_model()
        heavy_model()  # second call should not re-warn
    matches = [r for r in caplog.records if "inference profile" in r.message]
    assert len(matches) == 1
    assert "us.anthropic.claude-sonnet-4-5" in matches[0].message


def test_heavy_model_no_warning_for_inference_profile(monkeypatch, caplog):
    monkeypatch.setenv(
        "UIPATH_CLAUDE_MODEL_HEAVY", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    )
    with caplog.at_level("WARNING", logger=router.__name__):
        heavy_model()
    assert not [r for r in caplog.records if "inference profile" in r.message]


def test_register_task_is_picked_up(monkeypatch):
    router.register_task("ad_hoc_task", ModelTier.LIGHT)
    try:
        assert model_for_task("ad_hoc_task") == DEFAULT_LIGHT_MODEL
    finally:
        # Clean up to avoid leaking registration into other tests.
        router._TASK_TIERS.pop("ad_hoc_task", None)


def test_heavy_model_autorewrites_raw_sonnet_4_to_us_profile(monkeypatch):
    monkeypatch.setenv(
        "UIPATH_CLAUDE_MODEL_HEAVY", "anthropic.claude-sonnet-4-5-20250929-v1:0"
    )
    assert heavy_model() == "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


def test_heavy_model_autorewrites_raw_opus_4(monkeypatch):
    monkeypatch.setenv(
        "UIPATH_CLAUDE_MODEL_HEAVY", "anthropic.claude-opus-4-5-20251101-v1:0"
    )
    assert heavy_model() == "us.anthropic.claude-opus-4-5-20251101-v1:0"


def test_heavy_model_autorewrite_can_be_disabled(monkeypatch):
    monkeypatch.setenv("UIPATH_CLAUDE_AUTO_INFERENCE_PROFILE", "0")
    monkeypatch.setenv(
        "UIPATH_CLAUDE_MODEL_HEAVY", "anthropic.claude-sonnet-4-5-20250929-v1:0"
    )
    assert heavy_model() == "anthropic.claude-sonnet-4-5-20250929-v1:0"


def test_heavy_model_autorewrite_honors_region_override(monkeypatch):
    monkeypatch.setenv("UIPATH_CLAUDE_INFERENCE_PROFILE_REGION", "eu")
    monkeypatch.setenv(
        "UIPATH_CLAUDE_MODEL_HEAVY", "anthropic.claude-sonnet-4-5-20250929-v1:0"
    )
    assert heavy_model() == "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"


def test_autorewrite_passes_through_arn(monkeypatch):
    arn = "arn:aws:bedrock:us-east-1:123:inference-profile/foo"
    monkeypatch.setenv("UIPATH_CLAUDE_MODEL_HEAVY", arn)
    assert heavy_model() == arn


def test_autorewrite_passes_through_existing_profile(monkeypatch):
    profile = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    monkeypatch.setenv("UIPATH_CLAUDE_MODEL_HEAVY", profile)
    assert heavy_model() == profile


def test_inference_profile_hint_includes_aws_doc_links():
    msg = router.inference_profile_hint("anthropic.claude-sonnet-4-5-20250929-v1:0")
    assert router.AWS_SUPPORTED_MODELS_URL in msg
    assert router.AWS_INFERENCE_PROFILES_URL in msg


def test_autorewrite_logs_once_per_model(monkeypatch, caplog):
    monkeypatch.setenv(
        "UIPATH_CLAUDE_MODEL_HEAVY", "anthropic.claude-sonnet-4-5-20250929-v1:0"
    )
    with caplog.at_level("WARNING", logger=router.__name__):
        heavy_model()
        heavy_model()
    rewrites = [r for r in caplog.records if "Auto-rewriting" in r.message]
    assert len(rewrites) == 1
