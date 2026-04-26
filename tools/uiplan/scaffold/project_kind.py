"""Heuristic UiPath / builder project classification for UiPlan scaffold routing."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from tools.uiplan.paradigms import infer_paradigm_from_files, normalize_paradigm


class ProjectKind(str, Enum):
    CODED_AGENT = "coded-agent"
    RPA = "rpa"
    CODED_AUTOMATION = "coded-automation"
    CASE_MANAGEMENT = "case-management"
    SOLUTION = "solution"
    CODED_APP = "coded-app"
    API_WORKFLOW = "api-workflow"
    MAESTRO_FLOW = "maestro-flow"
    LIBRARY = "library"
    TESTS = "tests"
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

    if (root / "api-workflow.json").exists():
        return ProjectKind.API_WORKFLOW
    if any(root.rglob("*.bpmn")) or any(root.rglob("*.flow")):
        return ProjectKind.MAESTRO_FLOW

    if (root / "project.json").exists() and any(root.rglob("*.cs")) and not any(root.rglob("*.xaml")):
        return ProjectKind.CODED_AUTOMATION
    if (root / "project.json").exists() and (root / "Activities").exists():
        return ProjectKind.LIBRARY
    if (root / "project.json").exists() and (root / "Tests").exists() and not (root / "Main.xaml").exists():
        return ProjectKind.TESTS
    if (root / "project.json").exists():
        return ProjectKind.RPA

    return ProjectKind.UNKNOWN


def detect_paradigm(repo_root: Path) -> str:
    root = repo_root.resolve()
    if not root.is_dir():
        return "unknown"
    guessed = infer_paradigm_from_files(
        has_project_json=(root / "project.json").is_file(),
        has_xaml=any(root.rglob("*.xaml")),
        has_pyproject=(root / "pyproject.toml").is_file(),
        has_agent_marker=any((root / name).is_file() for name in _AGENT_MARKERS),
        has_solution=(root / "solution.uipx").is_file(),
        has_coded_app=(root / "app.config.json").is_file() and (root / "action-schema.json").is_file(),
        has_case_plan=(root / "caseplan.json").is_file(),
        has_api_workflow=(root / "api-workflow.json").is_file(),
        has_maestro_file=any(root.rglob("*.bpmn")) or any(root.rglob("*.flow")),
    )
    return normalize_paradigm(guessed)
