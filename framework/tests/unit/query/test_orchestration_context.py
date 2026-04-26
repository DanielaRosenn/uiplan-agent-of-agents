"""Tests for orchestration context builder."""
from __future__ import annotations

from unittest.mock import patch

from uipath_claude.query.orchestration_context import build_orchestration_context


def _fake_grounding_ok() -> dict:
    return {
        "status": "ok",
        "topic": "test",
        "source_documents": [
            {
                "path": "docs/pdd.md",
                "name": "pdd",
                "kind": "pdd",
                "excerpt": "PDD body line one",
            }
        ],
        "matched_skills": [{"name": "uiplan", "description": "planning skill"}],
        "pdd_candidates": [],
        "candidate_project_template": "",
        "project_context_excerpt": "ctx",
        "claude_md_excerpt": "claude",
        "unanswered": [],
    }


@patch("uipath_claude.query.orchestration_context.build_grounding_pack", return_value=_fake_grounding_ok())
def test_context_includes_source_docs_from_grounding(_mock_ground: object, tmp_path) -> None:
    ctx = build_orchestration_context(
        f"see {tmp_path / 'docs' / 'pdd.md'} for details",
        project_root=tmp_path,
        command_names=["help", "status"],
        tool_profile="all",
        history=[{"role": "user", "content": "hi"}],
    )
    assert ctx.user_request
    assert "help" in ctx.command_names and "status" in ctx.command_names
    g = ctx.grounding_pack
    assert g.get("status") == "ok"
    src = g.get("source_documents") or []
    assert len(src) == 1
    assert src[0].get("path") == "docs/pdd.md"
    assert "PDD body" in (src[0].get("excerpt") or "")


@patch("uipath_claude.query.orchestration_context.build_grounding_pack", return_value={"status": "error"})
def test_context_surfaces_grounding_error(_mock_ground: object, tmp_path) -> None:
    ctx = build_orchestration_context("x", project_root=tmp_path)
    assert ctx.grounding_pack.get("status") == "error"
