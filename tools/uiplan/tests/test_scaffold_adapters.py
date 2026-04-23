"""Scaffold-code routing and adapter behavior."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.uiplan.scaffold.project_kind import ProjectKind, detect_project_kind
from tools.uiplan.scaffold.registry import get_scaffold_adapter
from tools.uiplan.scaffold.runner import run_scaffold


def test_detect_coded_agent(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
    (tmp_path / "langgraph.json").write_text('{"graphs": {"a": "./main.py:graph"}}', encoding="utf-8")
    assert detect_project_kind(tmp_path) == ProjectKind.CODED_AGENT


def test_detect_rpa(tmp_path: Path) -> None:
    (tmp_path / "project.json").write_text(
        json.dumps({"name": "Proc", "projectType": "Process", "main": "Main.xaml"}),
        encoding="utf-8",
    )
    (tmp_path / "Main.xaml").write_text("<Activity />", encoding="utf-8")
    assert detect_project_kind(tmp_path) == ProjectKind.RPA


def test_detect_unknown_empty(tmp_path: Path) -> None:
    assert detect_project_kind(tmp_path) == ProjectKind.UNKNOWN


def test_case_over_rpa(tmp_path: Path) -> None:
    (tmp_path / "project.json").write_text("{}", encoding="utf-8")
    (tmp_path / "caseplan.json").write_text("{}", encoding="utf-8")
    assert detect_project_kind(tmp_path) == ProjectKind.CASE_MANAGEMENT


def test_coded_agent_scaffold_ok(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'x'\ndependencies = ['uipath']\n", encoding="utf-8"
    )
    (tmp_path / "langgraph.json").write_text('{"graphs": {"g": "./m.py:g"}}', encoding="utf-8")
    (tmp_path / "tests").mkdir()
    out = run_scaffold(plan_slug="p1", repo_root=tmp_path, max_loops=3)
    assert out["project_kind"] == "coded-agent"
    assert out["loop_outcome"]["status"] == "ok"


def test_rpa_scaffold_ok(tmp_path: Path) -> None:
    (tmp_path / "project.json").write_text(
        json.dumps({"name": "P", "projectType": "Process", "main": "Main.xaml"}),
        encoding="utf-8",
    )
    (tmp_path / "Main.xaml").write_text("<x/>", encoding="utf-8")
    out = run_scaffold(plan_slug="p2", repo_root=tmp_path, max_loops=2)
    assert out["project_kind"] == "rpa"
    assert out["loop_outcome"]["status"] == "ok"


def test_stub_not_implemented(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("x", encoding="utf-8")
    adapter = get_scaffold_adapter(tmp_path)
    report = adapter.run(plan_slug="z", repo_root=tmp_path, max_loops=2)
    assert report.loop_outcome["status"] == "failed"
    assert report.loop_outcome["reason"] == "not_implemented"


def test_repo_root_is_coded_agent() -> None:
    root = Path(__file__).resolve().parents[3]
    assert detect_project_kind(root) == ProjectKind.CODED_AGENT
