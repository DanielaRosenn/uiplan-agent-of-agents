"""Tests for the hardened skills submodule updater."""
from __future__ import annotations

from pathlib import Path

import pytest

from uipath_claude.skills import updater


class FakeGit:
    """Records git invocations and returns scripted outputs."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.rev_parse_result = "abcdef1234567890"
        self.remote_commit = "ffffffff00000000"
        self.dirty = False

    def __call__(self, args, cwd):
        self.calls.append(list(args))
        if args[:1] == ["rev-parse"]:
            target = args[1] if len(args) > 1 else ""
            if target.startswith("origin/"):
                return True, self.remote_commit
            return True, self.rev_parse_result
        if args[:1] == ["status"]:
            return True, ("M foo\n" if self.dirty else "")
        if args[:1] == ["fetch"]:
            return True, ""
        if args[:1] == ["checkout"]:
            return True, ""
        if args[:1] == ["reset"]:
            return True, ""
        if args[:1] == ["clean"]:
            return True, ""
        if args[:1] == ["branch"]:
            return True, ""
        if args[:1] == ["stash"]:
            return True, ""
        if args[:1] == ["pull"]:
            return True, ""
        return True, ""


@pytest.fixture
def fake_skills(tmp_path, monkeypatch):
    root = tmp_path / "skills"
    root.mkdir()
    # Simulate a submodule: .git file present.
    (root / ".git").write_text("gitdir: ../.git/modules/skills\n", encoding="utf-8")
    fg = FakeGit()
    monkeypatch.setattr(updater, "run_git_command", fg)
    return root, fg


def test_check_for_updates_flags_dirty_tree_as_needs_update(fake_skills):
    root, fg = fake_skills
    fg.rev_parse_result = fg.remote_commit  # same commit
    fg.dirty = True
    has, message, _cur, _rem = updater.check_for_updates(root)
    assert has is True
    assert "dirty" in message.lower()


def test_update_skills_force_preserves_drift_on_backup_branch(fake_skills):
    root, fg = fake_skills
    fg.dirty = True
    ok, msg = updater.update_skills(root, force=True)
    assert ok is True
    assert "backup/local-" in msg

    # Must have created a backup branch, hard-reset HEAD, cleaned, then
    # checked out main and hard-reset to origin/main.
    assert any(c[0] == "branch" and c[1].startswith("backup/local-") for c in fg.calls)
    assert ["reset", "--hard", "HEAD"] in fg.calls
    assert any(c == ["checkout", "main"] for c in fg.calls)
    assert ["reset", "--hard", "origin/main"] in fg.calls


def test_update_skills_clean_tree_just_resets_to_origin(fake_skills):
    root, fg = fake_skills
    fg.dirty = False
    ok, msg = updater.update_skills(root, force=True)
    assert ok is True
    assert "backup/local-" not in msg
    assert any(c == ["reset", "--hard", "origin/main"] for c in fg.calls)


def test_update_skills_non_force_uses_stash_and_pull(fake_skills):
    root, fg = fake_skills
    fg.dirty = True
    ok, msg = updater.update_skills(root, force=False)
    assert ok is True
    assert any(c[:2] == ["stash", "push"] for c in fg.calls)
    assert any(c[:2] == ["pull", "--ff-only"] for c in fg.calls)
