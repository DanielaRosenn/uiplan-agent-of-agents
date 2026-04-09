"""Detect UiPath project context from current directory."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class UiPathProjectContext:
    """Represents a detected UiPath project."""

    name: str
    project_id: str
    description: str
    main_workflow: str
    dependencies: dict
    schema_version: str
    expression_language: str
    target_framework: str
    project_path: Path
    workflows: list[str]


def detect_uipath_project(start_path: Path) -> Optional[UiPathProjectContext]:
    """
    Detect a UiPath project starting from the given path.

    Searches for project.json or .uiproj files in the directory
    and parent directories.

    Args:
        start_path: Directory to start searching from

    Returns:
        UiPathProjectContext if found, None otherwise
    """
    current = Path(start_path).resolve()

    # Search up to 5 levels up
    for _ in range(5):
        project_json = current / "project.json"
        if project_json.exists():
            return _parse_project_json(project_json)

        uiproj = list(current.glob("*.uiproj"))
        if uiproj:
            return _create_minimal_context(uiproj[0])

        parent = current.parent
        if parent == current:
            break
        current = parent

    return None


def _parse_project_json(path: Path) -> Optional[UiPathProjectContext]:
    """Parse project.json into context."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        project_dir = path.parent
        workflows = _find_workflows(project_dir)

        return UiPathProjectContext(
            name=data.get("name", "Unknown"),
            project_id=data.get("projectId", ""),
            description=data.get("description", ""),
            main_workflow=data.get("main", "Main.xaml"),
            dependencies=data.get("dependencies", {}),
            schema_version=data.get("schemaVersion", ""),
            expression_language=data.get("expressionLanguage", ""),
            target_framework=data.get("targetFramework", ""),
            project_path=project_dir,
            workflows=workflows,
        )
    except (json.JSONDecodeError, IOError):
        return None


def _create_minimal_context(uiproj_path: Path) -> UiPathProjectContext:
    """Create minimal context from .uiproj file."""
    project_dir = uiproj_path.parent
    workflows = _find_workflows(project_dir)

    return UiPathProjectContext(
        name=uiproj_path.stem,
        project_id="",
        description="",
        main_workflow="Main.xaml",
        dependencies={},
        schema_version="",
        expression_language="",
        target_framework="",
        project_path=project_dir,
        workflows=workflows,
    )


def _find_workflows(project_dir: Path) -> list[str]:
    """Find all .xaml workflow files in project."""
    workflows = []
    for xaml in project_dir.rglob("*.xaml"):
        rel_path = xaml.relative_to(project_dir)
        workflows.append(str(rel_path))
    return workflows
