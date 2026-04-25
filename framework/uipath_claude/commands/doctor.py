"""Read-only environment health checks for UiPath Builder Agent."""

from __future__ import annotations

import importlib.util
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import shutil
from typing import Callable

import typer
import yaml

from uipath_claude.library.catalog import LibraryCatalog
from uipath_claude.library.proposals import PROPOSALS_ENV_VAR, ProposalStore


Status = str


@dataclass(frozen=True)
class DoctorCheck:
    group: str
    name: str
    status: Status
    detail: str


def _ok(group: str, name: str, detail: str) -> DoctorCheck:
    return DoctorCheck(group, name, "ok", detail)


def _warn(group: str, name: str, detail: str) -> DoctorCheck:
    return DoctorCheck(group, name, "warn", detail)


def _fail(group: str, name: str, detail: str) -> DoctorCheck:
    return DoctorCheck(group, name, "fail", detail)


def _parse_created_at(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _markdown_mojibake(root: Path) -> list[str]:
    offenders: list[str] = []
    patterns = ("\u0393\u00c7", "\u0393\u00e5")
    for path in root.rglob("*.md"):
        if any(part in {".git", ".venv", "node_modules"} for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(pattern in text for pattern in patterns):
            offenders.append(str(path.relative_to(root)))
    return offenders


def _mcp_docs_current(root: Path) -> bool:
    script = root / "ops" / "scripts" / "generate_mcp_tools_doc.py"
    doc = root / "docs" / "MCP_TOOLS.md"
    if not script.is_file() or not doc.is_file():
        return False
    spec = importlib.util.spec_from_file_location("generate_mcp_tools_doc", script)
    if spec is None or spec.loader is None:
        return False
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return doc.read_text(encoding="utf-8") == module.build_markdown()


def _library_catalog_issues(root: Path) -> list[str]:
    issues: list[str] = []
    library_root = LibraryCatalog.get_library_path()
    try:
        catalog = LibraryCatalog.load()
    except (OSError, yaml.YAMLError, KeyError, TypeError) as exc:
        return [f"catalog load failed: {exc}"]

    seen_books: set[str] = set()
    for book in catalog.books:
        if book.id in seen_books:
            issues.append(f"duplicate book id: {book.id}")
        seen_books.add(book.id)
        if not book.manifest.curator:
            issues.append(f"{book.id}: missing MANIFEST curator")
        book_dir = library_root / book.path
        seen_chapters: set[str] = set()
        for chapter in book.chapters:
            if chapter.id in seen_chapters:
                issues.append(f"{book.id}: duplicate chapter id {chapter.id}")
            seen_chapters.add(chapter.id)
            seen_sections: set[str] = set()
            for section in chapter.sections:
                key = f"{chapter.id}/{section.id}"
                if key in seen_sections:
                    issues.append(f"{book.id}: duplicate section id {key}")
                seen_sections.add(key)
                section_file = book_dir / chapter.path / section.file
                if not section_file.is_file():
                    issues.append(f"{book.id}: missing section file {key}")
                    continue
                try:
                    section_file.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    issues.append(f"{book.id}: unreadable utf-8 section {key}")
                except OSError as exc:
                    issues.append(f"{book.id}: cannot read section {key}: {exc}")
    return issues


def _library_proposal_issues(stale_days: int) -> tuple[int, list[str]]:
    proposal_root = Path(
        os.environ.get(PROPOSALS_ENV_VAR, Path.home() / ".uipath-claude" / "library-proposals")
    ).expanduser()
    if not proposal_root.exists():
        return 0, []
    store = ProposalStore(root=proposal_root)
    pending = store.list_pending()
    issues: list[str] = []
    now = datetime.now(timezone.utc)
    seen_targets: set[tuple[str, str, str]] = set()
    for proposal in pending:
        target = (proposal.book_id, proposal.chapter_id, proposal.section_id)
        if target in seen_targets:
            issues.append(
                f"duplicate pending target: {proposal.book_id}/{proposal.chapter_id}/{proposal.section_id}"
            )
        seen_targets.add(target)
        created_at = _parse_created_at(proposal.created_at)
        if created_at is None:
            issues.append(f"{proposal.proposal_id}: invalid created_at")
        elif (now - created_at).days > stale_days:
            issues.append(f"{proposal.proposal_id}: stale for {(now - created_at).days} days")
    return len(pending), issues


def run_doctor(
    root: Path | None = None,
    *,
    stale_proposal_days: int = 14,
    which: Callable[[str], str | None] = shutil.which,
) -> list[DoctorCheck]:
    """Run read-only health checks and return structured results."""
    root = (root or Path.cwd()).resolve()
    checks: list[DoctorCheck] = []

    skills_root = root / "skills" / "skills"
    if (skills_root / "uipath-rpa").is_dir() and (skills_root / "uipath-interact").is_dir():
        checks.append(_ok("Skills", "submodule", "official skills are initialized"))
    else:
        checks.append(_fail("Skills", "submodule", "missing skills/skills/uipath-rpa or uipath-interact"))

    cursor_skills = root / ".cursor" / "skills"
    if (cursor_skills / "uipath-interact" / "SKILL.md").is_file():
        checks.append(_ok("Cursor", "uipath-interact", "canonical Cursor skill exists"))
    else:
        checks.append(_warn("Cursor", "uipath-interact", "missing .cursor/skills/uipath-interact/SKILL.md"))
    servo_skill = cursor_skills / "uipath-servo" / "SKILL.md"
    if servo_skill.is_file():
        text = servo_skill.read_text(encoding="utf-8", errors="replace").lower()
        if "uipath-interact" in text and "compatibility" in text:
            checks.append(_ok("Cursor", "servo redirect", "legacy uipath-servo redirects to uipath-interact"))
        else:
            checks.append(_warn("Cursor", "servo redirect", "uipath-servo exists but is not a redirect"))

    mcp_config = root / ".cursor" / "mcp.json"
    mcp_example = root / ".cursor" / "mcp.json.example"
    if mcp_config.is_file():
        checks.append(_ok("Cursor", "MCP config", ".cursor/mcp.json exists"))
    elif mcp_example.is_file():
        checks.append(_warn("Cursor", "MCP config", "copy .cursor/mcp.json.example to .cursor/mcp.json"))
    else:
        checks.append(_fail("Cursor", "MCP config", "missing .cursor/mcp.json and example"))

    checks.append(
        _ok("Tools", "uip", f"found {which('uip')}")
        if which("uip")
        else _warn("Tools", "uip", "uip CLI not found on PATH")
    )

    try:
        import uipath_claude  # noqa: F401

        checks.append(_ok("Runtime", "import", "uipath_claude imports successfully"))
    except Exception as exc:  # pragma: no cover - defensive diagnostic
        checks.append(_fail("Runtime", "import", f"cannot import uipath_claude: {exc}"))

    try:
        checks.append(
            _ok("Docs", "MCP docs", "docs/MCP_TOOLS.md is generated from current tools")
            if _mcp_docs_current(root)
            else _warn("Docs", "MCP docs", "run python ops/scripts/generate_mcp_tools_doc.py")
        )
    except Exception as exc:
        checks.append(_warn("Docs", "MCP docs", f"could not compare generated docs: {exc}"))

    mojibake = _markdown_mojibake(root)
    checks.append(
        _ok("Docs", "encoding", "no common markdown mojibake found")
        if not mojibake
        else _warn("Docs", "encoding", f"mojibake in {len(mojibake)} markdown files")
    )

    catalog_issues = _library_catalog_issues(root)
    checks.append(
        _ok("Library", "catalog", "library catalog and sections are readable")
        if not catalog_issues
        else _warn("Library", "catalog", "; ".join(catalog_issues[:5]))
    )
    pending_count, proposal_issues = _library_proposal_issues(stale_proposal_days)
    if proposal_issues:
        checks.append(_warn("Library", "proposals", f"{pending_count} pending; " + "; ".join(proposal_issues[:5])))
    else:
        checks.append(_ok("Library", "proposals", f"{pending_count} pending proposals"))

    return checks


def _format_checks(checks: list[DoctorCheck]) -> str:
    icon = {"ok": "OK", "warn": "WARN", "fail": "FAIL"}
    lines = ["UiPath Builder Agent doctor"]
    current_group = None
    for check in checks:
        if check.group != current_group:
            current_group = check.group
            lines.append("")
            lines.append(f"{current_group}:")
        lines.append(f"  [{icon.get(check.status, check.status.upper())}] {check.name}: {check.detail}")
    return "\n".join(lines)


def register_doctor_command(app: typer.Typer) -> None:
    """Register the top-level ``doctor`` command."""

    @app.command("doctor")
    def doctor_cmd(
        json_output: bool = typer.Option(False, "--json", help="Emit JSON instead of text."),
        stale_proposal_days: int = typer.Option(
            14,
            "--stale-proposal-days",
            help="Warn when pending library proposals are older than this many days.",
        ),
    ) -> None:
        checks = run_doctor(stale_proposal_days=stale_proposal_days)
        if json_output:
            typer.echo(json.dumps([check.__dict__ for check in checks], indent=2))
        else:
            typer.echo(_format_checks(checks))
        if any(check.status == "fail" for check in checks):
            raise typer.Exit(code=1)
