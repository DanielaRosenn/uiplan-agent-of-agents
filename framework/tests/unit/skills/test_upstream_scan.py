"""Tests for upstream skills scanner."""
from __future__ import annotations

from pathlib import Path

import pytest

from uipath_claude.skills import upstream_scan


def _make_fake_skills_tree(root: Path, skill_ids: list[str], tools: list[str]) -> None:
    (root / "skills").mkdir(parents=True, exist_ok=True)
    for sid in skill_ids:
        sdir = root / "skills" / sid
        sdir.mkdir(parents=True, exist_ok=True)
        (sdir / "SKILL.md").write_text("---\nname: " + sid + "\n---\n", encoding="utf-8")
    for tool_dir in tools:
        (root / tool_dir).mkdir(parents=True, exist_ok=True)


@pytest.fixture
def fake_skills(tmp_path, monkeypatch):
    root = tmp_path / "skills"
    root.mkdir()
    _make_fake_skills_tree(root, ["uipath-rpa"], ["agents"])

    def fake_cmd(args, cwd):
        if args[:1] == ["rev-parse"]:
            return True, "abc1234567890def"
        return True, ""

    monkeypatch.setattr(upstream_scan, "run_git_command", fake_cmd)
    monkeypatch.setattr(
        upstream_scan, "get_skills_submodule_path", lambda: root
    )
    return root


def test_first_scan_has_no_prev_but_includes_current(fake_skills, tmp_path):
    state = tmp_path / "state.json"
    diff = upstream_scan.scan_upstream(state_path=state)
    # First run: no prior snapshot, so everything is "new".
    assert diff.new_skills == ["uipath-rpa"]
    assert diff.new_tools == ["agents"]
    assert state.exists()


def test_second_scan_detects_added_skill(fake_skills, tmp_path):
    state = tmp_path / "state.json"
    upstream_scan.scan_upstream(state_path=state)
    _make_fake_skills_tree(fake_skills, ["uipath-rpa", "uipath-agents"], ["agents", "hooks"])
    diff = upstream_scan.scan_upstream(state_path=state)
    assert diff.new_skills == ["uipath-agents"]
    assert diff.new_tools == ["hooks"]
    assert diff.removed_skills == []


def test_second_scan_detects_removed_skill(fake_skills, tmp_path):
    state = tmp_path / "state.json"
    upstream_scan.scan_upstream(state_path=state)
    # Remove the skill.
    (fake_skills / "skills" / "uipath-rpa" / "SKILL.md").unlink()
    (fake_skills / "skills" / "uipath-rpa").rmdir()
    diff = upstream_scan.scan_upstream(state_path=state)
    assert diff.removed_skills == ["uipath-rpa"]


def test_format_diff_no_changes(fake_skills, tmp_path):
    state = tmp_path / "state.json"
    upstream_scan.scan_upstream(state_path=state)
    diff = upstream_scan.scan_upstream(state_path=state)
    assert "No new UiPath skills" in upstream_scan.format_diff(diff)


def test_dry_run_does_not_persist(fake_skills, tmp_path):
    state = tmp_path / "state.json"
    upstream_scan.scan_upstream(state_path=state, persist=False)
    assert not state.exists()


def test_save_snapshot_is_atomic(fake_skills, tmp_path, monkeypatch):
    """A mid-write crash must not leave an invalid state file."""
    import os
    state = tmp_path / "state.json"
    state.write_text('{"commit":"prev","skills":[],"tools":[]}', encoding="utf-8")

    orig_replace = os.replace

    def boom(src, dst):
        raise OSError("simulated crash")

    monkeypatch.setattr(os, "replace", boom)
    upstream_scan.save_snapshot(
        upstream_scan.SkillsSnapshot(commit="new", skills=["x"], tools=[]),
        path=state,
    )
    # Old content preserved because os.replace never ran.
    assert '"prev"' in state.read_text(encoding="utf-8")
    # Tmp file cleaned up.
    assert not state.with_suffix(".json.tmp").exists()
    monkeypatch.setattr(os, "replace", orig_replace)
