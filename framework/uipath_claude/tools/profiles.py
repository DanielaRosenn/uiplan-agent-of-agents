"""Tool profile definitions and resolver helpers."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolProfile:
    """Named set of allowed slash commands."""

    name: str
    commands: tuple[str, ...]


# ``safe`` includes the full in-chat slash surface needed for SDLC work
# (PDD lifecycle, validation, UiPlan, library harvest, repair) while still
# being a finite allow-list (unlike ``all`` which permits any string).
_SAFE_COMMANDS = (
    "help",
    "doctor",
    "status",
    "skills",
    "analyze",
    "validate",
    "bootstrap",
    "recall",
    "resume",
    "update-skills",
    "books",
    "scan-upstream-skills",
    "library-proposals",
    "library-harvest",
    "pdd",
    "repair-restore",
    "uiplan",
    "plan",
)
_UIPATH_DEV_COMMANDS = (*_SAFE_COMMANDS,)

_PROFILES = {
    "safe": ToolProfile(name="safe", commands=_SAFE_COMMANDS),
    "uipath-dev": ToolProfile(name="uipath-dev", commands=_UIPATH_DEV_COMMANDS),
    "all": ToolProfile(name="all", commands=("*",)),
}


def supported_profiles() -> dict[str, ToolProfile]:
    """Return supported tool profiles keyed by profile name."""
    return dict(_PROFILES)


def resolve_tool_profile(profile_name: str | None) -> ToolProfile:
    """Resolve configured profile name, defaulting to ``all`` when unset/unknown."""
    if not profile_name:
        return _PROFILES["all"]

    normalized = profile_name.strip().lower()
    return _PROFILES.get(normalized, _PROFILES["all"])


def is_command_allowed(profile: ToolProfile, command_name: str) -> bool:
    """Return True when command is enabled by profile."""
    normalized = command_name.strip().lower()
    return "*" in profile.commands or normalized in profile.commands
