"""Tests for docs/plans constitution loader."""
from __future__ import annotations

from pathlib import Path

from mcp_server.tools.plan_constitution import load_constitution


def test_load_constitution_override(tmp_path):
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    (plans / "constitution.md").write_text(
        "- **gate_a**: First gate.\n- **gate_b**: Second gate.\n",
        encoding="utf-8",
    )
    out = load_constitution(tmp_path)
    assert out["source"] == "docs/plans/constitution.md"
    ids = [g["id"] for g in out["gates"]]
    assert "gate_a" in ids
    assert "gate_b" in ids


def test_load_constitution_builtin_when_missing(tmp_path):
    out = load_constitution(tmp_path)
    assert out["source"] == "built-in"
    assert len(out["gates"]) >= 3
