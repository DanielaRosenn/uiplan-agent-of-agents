"""End-to-end tests for the library-proposals CLI subcommand."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def seeded_env(tmp_path, monkeypatch):
    library = tmp_path / "library"
    library.mkdir()
    (library / "catalog.yaml").write_text(
        yaml.dump(
            {
                "version": 1,
                "books": [
                    {
                        "id": "uipath-docs",
                        "title": "UiPath Docs",
                        "path": "books/uipath-docs",
                        "description": "",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    book = library / "books" / "uipath-docs"
    book.mkdir(parents=True)
    (book / "book.yaml").write_text(
        yaml.dump(
            {
                "id": "uipath-docs",
                "title": "UiPath Docs",
                "version": "1",
                "source": "test",
                "chapters": [
                    {
                        "id": "activities",
                        "title": "Activities",
                        "path": "chapters/01-activities",
                        "order": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    ch = book / "chapters" / "01-activities"
    ch.mkdir(parents=True)
    (ch / "chapter.yaml").write_text(
        yaml.dump({"id": "activities", "title": "Activities", "sections": []}),
        encoding="utf-8",
    )

    proposals = tmp_path / "proposals"
    events_log = tmp_path / "events.log"
    env = {
        "UIPATH_CLAUDE_LIBRARY": str(library),
        "UIPATH_CLAUDE_LIBRARY_PROPOSALS": str(proposals),
        "UIPATH_EVENT_LOG": str(events_log),
    }
    return {"library": library, "proposals": proposals, "env": env, "events_log": events_log}


def _run(args, env):
    result = subprocess.run(
        [sys.executable, "-m", "uipath_claude.cli.app", *args],
        capture_output=True,
        text=True,
        env={**os.environ, **env},
    )
    return result


def _enqueue_proposal(env):
    from uipath_claude.library.proposals import LibraryProposal, ProposalKind, ProposalStore

    for k, v in env.items():
        os.environ[k] = v
    store = ProposalStore()
    return store.enqueue(
        LibraryProposal(
            proposal_id="",
            book_id="uipath-docs",
            chapter_id="activities",
            section_id="retry-scope",
            section_title="Retry Scope",
            kind=ProposalKind.NEW_SECTION,
            content="# Retry Scope\n\nbody",
            keywords=["retry"],
            rationale="came up",
        )
    )


def _log_contains_event(events_log: Path, event: str) -> bool:
    if not events_log.exists():
        return False
    for line in events_log.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("event") == event:
            return True
    return False


def test_list_shows_pending_proposals(seeded_env):
    p = _enqueue_proposal(seeded_env["env"])
    result = _run(["library-proposals", "list"], seeded_env["env"])
    assert result.returncode == 0, result.stderr
    assert p.proposal_id in result.stdout
    assert "retry-scope" in result.stdout


def test_show_prints_full_proposal(seeded_env):
    p = _enqueue_proposal(seeded_env["env"])
    result = _run(["library-proposals", "show", p.proposal_id], seeded_env["env"])
    assert result.returncode == 0, result.stderr
    assert "Retry Scope" in result.stdout
    assert "came up" in result.stdout


def test_approve_applies_to_library_and_removes_proposal(seeded_env):
    p = _enqueue_proposal(seeded_env["env"])
    result = _run(["library-proposals", "approve", p.proposal_id], seeded_env["env"])
    assert result.returncode == 0, result.stderr

    md = (
        seeded_env["library"]
        / "books/uipath-docs/chapters/01-activities/retry-scope.md"
    )
    assert md.exists()
    assert "body" in md.read_text(encoding="utf-8")

    ch_yaml = yaml.safe_load(
        (
            seeded_env["library"]
            / "books/uipath-docs/chapters/01-activities/chapter.yaml"
        ).read_text(encoding="utf-8")
    )
    assert "retry-scope" in [s["id"] for s in ch_yaml["sections"]]

    follow = _run(["library-proposals", "list"], seeded_env["env"])
    assert p.proposal_id not in follow.stdout
    assert _log_contains_event(seeded_env["events_log"], "library_proposal_approved")


def test_reject_drops_without_touching_library(seeded_env):
    p = _enqueue_proposal(seeded_env["env"])
    result = _run(["library-proposals", "reject", p.proposal_id], seeded_env["env"])
    assert result.returncode == 0, result.stderr

    md = (
        seeded_env["library"]
        / "books/uipath-docs/chapters/01-activities/retry-scope.md"
    )
    assert not md.exists()

    follow = _run(["library-proposals", "list"], seeded_env["env"])
    assert p.proposal_id not in follow.stdout
    assert _log_contains_event(seeded_env["events_log"], "library_proposal_rejected")
