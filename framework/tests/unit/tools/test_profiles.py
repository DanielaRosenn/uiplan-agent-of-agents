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


def test_unknown_profile_falls_back_to_all():
    profile = resolve_tool_profile("unknown-profile")
    assert profile.name == "all"


def test_uipath_dev_profile_includes_validate_command():
    profile = resolve_tool_profile("uipath-dev")
    assert "validate" in profile.commands


def test_safe_profile_includes_validate_command():
    profile = resolve_tool_profile("safe")
    assert "validate" in profile.commands


@pytest.mark.parametrize("raw_profile", [None, "", "   "])
def test_empty_profile_values_fall_back_to_all(raw_profile):
    profile = resolve_tool_profile(raw_profile)
    assert profile.name == "all"


@pytest.mark.parametrize("raw_profile", [" SAFE ", "UiPath-Dev", " ALL "])
def test_profile_name_normalization(raw_profile):
    profile = resolve_tool_profile(raw_profile)
    assert profile.name == raw_profile.strip().lower()


def test_all_profile_allows_any_command():
    profile = resolve_tool_profile("all")
    assert is_command_allowed(profile, "help")
    assert is_command_allowed(profile, "nonexistent-command")


def test_safe_profile_blocks_unknown_command():
    profile = resolve_tool_profile("safe")
    assert not is_command_allowed(profile, "definitely-not-a-real-command")


def test_default_profile_allows_recall_command():
    profile = resolve_tool_profile(None)
    assert profile.name == "all"
    assert is_command_allowed(profile, "recall")


def test_safe_profile_allows_readonly_library_commands():
    profile = resolve_tool_profile("safe")
    assert is_command_allowed(profile, "books")
    assert is_command_allowed(profile, "scan-upstream-skills")
    assert is_command_allowed(profile, "library-proposals")


def test_safe_profile_allows_library_harvest():
    profile = resolve_tool_profile("safe")
    assert is_command_allowed(profile, "library-harvest")


def test_safe_profile_allows_pdd_and_uiplan():
    profile = resolve_tool_profile("safe")
    assert is_command_allowed(profile, "pdd")
    assert is_command_allowed(profile, "uiplan")
    assert is_command_allowed(profile, "uiplan-implement")
    assert is_command_allowed(profile, "repair-restore")


def test_uipath_dev_profile_allows_library_harvest():
    profile = resolve_tool_profile("uipath-dev")
    assert is_command_allowed(profile, "library-harvest")


def test_safe_and_uipath_dev_allow_same_command_set():
    safe_p = resolve_tool_profile("safe")
    dev_p = resolve_tool_profile("uipath-dev")
    assert safe_p.commands == dev_p.commands
