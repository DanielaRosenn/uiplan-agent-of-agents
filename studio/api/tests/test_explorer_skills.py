"""Tests for project-wide skill aggregation."""
from __future__ import annotations

from pathlib import Path

from app import explorer_skills


def test_match_skills_for_query_ranks_relevant_skill(monkeypatch) -> None:
    monkeypatch.setattr(
        explorer_skills,
        "load_registered_skills",
        lambda _root: [
            {
                "name": "uipath-rpa",
                "description": "UiPath automations with XAML workflows",
                "triggers": ["xaml workflow", "rpa automation"],
                "path": "skills/uipath-rpa/SKILL.md",
                "origin": "test",
            },
            {
                "name": "uipath-platform",
                "description": "Orchestrator folders and assets",
                "triggers": ["orchestrator"],
                "path": "skills/uipath-platform/SKILL.md",
                "origin": "test",
            },
        ],
    )

    matches = explorer_skills.match_skills_for_query(Path.cwd(), "Main.xaml workflow activity", top_k=1)

    assert len(matches) == 1
    assert matches[0].id == "uipath-rpa"
    assert matches[0].score > 0


def test_aggregate_skill_graph_context_caps_coverage_to_top_three(monkeypatch) -> None:
    monkeypatch.setattr(
        explorer_skills,
        "load_registered_skills",
        lambda _root: [
            {
                "name": "uipath-rpa",
                "description": "XAML workflows and RPA activity authoring",
                "triggers": ["xaml workflow"],
                "path": "skills/uipath-rpa/SKILL.md",
                "origin": "test",
                "tags": ["rpa"],
            },
        ],
    )
    nodes = [
        {"id": "rpa:Main.xaml", "label": "Main.xaml", "kind": "workflow", "layer": "rpa", "desc": "main xaml workflow"},
        {"id": "rpa:A.xaml", "label": "A.xaml", "kind": "activity", "layer": "rpa", "desc": "xaml activity"},
        {"id": "rpa:B.xaml", "label": "B.xaml", "kind": "activity", "layer": "rpa", "desc": "xaml activity"},
        {"id": "rpa:C.xaml", "label": "C.xaml", "kind": "activity", "layer": "rpa", "desc": "xaml activity"},
    ]

    skill_nodes, covers_edges = explorer_skills.aggregate_skill_graph_context(Path.cwd(), nodes)

    assert [n["id"] for n in skill_nodes] == ["skill:uipath-rpa"]
    assert skill_nodes[0]["meta"]["coverage_count"] == 4
    assert len(covers_edges) == 3
    assert all(edge["kind"] == "covers" for edge in covers_edges)


def test_read_skill_detail_returns_body_without_frontmatter(tmp_path: Path, monkeypatch) -> None:
    skill_file = tmp_path / "skill" / "SKILL.md"
    skill_file.parent.mkdir()
    skill_file.write_text(
        "---\nname: demo-skill\ndescription: Demo\ntriggers: [demo]\n---\n# Demo Skill\n\nBody text.",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        explorer_skills,
        "load_registered_skills",
        lambda _root: [
            {
                "name": "demo-skill",
                "description": "Demo",
                "triggers": ["demo"],
                "tags": ["sample"],
                "path": str(skill_file),
                "origin": "test",
            },
        ],
    )

    detail = explorer_skills.read_skill_detail(Path.cwd(), "demo-skill")

    assert detail is not None
    assert detail["id"] == "demo-skill"
    assert detail["body"].startswith("# Demo Skill")
    assert "---" not in detail["body"]
