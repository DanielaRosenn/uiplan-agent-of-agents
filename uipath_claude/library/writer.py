"""Write operations for the documentation library (sections + yaml)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import yaml

from uipath_claude.library.catalog import LibraryCatalog


def _assert_safe_segment(name: str, field: str) -> None:
    if not name or ".." in name or "/" in name or "\\" in name:
        raise ValueError(f"invalid {field}: {name!r}")


class LibraryWriter:
    """Create/update sections and keep chapter.yaml in sync."""

    def __init__(self, library_path: Path | None = None) -> None:
        self.library_path = library_path or LibraryCatalog.get_library_path()

    def _book_dir(self, book_id: str) -> Path:
        _assert_safe_segment(book_id, "book_id")
        catalog_file = self.library_path / "catalog.yaml"
        if not catalog_file.exists():
            raise ValueError(f"no catalog at {catalog_file}")
        data = yaml.safe_load(catalog_file.read_text(encoding="utf-8")) or {}
        for entry in data.get("books", []):
            if entry.get("id") == book_id:
                return self.library_path / entry["path"]
        raise ValueError(f"unknown book: {book_id}")

    def _chapter_dir(self, book_id: str, chapter_id: str) -> Path:
        _assert_safe_segment(chapter_id, "chapter_id")
        book_dir = self._book_dir(book_id)
        book_yaml = book_dir / "book.yaml"
        data = yaml.safe_load(book_yaml.read_text(encoding="utf-8")) or {}
        for ch in data.get("chapters", []):
            if ch.get("id") == chapter_id:
                return book_dir / ch["path"]
        raise ValueError(f"unknown chapter: {chapter_id} in {book_id}")

    def create_section(
        self,
        *,
        book_id: str,
        chapter_id: str,
        section_id: str,
        section_title: str,
        content: str,
        keywords: Iterable[str],
    ) -> Path:
        """Create (or upsert) a section markdown file and chapter.yaml entry."""
        _assert_safe_segment(section_id, "section_id")
        chapter_dir = self._chapter_dir(book_id, chapter_id)
        md_path = chapter_dir / f"{section_id}.md"
        md_path.write_text(content, encoding="utf-8")

        chapter_yaml = chapter_dir / "chapter.yaml"
        data = yaml.safe_load(chapter_yaml.read_text(encoding="utf-8")) or {}
        sections = data.get("sections", [])
        if not any(s.get("id") == section_id for s in sections):
            sections.append(
                {
                    "id": section_id,
                    "title": section_title,
                    "file": f"{section_id}.md",
                    "keywords": list(keywords),
                }
            )
            data["sections"] = sections
            chapter_yaml.write_text(
                yaml.dump(data, default_flow_style=False, sort_keys=False),
                encoding="utf-8",
            )
        return md_path

    def update_section(
        self,
        *,
        book_id: str,
        chapter_id: str,
        section_id: str,
        content: str,
    ) -> Path:
        """Overwrite an existing section's markdown body."""
        _assert_safe_segment(section_id, "section_id")
        chapter_dir = self._chapter_dir(book_id, chapter_id)
        md_path = chapter_dir / f"{section_id}.md"
        if not md_path.exists():
            raise ValueError(
                f"section does not exist: {book_id}/{chapter_id}/{section_id}"
            )
        md_path.write_text(content, encoding="utf-8")
        return md_path

    def create_chapter(
        self,
        *,
        book_id: str,
        chapter_id: str,
        chapter_title: str,
        order: int | None = None,
        initial_sections: list[dict[str, Any]] | None = None,
    ) -> Path:
        """Add a new chapter directory, book.yaml entry, and optional starter sections."""
        _assert_safe_segment(chapter_id, "chapter_id")
        book_dir = self._book_dir(book_id)
        book_yaml_path = book_dir / "book.yaml"
        if not book_yaml_path.exists():
            raise ValueError(f"no book.yaml at {book_yaml_path}")
        data = yaml.safe_load(book_yaml_path.read_text(encoding="utf-8")) or {}
        chapters = list(data.get("chapters", []))
        if order is None:
            orders = [int(c.get("order", 0)) for c in chapters]
            order = max(orders, default=0) + 1
        rel_path = f"chapters/{order:02d}-{chapter_id}"
        ch_dir = book_dir / rel_path
        if ch_dir.exists():
            raise ValueError(f"chapter path already exists: {rel_path}")
        ch_dir.mkdir(parents=True)

        sections_yaml: list[dict[str, Any]] = []
        for sec in initial_sections or []:
            sid = sec.get("id") or ""
            _assert_safe_segment(sid, "section_id")
            title = sec.get("title") or sid
            content = sec.get("content", "")
            keywords = sec.get("keywords") or []
            md_path = ch_dir / f"{sid}.md"
            md_path.write_text(str(content), encoding="utf-8")
            sections_yaml.append(
                {
                    "id": sid,
                    "title": title,
                    "file": f"{sid}.md",
                    "keywords": list(keywords),
                }
            )

        chapter_yaml_data = {
            "id": chapter_id,
            "title": chapter_title,
            "sections": sections_yaml,
        }
        (ch_dir / "chapter.yaml").write_text(
            yaml.dump(chapter_yaml_data, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )

        chapters.append(
            {
                "id": chapter_id,
                "order": order,
                "path": rel_path,
                "title": chapter_title,
            }
        )
        data["chapters"] = sorted(chapters, key=lambda c: int(c.get("order", 0)))
        book_yaml_path.write_text(
            yaml.dump(data, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
        return ch_dir
