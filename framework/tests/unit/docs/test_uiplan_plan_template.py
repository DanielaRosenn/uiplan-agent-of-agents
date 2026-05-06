"""Sanity checks for the UiPlan plan template."""
from __future__ import annotations

from pathlib import Path


def test_uiplan_plan_template_has_project_graph_contract():
    root = Path(__file__).resolve().parents[4]
    path = root / "templates" / "uiplan" / "_plan-template.md"
    text = path.read_text(encoding="utf-8")

    project_graph_start = text.index("## Project Graph")
    next_section_start = text.index("\n## ", project_graph_start + 1)
    project_graph = text[project_graph_start:next_section_start]

    for needle in (
        "### Mermaid source blocks",
        "### Task/todo source list",
        "### Context source table",
        "### Generation stages",
        "### Graph-to-package mapping",
        "```mermaid",
        "```text",
        "| Context source | Graph node(s) informed | Evidence / citation |",
        "| Stage | Inputs | Outputs | Gate before next stage |",
        "| Graph node / edge | Owning package/project | Artifact path | Build task IDs | Verify evidence |",
    ):
        assert needle in project_graph
