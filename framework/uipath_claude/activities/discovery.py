"""Resolve activity documentation: project .local docs, bundled skill refs, then CLI."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ActivityInfo:
    name: str
    full_name: str
    package_id: str
    description: str
    properties: dict
    example_xaml: str | None
    source: str


def _token_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


class ActivityDiscovery:
    """Priority: ``.local/docs/packages`` → bundled ``uipath-rpa`` references → ``uip`` CLI."""

    def __init__(self, skills_root: Path) -> None:
        self.skills_root = Path(skills_root)
        self._cache: dict[str, ActivityInfo | None] = {}

    def _read_markdown(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""

    def _search_local_docs(self, query: str, project_path: Path) -> ActivityInfo | None:
        key = _token_key(query)
        base = project_path / ".local" / "docs" / "packages"
        if not base.is_dir():
            return None
        for pkg_dir in base.iterdir():
            if not pkg_dir.is_dir():
                continue
            package_id = pkg_dir.name
            for md in pkg_dir.rglob("*.md"):
                stem_key = _token_key(md.stem)
                if key in stem_key or stem_key in key:
                    body = self._read_markdown(md)
                    return ActivityInfo(
                        name=md.stem,
                        full_name=f"{package_id}:{md.stem}",
                        package_id=package_id,
                        description=body[:500],
                        properties={},
                        example_xaml=None,
                        source="local_docs",
                    )
        return None

    def _search_bundled_docs(self, query: str) -> ActivityInfo | None:
        key = _token_key(query)
        bundled = (
            self.skills_root
            / "skills"
            / "uipath-rpa"
            / "references"
            / "activity-docs"
        )
        if not bundled.is_dir():
            return None
        for md in bundled.rglob("*.md"):
            stem_key = _token_key(md.stem)
            if key in stem_key or stem_key in key:
                body = self._read_markdown(md)
                parts = md.relative_to(bundled).parts
                package_id = parts[0] if len(parts) > 1 else "bundled"
                return ActivityInfo(
                    name=md.stem,
                    full_name=str(md.relative_to(bundled)),
                    package_id=package_id,
                    description=body[:500],
                    properties={},
                    example_xaml=None,
                    source="bundled",
                )
        return None

    def _search_live(self, query: str, project_path: Path) -> ActivityInfo | None:
        try:
            proc = subprocess.run(
                [
                    "uip",
                    "rpa",
                    "find-activities",
                    "--query",
                    query,
                    "--project-dir",
                    str(project_path.resolve()),
                    "--limit",
                    "1",
                    "--output",
                    "json",
                    "--use-studio",
                ],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return None
        text = (proc.stdout or "") + (proc.stderr or "")
        if query.lower() in text.lower() and proc.returncode == 0:
            return ActivityInfo(
                name=query,
                full_name=query,
                package_id="",
                description=text[:2000],
                properties={},
                example_xaml=None,
                source="live",
            )
        return None

    def find_activity(self, query: str, project_path: Path) -> ActivityInfo | None:
        cache_key = f"{project_path.resolve()}:{_token_key(query)}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        project_path = Path(project_path)
        for hit in (
            self._search_local_docs(query, project_path),
            self._search_bundled_docs(query),
            self._search_live(query, project_path),
        ):
            if hit:
                self._cache[cache_key] = hit
                return hit
        self._cache[cache_key] = None
        return None
