"""Tests for the read-only doctor command."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from typer.testing import CliRunner

from uipath_claude.cli.app import app
from uipath_claude.commands.doctor import run_doctor
from uipath_claude.library.proposals import PROPOSALS_ENV_VAR


def _minimal_repo(root: Path) -> None:
    (root / "skills" / "skills" / "uipath-rpa").mkdir(parents=True)
    (root / "skills" / "skills" / "uipath-interact").mkdir(parents=True)
    (root / ".cursor" / "skills" / "uipath-rpa").mkdir(parents=True)
    (root / ".cursor" / "skills" / "uipath-rpa" / "SKILL.md").write_text(
        "---\nname: uipath-rpa\n---\n",
        encoding="utf-8",
    )
    (root / ".cursor" / "skills" / "uipath-interact").mkdir(parents=True)
    (root / ".cursor" / "skills" / "uipath-interact" / "SKILL.md").write_text(
        "---\nname: uipath-interact\n---\n",
        encoding="utf-8",
    )
    (root / ".cursor" / "skills" / "uipath-servo").mkdir(parents=True)
    (root / ".cursor" / "skills" / "uipath-servo" / "SKILL.md").write_text(
        "compatibility redirect to uipath-interact\n",
        encoding="utf-8",
    )
    (root / ".cursor" / "mcp.json.example").write_text("{}", encoding="utf-8")
    (root / "data" / "library").mkdir(parents=True)
    (root / "data" / "library" / "catalog.yaml").write_text(
        "version: 1\nbooks: []\n",
        encoding="utf-8",
    )


def test_run_doctor_reports_core_health(tmp_path, monkeypatch):
    _minimal_repo(tmp_path)
    monkeypatch.setenv("UIPATH_CLAUDE_LIBRARY", str(tmp_path / "data" / "library"))
    monkeypatch.setenv(PROPOSALS_ENV_VAR, str(tmp_path / "missing-proposals"))

    checks = run_doctor(tmp_path, which=lambda name: "C:/tools/uip.exe" if name == "uip" else None)
    by_name = {(check.group, check.name): check for check in checks}

    assert by_name[("Skills", "submodule")].status == "ok"
    assert by_name[("Cursor", "skills alignment")].status == "ok"
    assert by_name[("Cursor", "uipath-interact")].status == "ok"
    assert by_name[("Cursor", "servo redirect")].status == "ok"
    assert by_name[("Tools", "uip")].status == "ok"
    assert by_name[("Library", "proposals")].status == "ok"


def test_doctor_warns_on_stale_duplicate_library_proposals(tmp_path, monkeypatch):
    _minimal_repo(tmp_path)
    proposals = tmp_path / "proposals"
    proposals.mkdir()
    old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat().replace("+00:00", "Z")
    payload = [
        {
            "proposal_id": "p1",
            "book_id": "book",
            "chapter_id": "chapter",
            "section_id": "section",
            "section_title": "Title",
            "kind": "new_section",
            "content": "body",
            "status": "pending",
            "created_at": old,
        },
        {
            "proposal_id": "p2",
            "book_id": "book",
            "chapter_id": "chapter",
            "section_id": "section",
            "section_title": "Title 2",
            "kind": "new_section",
            "content": "body",
            "status": "pending",
            "created_at": old,
        },
    ]
    (proposals / "book.json").write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("UIPATH_CLAUDE_LIBRARY", str(tmp_path / "data" / "library"))
    monkeypatch.setenv(PROPOSALS_ENV_VAR, str(proposals))

    checks = run_doctor(tmp_path, which=lambda _name: None, stale_proposal_days=14)
    proposal_check = next(c for c in checks if c.group == "Library" and c.name == "proposals")

    assert proposal_check.status == "warn"
    assert "duplicate pending target" in proposal_check.detail
    assert "stale" in proposal_check.detail


def test_doctor_warns_on_cursor_skill_drift(tmp_path, monkeypatch):
    _minimal_repo(tmp_path)
    (tmp_path / "skills" / "skills" / "uipath-gov-aops-policy").mkdir(parents=True)
    (tmp_path / ".cursor" / "skills" / "unknown-local-skill").mkdir(parents=True)
    monkeypatch.setenv("UIPATH_CLAUDE_LIBRARY", str(tmp_path / "data" / "library"))
    monkeypatch.setenv(PROPOSALS_ENV_VAR, str(tmp_path / "missing-proposals"))

    checks = run_doctor(tmp_path, which=lambda _name: None)
    alignment = next(c for c in checks if c.group == "Cursor" and c.name == "skills alignment")

    assert alignment.status == "warn"
    assert "missing upstream skills" in alignment.detail
    assert "unmanaged Cursor-only skills" in alignment.detail


def test_doctor_warns_on_non_uv_mcp_launch(tmp_path, monkeypatch):
    _minimal_repo(tmp_path)
    (tmp_path / ".cursor" / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "uipath-builder-agent": {
                        "command": "python",
                        "args": ["-m", "mcp_server.server"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("UIPATH_CLAUDE_LIBRARY", str(tmp_path / "data" / "library"))
    monkeypatch.setenv(PROPOSALS_ENV_VAR, str(tmp_path / "missing-proposals"))

    checks = run_doctor(tmp_path, which=lambda _name: None)
    launch = next(c for c in checks if c.group == "Cursor" and c.name == "MCP launch")

    assert launch.status == "warn"
    assert "uv run python -m mcp_server.server" in launch.detail


def test_doctor_cli_json(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(
        "uipath_claude.commands.doctor.run_doctor",
        lambda **_kwargs: [],
    )

    result = runner.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "[]"
