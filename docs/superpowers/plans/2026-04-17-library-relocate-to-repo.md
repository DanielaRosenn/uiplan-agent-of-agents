# Library Relocate to Repo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the default documentation library location from `~/.uipath-claude/library/` into the repo at `data/library/`, commit the seeded library content, and separate the (currently dead) query cache so the library folder stays clean and committable.

**Architecture:** `LibraryCatalog.get_library_path()` default changes to a repo-relative path resolved from `catalog.py`'s location. `UIPATH_CLAUDE_LIBRARY` env var still overrides. The `_cache/` directory — which is mutable, machine-local memoization, and currently dead code — moves out of the library into its own user-scoped location (`~/.uipath-claude/library-cache/`) so committing `data/library/` doesn't drag a cache along. `LibraryReader.__init__` gains a `cache_path` attribute so cache location is independent of content location. Existing seeded content at `~/.uipath-claude/library/` is copied into the repo.

**Tech Stack:** Python 3.12, pytest, PyYAML. Windows PowerShell for shell commands.

---

## File Structure

**Modified:**
- `uipath_claude/library/catalog.py` — default path changes to repo-relative; new helper `_default_library_path()` introduced for clarity. Keeps `LIBRARY_PATH_ENV_VAR` override.
- `uipath_claude/library/reader.py` — cache directory becomes `LibraryReader._default_cache_path()` returning `~/.uipath-claude/library-cache/` (overridable via constructor arg `cache_path` and env var `UIPATH_CLAUDE_LIBRARY_CACHE`). `get_cached_response` / `cache_response` use `self.cache_path` instead of `self.library_path / "books" / "uipath-docs" / "_cache"`.
- `scripts/seed_uipath_docs.py` — unchanged logic, but it inherits the new default path automatically. Adds a `--target` CLI flag for explicit overrides (useful in CI).
- `tests/unit/library/test_catalog.py` — updates the "defaults to home" assertion, adds assertion for repo-relative default.
- `tests/unit/library/test_reader.py` — NEW file covering cache location.
- `README.md` — add "Runtime data locations" section.
- `.gitignore` — ensure `data/library/books/*/\_cache/` is ignored defensively (belt-and-braces; the cache is moving out, but legacy `_cache` directories inside any checked-in book must never be committed).

**Created:**
- `data/library/` — seeded library content, copied from `~/.uipath-claude/library/`.
- `data/library/catalog.yaml`, `data/library/books/uipath-docs/*` — existing content relocated.

**Unchanged but affected (no code edits, behavior changes because of new default):**
- `uipath_claude/tools/library_tools.py` — calls `LibraryCatalog.load()` which picks up the new default.

---

## Task 1: Update catalog default path to repo-relative

**Files:**
- Modify: `uipath_claude/library/catalog.py` (replace the `get_library_path` classmethod and add `_default_library_path`)
- Test: `tests/unit/library/test_catalog.py` (update `test_get_library_path_defaults_to_home` → `test_get_library_path_defaults_to_repo_data_dir`, keep env-var override tests)

- [ ] **Step 1: Write the failing test**

Replace the body of `test_get_library_path_defaults_to_home` in `tests/unit/library/test_catalog.py` with a new test that asserts the default is repo-relative:

```python
def test_get_library_path_defaults_to_repo_data_dir(monkeypatch):
    monkeypatch.delenv(LIBRARY_PATH_ENV_VAR, raising=False)
    expected = (
        Path(__file__).resolve().parents[3] / "data" / "library"
    )
    assert LibraryCatalog.get_library_path() == expected
```

Note: `parents[3]` because the test file lives at `tests/unit/library/test_catalog.py` → `parents[0]=library`, `[1]=unit`, `[2]=tests`, `[3]=<repo root>`.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/library/test_catalog.py::test_get_library_path_defaults_to_repo_data_dir -v`
Expected: FAIL — assertion compares `~/.uipath-claude/library` (current default) against `<repo>/data/library`.

- [ ] **Step 3: Modify `catalog.py` to use repo-relative default**

Replace the `get_library_path` classmethod in `uipath_claude/library/catalog.py` (currently lines 51–62):

```python
    @classmethod
    def _default_library_path(cls) -> Path:
        """Repo-relative default: ``<repo>/data/library``.

        Resolved from this file's location. ``catalog.py`` lives at
        ``<repo>/uipath_claude/library/catalog.py`` so ``parents[2]`` is the repo root.
        """
        return Path(__file__).resolve().parents[2] / "data" / "library"

    @classmethod
    def get_library_path(cls) -> Path:
        """Get the library root path.

        Resolves in this order:
        1. ``UIPATH_CLAUDE_LIBRARY`` environment variable, if set.
        2. Repo-relative default: ``<repo>/data/library``.
        """
        override = os.environ.get(LIBRARY_PATH_ENV_VAR)
        if override:
            return Path(override).expanduser()
        return cls._default_library_path()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/library/test_catalog.py -v`
Expected: All 9 tests pass (the renamed default test plus the 3 env-var tests plus 5 existing).

- [ ] **Step 5: Commit**

```bash
git add uipath_claude/library/catalog.py tests/unit/library/test_catalog.py
git commit -m "refactor(library): default library path is repo-relative (data/library)"
```

---

## Task 2: Decouple cache path from library path in `LibraryReader`

**Files:**
- Modify: `uipath_claude/library/reader.py` (full rewrite of constructor and cache methods)
- Create: `tests/unit/library/test_reader.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/library/test_reader.py`:

```python
"""Tests for library reader, especially cache path independence."""
import os
from pathlib import Path

import pytest

from uipath_claude.library.catalog import LibraryCatalog
from uipath_claude.library.reader import (
    LIBRARY_CACHE_ENV_VAR,
    LibraryReader,
)


def test_default_cache_path_is_user_scoped(monkeypatch):
    monkeypatch.delenv(LIBRARY_CACHE_ENV_VAR, raising=False)
    reader = LibraryReader(catalog=LibraryCatalog(books=[]))
    assert reader.cache_path == Path.home() / ".uipath-claude" / "library-cache"


def test_cache_path_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv(LIBRARY_CACHE_ENV_VAR, str(tmp_path / "cache"))
    reader = LibraryReader(catalog=LibraryCatalog(books=[]))
    assert reader.cache_path == tmp_path / "cache"


def test_cache_path_constructor_arg_wins(monkeypatch, tmp_path):
    monkeypatch.setenv(LIBRARY_CACHE_ENV_VAR, str(tmp_path / "env"))
    explicit = tmp_path / "explicit"
    reader = LibraryReader(
        catalog=LibraryCatalog(books=[]), cache_path=explicit
    )
    assert reader.cache_path == explicit


def test_cache_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv(LIBRARY_CACHE_ENV_VAR, str(tmp_path))
    reader = LibraryReader(catalog=LibraryCatalog(books=[]))
    assert reader.get_cached_response("hello") is None
    reader.cache_response("hello", "world")
    assert reader.get_cached_response("hello") == "world"


def test_cache_does_not_touch_library_dir(tmp_path, monkeypatch):
    library_root = tmp_path / "library"
    library_root.mkdir()
    cache_root = tmp_path / "cache"
    monkeypatch.setenv("UIPATH_CLAUDE_LIBRARY", str(library_root))
    monkeypatch.setenv(LIBRARY_CACHE_ENV_VAR, str(cache_root))

    reader = LibraryReader(catalog=LibraryCatalog(books=[]))
    reader.cache_response("x", "y")

    assert list(library_root.rglob("*")) == []
    assert any(cache_root.rglob("*.json"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/library/test_reader.py -v`
Expected: FAIL — `LIBRARY_CACHE_ENV_VAR` not importable; `LibraryReader` has no `cache_path` attribute.

- [ ] **Step 3: Rewrite `reader.py`**

Replace the full contents of `uipath_claude/library/reader.py` with:

```python
"""Library section reader with optional query-response caching."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from uipath_claude.library.catalog import LibraryCatalog

LIBRARY_CACHE_ENV_VAR = "UIPATH_CLAUDE_LIBRARY_CACHE"


def _default_cache_path() -> Path:
    """Default cache location: ``~/.uipath-claude/library-cache``.

    Cache is machine-local, mutable, and derivable — it must live outside
    the (committable) library content directory.
    """
    override = os.environ.get(LIBRARY_CACHE_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return Path.home() / ".uipath-claude" / "library-cache"


class LibraryReader:
    """Read sections from the documentation library."""

    CACHE_TTL = timedelta(days=30)

    def __init__(
        self,
        catalog: LibraryCatalog | None = None,
        cache_path: Path | None = None,
    ) -> None:
        """Initialize reader.

        Args:
            catalog: Optional preloaded catalog (loaded via ``LibraryCatalog.load()`` if ``None``).
            cache_path: Optional override for the query-cache directory. Falls back to
                ``UIPATH_CLAUDE_LIBRARY_CACHE`` env var, then ``~/.uipath-claude/library-cache``.
        """
        self.catalog = catalog or LibraryCatalog.load()
        self.library_path = LibraryCatalog.get_library_path()
        self.cache_path = Path(cache_path) if cache_path else _default_cache_path()

    def read_section(
        self, book_id: str, chapter_id: str, section_id: str
    ) -> str | None:
        """Read a section's content."""
        book = self.catalog.get_book(book_id)
        if not book:
            return None

        chapter = None
        for ch in book.chapters:
            if ch.id == chapter_id:
                chapter = ch
                break
        if not chapter:
            return None

        section = None
        for sec in chapter.sections:
            if sec.id == section_id:
                section = sec
                break
        if not section:
            return None

        section_path = self.library_path / book.path / chapter.path / section.file
        if not section_path.exists():
            return None
        return section_path.read_text(encoding="utf-8")

    def _cache_file(self, query: str) -> Path:
        cache_key = hashlib.md5(query.lower().encode()).hexdigest()
        return self.cache_path / f"{cache_key}.json"

    def get_cached_response(self, query: str) -> str | None:
        """Return a cached response for ``query`` if present and within TTL."""
        cache_file = self._cache_file(query)
        if not cache_file.exists():
            return None
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            cached_at = datetime.fromisoformat(data["cached_at"])
            if datetime.now() - cached_at > self.CACHE_TTL:
                return None
            return data["response"]
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def cache_response(self, query: str, response: str) -> None:
        """Persist a query→response pair in the cache directory."""
        self.cache_path.mkdir(parents=True, exist_ok=True)
        cache_file = self._cache_file(query)
        data = {
            "query": query,
            "response": response,
            "cached_at": datetime.now().isoformat(),
        }
        cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/library/test_reader.py tests/unit/library/test_catalog.py -v`
Expected: All tests pass (9 in `test_catalog.py`, 5 in `test_reader.py`).

- [ ] **Step 5: Commit**

```bash
git add uipath_claude/library/reader.py tests/unit/library/test_reader.py
git commit -m "refactor(library): move query cache out of library dir; add UIPATH_CLAUDE_LIBRARY_CACHE override"
```

---

## Task 3: Remove stale `_cache` creation from seed script

**Files:**
- Modify: `scripts/seed_uipath_docs.py:262-264` (delete the `_cache` directory creation)

- [ ] **Step 1: Write the failing test**

Create `tests/unit/scripts/test_seed_uipath_docs.py` (the directory may not exist; create it and add an `__init__.py` if conventional — check `tests/unit/` for pattern). If tests in `tests/unit/` use no `__init__.py`, skip creating one.

```python
"""Tests for the documentation library seed script."""
import subprocess
import sys
from pathlib import Path


def test_seed_script_does_not_create_cache_inside_book(tmp_path, monkeypatch):
    monkeypatch.setenv("UIPATH_CLAUDE_LIBRARY", str(tmp_path))
    repo_root = Path(__file__).resolve().parents[3]
    script = repo_root / "scripts" / "seed_uipath_docs.py"

    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "UIPATH_CLAUDE_LIBRARY": str(tmp_path)},
        cwd=str(repo_root),
    )
    assert result.returncode == 0, result.stderr

    cache_dirs = list(tmp_path.rglob("_cache"))
    assert cache_dirs == [], f"seed created cache dir(s) inside library: {cache_dirs}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/scripts/test_seed_uipath_docs.py -v`
Expected: FAIL — the current seed script creates `books/uipath-docs/_cache/`.

- [ ] **Step 3: Remove the cache-creation block in the seed script**

In `scripts/seed_uipath_docs.py`, delete these three lines (currently around lines 262–264):

```python
    # Create _cache directory
    cache_dir = book_path / "_cache"
    cache_dir.mkdir(exist_ok=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/scripts/test_seed_uipath_docs.py -v`
Expected: PASS. No `_cache` directory created under the library.

- [ ] **Step 5: Commit**

```bash
git add scripts/seed_uipath_docs.py tests/unit/scripts/test_seed_uipath_docs.py
git commit -m "chore(seed): stop creating dead _cache dir inside seeded book"
```

---

## Task 4: Add `--target` flag to seed script

**Files:**
- Modify: `scripts/seed_uipath_docs.py` (add argparse, thread `target` into `create_library_structure`)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/scripts/test_seed_uipath_docs.py`:

```python
def test_seed_script_target_flag_overrides_env(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    script = repo_root / "scripts" / "seed_uipath_docs.py"
    target = tmp_path / "custom"

    result = subprocess.run(
        [sys.executable, str(script), "--target", str(target)],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    assert result.returncode == 0, result.stderr
    assert (target / "catalog.yaml").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/scripts/test_seed_uipath_docs.py::test_seed_script_target_flag_overrides_env -v`
Expected: FAIL — `--target` is an unrecognized argument.

- [ ] **Step 3: Add argparse to the seed script**

In `scripts/seed_uipath_docs.py`, replace the `if __name__ == "__main__":` block at the bottom and the top of `create_library_structure()` with:

```python
def create_library_structure(target: Path | None = None) -> None:
    """Create the library directory structure and seed content."""
    library_path = target or LibraryCatalog.get_library_path()
    # ... rest of function body unchanged (note: the function currently
    # derives library_path from LibraryCatalog.get_library_path() at line 174;
    # replace that single line with the conditional above)
```

Then replace the entrypoint:

```python
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        type=Path,
        default=None,
        help="Target library directory (overrides UIPATH_CLAUDE_LIBRARY and default)",
    )
    args = parser.parse_args()
    create_library_structure(target=args.target)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/scripts/test_seed_uipath_docs.py -v`
Expected: both tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/seed_uipath_docs.py tests/unit/scripts/test_seed_uipath_docs.py
git commit -m "feat(seed): add --target flag to seed_uipath_docs.py"
```

---

## Task 5: Copy existing library into `data/library/` and commit it

**Files:**
- Create: `data/library/catalog.yaml`, `data/library/books/uipath-docs/book.yaml`, and all chapter/section files (copied from `~/.uipath-claude/library/`).

- [ ] **Step 1: Verify source exists and inspect what will be copied**

Run (PowerShell):

```powershell
Get-ChildItem "$env:USERPROFILE\.uipath-claude\library" -Recurse | Select-Object FullName, Length
```

Expected: see `catalog.yaml`, `books\uipath-docs\book.yaml`, chapter folders, section `.md` files. If the `_cache\` dir is present, it will be skipped in the next step.

- [ ] **Step 2: Copy library content into the repo, excluding `_cache`**

Run (PowerShell, from repo root):

```powershell
$src = "$env:USERPROFILE\.uipath-claude\library"
$dst = "data\library"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
robocopy $src $dst /E /XD _cache
```

Expected: `robocopy` exit code 0 or 1 (both indicate success — 1 means files were copied). Ignore exit codes >= 8 (failure). Confirm layout:

```powershell
Get-ChildItem data\library -Recurse | Select-Object FullName
```

- [ ] **Step 3: Run the full test suite to ensure nothing broke**

Run: `pytest tests/unit/library/ tests/unit/scripts/ -v`
Expected: all tests pass. The catalog tests rely on paths, not content, so this should be green.

- [ ] **Step 4: Verify the agent can read the library from the new location**

Run:

```powershell
python -c "from uipath_claude.library.catalog import LibraryCatalog; c = LibraryCatalog.load(); print([b.id for b in c.books]); print('chapters:', [ch.id for b in c.books for ch in b.chapters])"
```

Expected output:
```
['uipath-docs']
chapters: ['activities', 'orchestrator', 'studio', 'best-practices']
```

- [ ] **Step 5: Commit the library content**

```bash
git add data/library
git commit -m "chore(library): seed data/library with initial uipath-docs content"
```

---

## Task 6: Defensive `.gitignore` entry for legacy cache dirs

**Files:**
- Modify: `.gitignore` (add one line near the "Local runtime / tooling data" block)

- [ ] **Step 1: Write the failing test**

Create `tests/unit/meta/test_gitignore.py`:

```python
"""Meta-tests for .gitignore invariants."""
from pathlib import Path


def test_gitignore_excludes_library_cache_dirs():
    repo_root = Path(__file__).resolve().parents[3]
    gitignore = (repo_root / ".gitignore").read_text(encoding="utf-8")
    assert "data/library/**/_cache/" in gitignore, (
        "Defensive ignore for legacy _cache dirs missing from .gitignore"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/meta/test_gitignore.py -v`
Expected: FAIL.

- [ ] **Step 3: Add the ignore rule**

In `.gitignore`, directly after the existing `# Local runtime / tooling data` block (after the line `.skills_refresh_at`), add:

```
# Legacy cache dirs accidentally created inside committed library content
data/library/**/_cache/
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/meta/test_gitignore.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .gitignore tests/unit/meta/test_gitignore.py
git commit -m "chore(gitignore): defensively ignore _cache inside committed library"
```

---

## Task 7: Document runtime data locations in README

**Files:**
- Modify: `README.md` (add a new section)

- [ ] **Step 1: Locate a suitable insertion point**

Open `README.md` and find a section near the existing "Global" / "Project" memory tables (search for `Global memory` or `.uipath-claude/memory.md`). Insert the new section just after that table.

- [ ] **Step 2: Add the new section**

Insert this block verbatim:

```markdown
## Runtime data locations

The agent persists several kinds of data. The defaults balance "in-repo, reproducible" content vs. "machine-local" user state.

| Data | Default location | Override |
|---|---|---|
| Library (books/chapters/sections) | `<repo>/data/library/` | `UIPATH_CLAUDE_LIBRARY` env var |
| Library query cache | `~/.uipath-claude/library-cache/` | `UIPATH_CLAUDE_LIBRARY_CACHE` env var or `LibraryReader(cache_path=...)` |
| Structured event log | `~/.uipath-claude/logs/events.log` | `UIPATH_EVENT_LOG` env var |
| Session JSONL | `~/.uipath-claude/sessions/` | `SessionStore(root=...)` constructor arg |
| Global memory | `~/.uipath-claude/memory.md` | Respects `HOME` env var |
| Project memory | `<project>/.uipath-claude/memory.md` | Per-project |
| Skill insights (project) | `<project>/.uipath-claude/skill-insights/` | Per-project |
| Skill insights (user) | `~/.cursor/skill-insights/` | Per-user |
| Tracked test PIDs | `~/.uipath-claude/tracked_processes.json` | `ProcessTracker(tracking_file=...)` |

Library content lives in the repo so it is versioned, browsable, and reproducible across machines. Everything else is machine-local user state.
```

- [ ] **Step 3: Verify the README renders**

Run:

```powershell
python -c "import pathlib; t = pathlib.Path('README.md').read_text(encoding='utf-8'); assert 'Runtime data locations' in t; print('OK')"
```

Expected output: `OK`.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(readme): document runtime data locations and overrides"
```

---

## Self-Review

**1. Spec coverage:**

| Spec item | Task |
|---|---|
| Default library path inside the repo | Task 1 |
| Env-var override preserved | Task 1 (test retained) |
| `_cache` removed from library folder | Task 2 + Task 3 |
| Cache has its own override path | Task 2 |
| Seed script doesn't pollute committable content | Task 3 |
| CI / alt-location seed support | Task 4 |
| Existing library content moved into repo | Task 5 |
| Defensive gitignore | Task 6 |
| Documentation | Task 7 |

All covered.

**2. Placeholder scan:** no TBD/TODO; every code step has complete code; every command has a concrete expected output.

**3. Type consistency:**
- `get_library_path()` / `_default_library_path()` — consistent across Tasks 1 and 2.
- `LibraryReader.__init__(catalog, cache_path=None)` — consistent across Task 2 tests and source.
- `LIBRARY_CACHE_ENV_VAR` constant — declared in `reader.py`, imported in `test_reader.py`.
- `create_library_structure(target: Path | None = None)` — consistent between Task 4 test and source.
- `parents[3]` used for repo root in test files at depth 3 (`tests/unit/library/...` and `tests/unit/scripts/...` and `tests/unit/meta/...`). All match.

Plan ready.
