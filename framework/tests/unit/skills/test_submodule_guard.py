"""Unit tests for the UiPath/skills submodule guard."""
from __future__ import annotations

from pathlib import Path

import pytest

from uipath_claude.skills import submodule_guard


def _make_fake_repo(
    root: Path,
    *,
    approved: list[str] | None,
    skill_ids: list[str],
    rule_files: dict[str, str] | None = None,
    verbs_file: dict | None = None,
    cli_doc: str | None = None,
    submodule_exists: bool = True,
    gitmodules_content: str | None = None,
) -> Path:
    """Create a fake repo layout. Returns the repo root."""
    (root / ".git").mkdir(parents=True, exist_ok=True)

    gm = gitmodules_content
    if gm is None:
        gm = (
            '[submodule "skills"]\n'
            "\tpath = skills\n"
            "\turl = https://github.com/UiPath/skills\n"
        )
    (root / ".gitmodules").write_text(gm, encoding="utf-8")

    if submodule_exists:
        skills_root = root / "skills"
        (skills_root / "skills").mkdir(parents=True, exist_ok=True)
        (skills_root / "CLAUDE.md").write_text("skills repo", encoding="utf-8")
        for sid in skill_ids:
            sdir = skills_root / "skills" / sid
            sdir.mkdir(parents=True, exist_ok=True)
            (sdir / "SKILL.md").write_text(f"---\nname: {sid}\n---\n", encoding="utf-8")

    if approved is not None:
        (root / ".uipath").mkdir(parents=True, exist_ok=True)
        (root / ".uipath" / "skills-approved.sha").write_text(
            "\n".join(approved) + "\n", encoding="utf-8"
        )

    files = rule_files or {}
    for rel, content in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    if cli_doc is not None:
        cli_path = root / "docs" / "uipath-cli.md"
        cli_path.parent.mkdir(parents=True, exist_ok=True)
        cli_path.write_text(cli_doc, encoding="utf-8")

    if verbs_file is not None:
        import json

        verbs_path = root / "docs" / "uipath-cli.verbs.json"
        verbs_path.parent.mkdir(parents=True, exist_ok=True)
        verbs_path.write_text(json.dumps(verbs_file), encoding="utf-8")

    return root


def _install_git_stub(
    monkeypatch: pytest.MonkeyPatch,
    *,
    head: str = "c9458040aca239f145ed238f2d72b33aa82d8ccd",
    porcelain: str = "",
) -> None:
    def stub(args, cwd):
        if args[:1] == ["rev-parse"]:
            return True, head
        if args[:1] == ["status"]:
            return True, porcelain
        return True, ""

    monkeypatch.setattr(submodule_guard, "run_git_command", stub)


def _point_submodule(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setattr(
        submodule_guard, "get_skills_submodule_path", lambda: path
    )


def test_passes_on_clean_approved_repo(tmp_path, monkeypatch):
    head = "c9458040aca239f145ed238f2d72b33aa82d8ccd"
    _make_fake_repo(
        tmp_path,
        approved=[head],
        skill_ids=["uipath-rpa", "uipath-agents"],
        rule_files={
            "CLAUDE.md": "See uipath-rpa and uipath-agents skills.",
        },
    )
    _install_git_stub(monkeypatch, head=head)
    _point_submodule(monkeypatch, tmp_path / "skills")

    result = submodule_guard.verify(strict=True, repo_root=tmp_path)

    assert result.ok is True, result.to_report()
    assert not result.errors


def test_fails_when_submodule_missing(tmp_path, monkeypatch):
    _make_fake_repo(
        tmp_path,
        approved=["abc"],
        skill_ids=[],
        submodule_exists=False,
    )
    _install_git_stub(monkeypatch)
    _point_submodule(monkeypatch, tmp_path / "skills")

    result = submodule_guard.verify(strict=True, repo_root=tmp_path)

    assert result.ok is False
    assert any("skills submodule directory missing" in e for e in result.errors)


def test_fails_on_unapproved_head(tmp_path, monkeypatch):
    _make_fake_repo(
        tmp_path,
        approved=["aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"],
        skill_ids=["uipath-rpa"],
    )
    _install_git_stub(monkeypatch, head="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
    _point_submodule(monkeypatch, tmp_path / "skills")

    result = submodule_guard.verify(strict=True, repo_root=tmp_path)

    assert result.ok is False
    assert any("not in" in e for e in result.errors)


def test_fails_on_dirty_tree(tmp_path, monkeypatch):
    head = "c9458040aca239f145ed238f2d72b33aa82d8ccd"
    _make_fake_repo(tmp_path, approved=[head], skill_ids=["uipath-rpa"])
    _install_git_stub(monkeypatch, head=head, porcelain=" M skills/README.md")
    _point_submodule(monkeypatch, tmp_path / "skills")

    result = submodule_guard.verify(strict=True, repo_root=tmp_path)

    assert result.ok is False
    assert any("local modifications" in e for e in result.errors)


def test_fails_on_dangling_skill_reference(tmp_path, monkeypatch):
    head = "c9458040aca239f145ed238f2d72b33aa82d8ccd"
    _make_fake_repo(
        tmp_path,
        approved=[head],
        skill_ids=["uipath-rpa"],
        rule_files={
            "CLAUDE.md": "Refer to uipath-rpa and uipath-banana-farming skills.",
        },
    )
    _install_git_stub(monkeypatch, head=head)
    _point_submodule(monkeypatch, tmp_path / "skills")

    result = submodule_guard.verify(strict=True, repo_root=tmp_path)

    assert result.ok is False
    assert any("uipath-banana-farming" in e for e in result.errors)


def test_fails_on_unknown_cli_verb(tmp_path, monkeypatch):
    head = "c9458040aca239f145ed238f2d72b33aa82d8ccd"
    verbs = {
        "clis": {
            "uipcli": {"verbs": ["package pack", "package analyze"]},
            "uipath": {"verbs": ["auth", "run"]},
        }
    }
    cli_doc = (
        "# CLI\n\n"
        "```bash\n"
        "uipcli package analyze project.json\n"
        "uipcli package delete my-pkg\n"
        "uipath run agent '{}'\n"
        "```\n"
    )
    _make_fake_repo(
        tmp_path,
        approved=[head],
        skill_ids=["uipath-rpa"],
        verbs_file=verbs,
        cli_doc=cli_doc,
    )
    _install_git_stub(monkeypatch, head=head)
    _point_submodule(monkeypatch, tmp_path / "skills")

    result = submodule_guard.verify(strict=True, repo_root=tmp_path)

    assert result.ok is False
    joined = "\n".join(result.errors)
    assert "uipcli package delete" in joined


def test_prose_mentions_do_not_trigger_verb_scan(tmp_path, monkeypatch):
    """Verb scanning must only look inside fenced command blocks."""
    head = "c9458040aca239f145ed238f2d72b33aa82d8ccd"
    verbs = {
        "clis": {
            "uipcli": {"verbs": ["package analyze"]},
        }
    }
    cli_doc = (
        "The `uipcli package delete` verb no longer exists in 25.10.\n\n"
        "```bash\nuipcli package analyze project.json\n```\n"
    )
    _make_fake_repo(
        tmp_path,
        approved=[head],
        skill_ids=["uipath-rpa"],
        verbs_file=verbs,
        cli_doc=cli_doc,
    )
    _install_git_stub(monkeypatch, head=head)
    _point_submodule(monkeypatch, tmp_path / "skills")

    result = submodule_guard.verify(strict=True, repo_root=tmp_path)

    assert result.ok is True, result.to_report()


def test_non_skill_uipath_tokens_are_ignored(tmp_path, monkeypatch):
    """References to uipath-python/uipath-langchain/etc. must not fail."""
    head = "c9458040aca239f145ed238f2d72b33aa82d8ccd"
    _make_fake_repo(
        tmp_path,
        approved=[head],
        skill_ids=["uipath-rpa"],
        rule_files={
            "CLAUDE.md": (
                "Use uipath-langchain SDK. See the uipath-rpa skill. "
                "Also uipath-python and uipath-project-discovery-agent."
            ),
        },
    )
    _install_git_stub(monkeypatch, head=head)
    _point_submodule(monkeypatch, tmp_path / "skills")

    result = submodule_guard.verify(strict=True, repo_root=tmp_path)

    assert result.ok is True, result.to_report()
