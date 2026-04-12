"""Tests for tool profiles."""
import pytest

from uipath_claude.tools.profiles import (
    is_command_allowed,
    resolve_tool_profile,
    supported_profiles,
)


def test_supported_profiles_include_expected_names():
    profiles = supported_profiles()
    assert set(profiles.keys()) == {"safe", "uipath-dev", "all"}


def test_unknown_profile_falls_back_to_safe():
    profile = resolve_tool_profile("unknown-profile")
    assert profile.name == "safe"


def test_uipath_dev_profile_includes_validate_command():
    profile = resolve_tool_profile("uipath-dev")
    assert "validate" in profile.commands


@pytest.mark.parametrize("raw_profile", [None, "", "   "])
def test_empty_profile_values_fall_back_to_safe(raw_profile):
    profile = resolve_tool_profile(raw_profile)
    assert profile.name == "safe"


@pytest.mark.parametrize("raw_profile", [" SAFE ", "UiPath-Dev", " ALL "])
def test_profile_name_normalization(raw_profile):
    profile = resolve_tool_profile(raw_profile)
    assert profile.name == raw_profile.strip().lower()


def test_all_profile_allows_any_command():
    profile = resolve_tool_profile("all")
    assert is_command_allowed(profile, "help")
    assert is_command_allowed(profile, "nonexistent-command")


def test_safe_profile_blocks_non_safe_command():
    profile = resolve_tool_profile("safe")
    assert not is_command_allowed(profile, "validate")


def test_default_profile_allows_recall_command():
    profile = resolve_tool_profile(None)
    assert profile.name == "safe"
    assert is_command_allowed(profile, "recall")
