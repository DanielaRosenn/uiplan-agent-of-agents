"""Per-project-type scaffold adapters."""

from tools.uiplan.scaffold.adapters.base import ScaffoldAdapter
from tools.uiplan.scaffold.adapters.coded_agent import CodedAgentScaffoldAdapter
from tools.uiplan.scaffold.adapters.rpa import RpaScaffoldAdapter
from tools.uiplan.scaffold.adapters.stub import ExplicitStubAdapter

__all__ = [
    "ScaffoldAdapter",
    "CodedAgentScaffoldAdapter",
    "RpaScaffoldAdapter",
    "ExplicitStubAdapter",
]
