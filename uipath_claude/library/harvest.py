"""Harvest UiPath upstream skills into pending library proposals.

Walks the ``skills/skills/*/SKILL.md`` files in the UiPath/skills submodule
and enqueues a ``NEW_SECTION`` proposal per skill into the default ``uipath-docs``
book, ``best-practices`` chapter. Nothing is written to the library until a
human approves via ``uipath-claude library-proposals approve``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml

from uipath_claude.library.catalog import LibraryCatalog
from uipath_claude.library.proposals import (
    LibraryProposal,
    ProposalKind,
    ProposalStore,
)
from uipath_claude.skills.updater import get_skills_submodule_path

DEFAULT_BOOK_ID = "uipath-docs"
DEFAULT_CHAPTER_ID = "best-practices"
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
MAX_BODY_CHARS = 12_000


@dataclass
class HarvestResult:
    skipped_existing: list[str]
    proposed: list[str]
    skipped_missing: list[str]

    def summary(self) -> str:
        parts = []
        if self.proposed:
            parts.append(f"proposed {len(self.proposed)}: " + ", ".join(self.proposed))
        if self.skipped_existing:
            parts.append(
                f"skipped {len(self.skipped_existing)} already in library"
            )
        if self.skipped_missing:
            parts.append(
                f"skipped {len(self.skipped_missing)} (no SKILL.md/frontmatter)"
            )
        return "; ".join(parts) if parts else "nothing to harvest"


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    body = text[m.end():]
    return meta, body


def _section_id_for(skill_id: str) -> str:
    # Drop `uipath-` prefix for brevity but stay safe for filenames.
    cleaned = skill_id.removeprefix("uipath-")
    return re.sub(r"[^a-z0-9\-]", "-", cleaned.lower()) or skill_id


def _iter_upstream_skills(skills_root: Path) -> Iterable[tuple[str, Path]]:
    skills_dir = skills_root / "skills"
    if not skills_dir.exists():
        return
    for sdir in sorted(skills_dir.iterdir()):
        sk = sdir / "SKILL.md"
        if sdir.is_dir() and sk.exists():
            yield sdir.name, sk


def _existing_section_ids(book_id: str, chapter_id: str) -> set[str]:
    catalog = LibraryCatalog.load()
    book = catalog.get_book(book_id)
    if not book:
        return set()
    for ch in book.chapters:
        if ch.id == chapter_id:
            return {sec.id for sec in ch.sections}
    return set()


def harvest_upstream_skills(
    *,
    book_id: str = DEFAULT_BOOK_ID,
    chapter_id: str = DEFAULT_CHAPTER_ID,
    skills_root: Path | None = None,
    store: ProposalStore | None = None,
) -> HarvestResult:
    """Enqueue a library proposal per upstream skill (idempotent per section id)."""
    root = skills_root or get_skills_submodule_path()
    store = store or ProposalStore()
    existing = _existing_section_ids(book_id, chapter_id)
    pending = {
        p.section_id
        for p in store.list_pending()
        if p.book_id == book_id and p.chapter_id == chapter_id
    }

    proposed: list[str] = []
    skipped_existing: list[str] = []
    skipped_missing: list[str] = []

    for skill_id, skill_path in _iter_upstream_skills(root):
        text = skill_path.read_text(encoding="utf-8", errors="ignore")
        meta, body = _parse_frontmatter(text)
        if not body.strip():
            skipped_missing.append(skill_id)
            continue

        section_id = _section_id_for(skill_id)
        if section_id in existing or section_id in pending:
            skipped_existing.append(skill_id)
            continue

        title = (meta.get("name") or skill_id).strip()
        description = (meta.get("description") or "").strip()
        truncated = body.strip()[:MAX_BODY_CHARS]
        header = f"# {title}\n\n"
        if description:
            header += f"> {description}\n\n"
        content = header + truncated + (
            "\n\n---\n*Harvested from UiPath/skills/" + skill_id + "/SKILL.md*\n"
        )
        keywords = [skill_id, "uipath", "skill"]
        rationale = (
            "Auto-harvested from UiPath/skills upstream; pending human review."
        )
        store.enqueue(
            LibraryProposal(
                proposal_id="",
                book_id=book_id,
                chapter_id=chapter_id,
                section_id=section_id,
                section_title=title,
                kind=ProposalKind.NEW_SECTION,
                content=content,
                keywords=keywords,
                rationale=rationale,
                source_session="harvest:upstream-skills",
            )
        )
        proposed.append(skill_id)

    return HarvestResult(
        skipped_existing=skipped_existing,
        proposed=proposed,
        skipped_missing=skipped_missing,
    )
