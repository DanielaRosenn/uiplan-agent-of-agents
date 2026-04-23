"""Tests for UiPlan grounding pack (library search, no LangChain misuse)."""
from __future__ import annotations

from pathlib import Path

from mcp_server.tools.plan_grounding import build_grounding_pack


def _repo_root() -> Path:
    # framework/tests/mcp/<this_file> -> parents[3] is repository root
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
