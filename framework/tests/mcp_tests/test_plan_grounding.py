"""Tests for UiPlan grounding pack (library search, no LangChain misuse)."""
from __future__ import annotations

from pathlib import Path

from mcp_server.tools import plan_grounding
from mcp_server.tools.plan_grounding import build_grounding_pack


def _repo_root() -> Path:
    # framework/tests/mcp_tests/<this_file> -> parents[3] is repository root
    return Path(__file__).resolve().parents[3]


def test_build_grounding_pack_library_hits_no_structured_tool_error():
    repo = _repo_root()
    assert (repo / "pyproject.toml").is_file(), "expected real repo root for library catalog"
    pack = build_grounding_pack(repo, "orchestrator queue invoice")
    assert pack.get("status") == "ok"
    hits = pack.get("library_hits") or []
    assert hits, "expected at least one library query from topic tokens"
    for h in hits:
        err = h.get("error", "")
        assert "StructuredTool" not in err, f"library_hits should use .invoke: {h!r}"
        assert "not callable" not in err, f"unexpected call error: {h!r}"
        assert "excerpt" in h or "error" in h


def test_build_grounding_pack_includes_skill_excerpts_and_knowledge_lookup(tmp_path, monkeypatch):
    (tmp_path / "CLAUDE.md").write_text("# Rules\n", encoding="utf-8")

    class FakeRegistry:
        def __init__(self, project_root):
            self.project_root = project_root
            self.skills = [
                {
                    "name": "uipath-planner",
                    "origin": "test",
                    "description": "Plan work.",
                    "path": "planner.md",
                },
                {
                    "name": "uipath-rpa",
                    "origin": "test",
                    "description": "Build workflows.",
                    "path": "rpa.md",
                },
            ]

        def load_skills(self):
            return self.skills

        def get_skill(self, name):
            return next((skill for skill in self.skills if skill["name"] == name), None)

    monkeypatch.setattr(plan_grounding, "SkillRegistry", FakeRegistry)
    monkeypatch.setattr(
        plan_grounding,
        "_select_relevant_skills",
        lambda topic, skills, max_items=5: [skills[1]],
    )
    monkeypatch.setattr(
        plan_grounding,
        "load_skill_content",
        lambda path: "---\nname: x\n---\n# Skill Body\nUse this guidance for planning.",
    )
    class FakeSearchLibrary:
        def invoke(self, payload):
            return "library result"

    class FakeLookupKnowledge:
        def invoke(self, payload):
            return "knowledge result\n---\nSOURCE: askai"

    monkeypatch.setattr(plan_grounding, "_search_library", FakeSearchLibrary())
    monkeypatch.setattr(plan_grounding, "_lookup_knowledge", FakeLookupKnowledge())

    pack = build_grounding_pack(tmp_path, "queue automation")

    assert pack["planning_skill"]["name"] == "uipath-planner"
    assert "Skill Body" in pack["planning_skill"]["excerpt"]
    assert pack["matched_skills"][0]["name"] == "uipath-rpa"
    assert "Skill Body" in pack["matched_skills"][0]["excerpt"]
    assert pack["knowledge_lookups"][0]["source"] == "SOURCE: askai"
    assert "knowledge result" in pack["knowledge_lookups"][0]["excerpt"]
