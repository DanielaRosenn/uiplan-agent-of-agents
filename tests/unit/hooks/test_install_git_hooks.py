"""Tests for the git-hooks installer."""
from __future__ import annotations

from pathlib import Path

import pytest

from uipath_claude.hooks.install_git_hooks import (
    HOOK_MARKER,
    HOOK_NAMES,
    install,
)


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".gitmodules").write_text(
        "[submodule \"skills\"]\n  path = skills\n  url = https://example.com/skills\n",
        encoding="utf-8",
    )
    return tmp_path


def test_install_creates_all_hooks(fake_repo):
    results = install(repo_root=fake_repo)
    statuses = dict(results)
    for name in HOOK_NAMES:
        assert statuses[name] == "installed"
        target = fake_repo / ".git" / "hooks" / name
        assert target.exists()
        content = target.read_text(encoding="utf-8")
        assert HOOK_MARKER in content
        assert "git submodule update --init --remote --merge skills" in content


def test_install_is_idempotent(fake_repo):
    install(repo_root=fake_repo)
    second = install(repo_root=fake_repo)
    statuses = dict(second)
    for name in HOOK_NAMES:
        assert statuses[name] == "already installed"


def test_install_skips_unmarked_existing_without_force(fake_repo):
    target = fake_repo / ".git" / "hooks" / "post-merge"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("#!/bin/sh\necho user hook\n", encoding="utf-8")

    statuses = dict(install(repo_root=fake_repo))
    assert statuses["post-merge"] == "exists (skipped; use --force)"
    # Unrelated hooks still install.
    assert statuses["post-checkout"] == "installed"


def test_install_force_overwrites(fake_repo):
    target = fake_repo / ".git" / "hooks" / "post-merge"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("#!/bin/sh\necho user hook\n", encoding="utf-8")

    statuses = dict(install(repo_root=fake_repo, force=True))
    assert statuses["post-merge"] == "installed"
    assert HOOK_MARKER in target.read_text(encoding="utf-8")


def test_install_handles_worktree_gitfile(tmp_path):
    # Simulate a worktree: .git is a file pointing at gitdir.
    real = tmp_path / "real"
    (real / "hooks").mkdir(parents=True)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    (worktree / ".git").write_text(f"gitdir: {real}\n", encoding="utf-8")

    results = install(repo_root=worktree)
    statuses = dict(results)
    for name in HOOK_NAMES:
        assert statuses[name] == "installed"
        assert (real / "hooks" / name).exists()
