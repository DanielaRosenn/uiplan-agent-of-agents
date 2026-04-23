"""Heuristic UiPath / builder project classification for UiPlan scaffold routing."""

from __future__ import annotations

from enum import Enum
from pathlib import Path


class ProjectKind(str, Enum):
    CODED_AGENT = "coded-agent"
    RPA = "rpa"
    CASE_MANAGEMENT = "case-management"
    SOLUTION = "solution"
    CODED_APP = "coded-app"
    UNKNOWN = "unknown"


_AGENT_MARKERS = ("langgraph.json", "agent_framework.json", "llama_index.json")


def detect_project_kind(repo_root: Path) -> ProjectKind:
    root = repo_root.resolve()
    if not root.is_dir():
        return ProjectKind.UNKNOWN

    if (root / "caseplan.json").exists():
        return ProjectKind.CASE_MANAGEMENT
    if (root / "solution.uipx").exists():
        return ProjectKind.SOLUTION
    if (root / "app.config.json").exists() and (root / "action-schema.json").exists():
        return ProjectKind.CODED_APP

    pyproject = root / "pyproject.toml"
    if pyproject.exists() and any((root / name).exists() for name in _AGENT_MARKERS):
        return ProjectKind.CODED_AGENT

    if (root / "project.json").exists():
        return ProjectKind.RPA

    return ProjectKind.UNKNOWN
