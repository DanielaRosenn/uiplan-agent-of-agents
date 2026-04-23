"""Context detection (project, environment)."""
from uipath_claude.context.project import detect_uipath_project
from uipath_claude.context.environment import get_environment_info

__all__ = ["detect_uipath_project", "get_environment_info"]
