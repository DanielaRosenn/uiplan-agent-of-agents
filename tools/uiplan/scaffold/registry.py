"""Registry mapping detected project kind -> scaffold adapter."""

from __future__ import annotations

from pathlib import Path

from tools.uiplan.scaffold.project_kind import ProjectKind, detect_project_kind
from tools.uiplan.scaffold.adapters.base import ScaffoldAdapter
from tools.uiplan.scaffold.adapters.coded_agent import CodedAgentScaffoldAdapter
from tools.uiplan.scaffold.adapters.rpa import RpaScaffoldAdapter
from tools.uiplan.scaffold.adapters.stub import ExplicitStubAdapter

_CODED = CodedAgentScaffoldAdapter()
_RPA = RpaScaffoldAdapter()


def get_scaffold_adapter(repo_root: Path) -> ScaffoldAdapter:
    kind = detect_project_kind(repo_root)
    if kind == ProjectKind.CODED_AGENT:
        return _CODED
    if kind == ProjectKind.RPA:
        return _RPA
    return ExplicitStubAdapter(kind.value)
