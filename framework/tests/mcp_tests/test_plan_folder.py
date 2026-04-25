"""Tests for folder-shaped UiPlan resolution."""
from __future__ import annotations

import pytest
import yaml

from mcp_server.tools.plan_folder import (
    collect_folder_plan_entries,
    is_folder_plan,
    load_folder_meta,
    resolve_plan_path,
    save_folder_meta,
)


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "docs" / "plans").mkdir(parents=True)
    (tmp_path / ".cursor" / "plans").mkdir(parents=True)
    return tmp_path


def test_resolve_folder_by_slug(repo):
    d = repo / ".cursor" / "plans" / "2026-04-21-acme-feature"
    d.mkdir(parents=True)
    save_folder_meta(
        d,
        {
            "slug": "acme-feature",
            "title": "Acme",
            "date": "2026-04-21",
            "status": "draft",
            "owner": "t",
            "project_type": "mixed",
            "plan_kind": "uiplan",
        },
    )
    r = resolve_plan_path(repo / ".cursor" / "plans", None, "acme-feature")
    assert r.path == d
    assert r.kind == "folder"


def test_is_folder_plan(repo):
    d = repo / ".cursor" / "plans" / "2026-04-21-x"
    d.mkdir()
    assert not is_folder_plan(d)
    (d / ".meta.yaml").write_text("slug: x\nplan_kind: uiplan\n", encoding="utf-8")
    assert is_folder_plan(d)


def test_collect_folder_entries(repo):
    d = repo / ".cursor" / "plans" / "2026-04-21-z"
    d.mkdir()
    save_folder_meta(
        d,
        {
            "slug": "z",
            "title": "Zed",
            "date": "2026-04-21",
            "status": "draft",
            "owner": "t",
            "project_type": "rpa",
            "plan_kind": "uiplan",
        },
    )
    items = collect_folder_plan_entries(repo / ".cursor" / "plans", "draft")
    assert any(i.get("slug") == "z" for i in items)


def test_load_meta_roundtrip(repo):
    d = repo / ".cursor" / "plans" / "2026-04-21-rt"
    d.mkdir()
    meta = {"slug": "rt", "plan_kind": "uiplan", "status": "draft"}
    save_folder_meta(d, meta)
    loaded = load_folder_meta(d)
    assert loaded["slug"] == "rt"
    assert yaml.safe_load((d / ".meta.yaml").read_text(encoding="utf-8"))["slug"] == "rt"
