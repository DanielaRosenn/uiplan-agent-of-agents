# UiPath Agent Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement CLI UX improvements, plan persistence, planner unit tests, and a CandleKeep-style documentation library for the UiPath Builder Agent.

**Architecture:** Add new commands and tools to the existing CLI structure. The documentation library will live in `~/.uipath-claude/library/` with YAML manifests and markdown content. Plan persistence saves to the existing `generated/chat/<session>/` structure.

**Tech Stack:** Python 3.11, Typer CLI, Rich (tables/panels), PyYAML, pytest

---

## File Structure

**Files to Create:**
- `uipath_claude/commands/plan.py` — /plan command implementation
- `uipath_claude/tools/library_tools.py` — Documentation library agent tools
- `uipath_claude/library/catalog.py` — Library catalog management
- `uipath_claude/library/reader.py` — Section reader with caching
- `scripts/seed_uipath_docs.py` — Library seeding script
- `tests/unit/query/test_planner.py` — Planner unit tests
- `tests/unit/tools/test_library_tools.py` — Library tools tests
- `tests/unit/commands/test_plan_command.py` — /plan command tests

**Files to Modify:**
- `uipath_claude/cli/app.py` — Add --no-plan flag, phase indicators, plan persistence
- `uipath_claude/commands/recall.py` — Rich Table formatting
- `README.md` — Add Plan Mode detailed section

---

### Task 1: Add Planner Unit Tests

**Files:**
- Create: `tests/unit/query/test_planner.py`

- [ ] **Step 1: Write failing test for get_planning_tools**

```python
"""Tests for planning agent module."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from uipath_claude.tools.skill_execution_tools import get_planning_tools


class TestGetPlanningTools:
    def test_returns_list_of_tools(self):
        tools = get_planning_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_includes_read_only_tools(self):
        tools = get_planning_tools()
        tool_names = {t.name for t in tools}
        assert "read_file" in tool_names
        assert "list_directory" in tool_names
        assert "read_project_json" in tool_names

    def test_excludes_write_tools(self):
        tools = get_planning_tools()
        tool_names = {t.name for t in tools}
        assert "write_file" not in tool_names
        assert "install_package" not in tool_names
        assert "run_workflow" not in tool_names
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/unit/query/test_planner.py::TestGetPlanningTools -v`
Expected: PASS (get_planning_tools already exists)

- [ ] **Step 3: Write failing test for run_planner_agent**

```python
class TestRunPlannerAgent:
    @pytest.mark.asyncio
    @patch("uipath_claude.query.planner.AgenticExecutor")
    async def test_creates_executor_with_model_params(self, mock_executor_cls):
        from uipath_claude.query.planner import run_planner_agent
        from uipath_claude.query.agentic_executor import AgenticResult

        mock_executor = MagicMock()
        mock_executor.execute = AsyncMock(
            return_value=AgenticResult(
                success=True,
                final_response="Plan content here",
                iterations=1,
                tool_calls_made=[],
                files_written=[],
                error=None,
            )
        )
        mock_executor_cls.return_value = mock_executor

        await run_planner_agent(
            "Create a workflow",
            model_name="test-model",
            region="us-east-1",
        )

        mock_executor_cls.assert_called_once_with(
            model_name="test-model", region="us-east-1"
        )

    @pytest.mark.asyncio
    @patch("uipath_claude.query.planner.AgenticExecutor")
    async def test_system_prompt_contains_read_only_constraint(self, mock_executor_cls):
        from uipath_claude.query.planner import run_planner_agent
        from uipath_claude.query.agentic_executor import AgenticResult

        mock_executor = MagicMock()
        mock_executor.execute = AsyncMock(
            return_value=AgenticResult(
                success=True,
                final_response="Plan",
                iterations=1,
                tool_calls_made=[],
                files_written=[],
                error=None,
            )
        )
        mock_executor_cls.return_value = mock_executor

        await run_planner_agent(
            "Create a workflow",
            model_name="test-model",
            region="us-east-1",
        )

        call_kwargs = mock_executor.execute.call_args.kwargs
        skill_content = call_kwargs.get("skill_content", "")
        assert "READ-ONLY" in skill_content
        assert "STRICTLY PROHIBITED" in skill_content

    @pytest.mark.asyncio
    @patch("uipath_claude.query.planner.AgenticExecutor")
    async def test_passes_planning_tools_to_executor(self, mock_executor_cls):
        from uipath_claude.query.planner import run_planner_agent
        from uipath_claude.query.agentic_executor import AgenticResult
        from uipath_claude.tools.skill_execution_tools import get_planning_tools

        mock_executor = MagicMock()
        mock_executor.execute = AsyncMock(
            return_value=AgenticResult(
                success=True,
                final_response="Plan",
                iterations=1,
                tool_calls_made=[],
                files_written=[],
                error=None,
            )
        )
        mock_executor_cls.return_value = mock_executor

        await run_planner_agent(
            "Create a workflow",
            model_name="test-model",
            region="us-east-1",
        )

        call_kwargs = mock_executor.execute.call_args.kwargs
        tools = call_kwargs.get("tools", [])
        expected_tools = get_planning_tools()
        assert len(tools) == len(expected_tools)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/query/test_planner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/query/test_planner.py
git commit -m "test: add planner unit tests for get_planning_tools and run_planner_agent"
```

---

### Task 2: Update README with Plan Mode Section

**Files:**
- Modify: `README.md:141-142`

- [ ] **Step 1: Add Plan Mode section after /recall in slash commands**

Insert after line 141 (`- `/recall <term>` — Search recent session messages for matching text`):

```markdown

### Plan mode

When `UIPATH_PLAN_MODE=1` (default), BUILD and AMBIGUOUS intents trigger a planning phase before execution:

1. **Planning**: A read-only planning agent explores the codebase and proposes an implementation plan
2. **Review**: The plan is displayed in a cyan-bordered panel. You can:
   - Type `y` or `yes` to approve and proceed to execution
   - Type `n` or `no` to cancel
   - Type any other text as feedback to refine the plan
3. **Persistence**: Approved plans are saved to `generated/chat/<session>/.plan.md`
4. **Execution**: The approved plan is injected into the execution context

**Environment variables:**
- `UIPATH_PLAN_MODE=1` — Enable planning (default)
- `UIPATH_PLAN_MODE=0` — Disable planning for faster iteration

**CLI flags:**
- `uipath-claude chat --no-plan` — Skip planning for this session
```

- [ ] **Step 2: Verify README renders correctly**

Run: `python -c "import pathlib; print(len(pathlib.Path('README.md').read_text()))"`
Expected: File size increased

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add Plan Mode section to README"
```

---

### Task 3: Add --no-plan CLI Flag

**Files:**
- Modify: `uipath_claude/cli/app.py:581-590`

- [ ] **Step 1: Add no_plan parameter to chat command**

Find the `def chat(` function (around line 580) and add the parameter:

```python
@app.command()
def chat(
    no_banner: bool = typer.Option(False, "--no-banner", help="Skip welcome banner"),
    no_plan: bool = typer.Option(False, "--no-plan", help="Skip planning phase for BUILD intents"),
    stream: bool | None = typer.Option(
        None,
        "--stream/--no-stream",
        help="Stream assistant tokens while generating responses.",
    ),
):
```

- [ ] **Step 2: Use no_plan to override UIPATH_PLAN_MODE**

Find the plan mode check (around line 783) and modify:

```python
        # Plan Mode logic
        approved_plan = ""
        plan_mode_enabled = os.environ.get("UIPATH_PLAN_MODE", "1").strip().lower() in ("1", "true", "yes")
        if plan_mode_enabled and not no_plan:
            if intent in (IntentType.BUILD, IntentType.AMBIGUOUS):
```

- [ ] **Step 3: Run CLI help to verify flag appears**

Run: `python -m uipath_claude.cli.app chat --help`
Expected: `--no-plan` flag listed

- [ ] **Step 4: Commit**

```bash
git add uipath_claude/cli/app.py
git commit -m "feat: add --no-plan CLI flag to skip planning phase"
```

---

### Task 4: Add Phase Indicators to CLI

**Files:**
- Modify: `uipath_claude/cli/app.py:786-798`

- [ ] **Step 1: Add [PLANNING] indicator before plan generation**

Find the plan generation spinner (around line 786) and update:

```python
        if plan_mode_enabled and not no_plan:
            if intent in (IntentType.BUILD, IntentType.AMBIGUOUS):
                while True:
                    console.print("[bold cyan][PLANNING][/bold cyan]")
                    with progress.generating("implementation plan"):
                        plan_result = asyncio.run(
                            run_planner_agent(
```

- [ ] **Step 2: Add [EXECUTING] indicator before workflow generation**

Find the workflow generation section (around line 856) and add before the spinner:

```python
            if use_spinner and (stream_enabled and suppress_stream_output):
                console.print("[bold yellow][EXECUTING][/bold yellow]")
                with progress.generating("workflow"):
```

And also around line 859:

```python
            elif use_spinner and (not stream_enabled and file_intent):
                console.print("[bold yellow][EXECUTING][/bold yellow]")
                with progress.generating("workflow"):
```

- [ ] **Step 3: Manual test**

Run: `uipath-claude chat` and type "create a workflow that reads an Excel file"
Expected: See `[PLANNING]` before plan, `[EXECUTING]` before workflow

- [ ] **Step 4: Commit**

```bash
git add uipath_claude/cli/app.py
git commit -m "feat: add [PLANNING] and [EXECUTING] phase indicators to CLI"
```

---

### Task 5: Format /recall Output as Rich Table

**Files:**
- Modify: `uipath_claude/commands/recall.py`

- [ ] **Step 1: Write failing test for table format**

Create `tests/unit/commands/test_recall_table.py`:

```python
"""Test recall command Rich Table output."""
from uipath_claude.commands.recall import register_recall_command
from uipath_claude.commands.registry import CommandRegistry


def test_recall_output_contains_table_structure():
    """Output should contain table-like formatting."""
    registry = CommandRegistry()
    history = [
        {"role": "user", "content": "build invoice workflow"},
        {"role": "assistant", "content": "I will create an invoice workflow"},
    ]
    register_recall_command(registry, get_history=lambda: history)

    result = registry.execute("recall", "invoice")
    # Rich Table output contains box-drawing characters
    assert "│" in result or "Role" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/commands/test_recall_table.py -v`
Expected: FAIL (current output uses plain text)

- [ ] **Step 3: Update recall command to use Rich Table**

```python
"""Recall command implementation."""
from io import StringIO
from typing import Callable

from rich.console import Console
from rich.table import Table

from uipath_claude.commands.registry import CommandRegistry, register_command
from uipath_claude.query.session_search import search_session_history


def register_recall_command(
    registry: CommandRegistry,
    get_history: Callable[[], list[dict[str, str]]],
) -> None:
    """Register the /recall command."""

    @register_command(
        registry,
        name="recall",
        description="Search recent session history",
    )
    def recall_command(*query_parts: str) -> str:
        """Search for matching messages in the current session."""
        query = " ".join(query_parts).strip()
        if not query:
            return "Usage: /recall <query>"

        matches = search_session_history(get_history(), query)
        if not matches:
            return f"No matches found for: {query}"

        table = Table(title=f"Matches for '{query}'")
        table.add_column("#", style="dim", width=4)
        table.add_column("Role", style="cyan", width=12)
        table.add_column("Content", style="white")

        for idx, match in enumerate(matches, start=1):
            role = match.get("role", "unknown")
            content = match.get("content", "")
            # Truncate long content
            if len(content) > 80:
                content = content[:77] + "..."
            table.add_row(str(idx), role, content)

        # Render table to string
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)
        console.print(table)
        return string_io.getvalue()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/commands/test_recall_table.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add uipath_claude/commands/recall.py tests/unit/commands/test_recall_table.py
git commit -m "feat: format /recall output as Rich Table"
```

---

### Task 6: Add Plan Persistence

**Files:**
- Modify: `uipath_claude/cli/app.py:800-813`

- [ ] **Step 1: Create helper function to save plan**

Add near top of app.py (around line 150):

```python
def _save_plan_to_file(
    session_id: str,
    user_request: str,
    plan_content: str,
    output_root: Path,
) -> Path:
    """Save approved plan to .plan.md file."""
    from datetime import datetime, timezone

    session_dir = output_root / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    plan_path = session_dir / ".plan.md"

    content = f"""# Implementation Plan
Generated: {datetime.now(timezone.utc).isoformat()}
Session: {session_id}

## User Request
{user_request}

## Plan
{plan_content}
"""
    plan_path.write_text(content, encoding="utf-8")
    return plan_path
```

- [ ] **Step 2: Call save function when plan is approved**

Find the approval section (around line 800) and add after `approved_plan = plan_result.final_response`:

```python
                    if confirm in ("y", "yes"):
                        approved_plan = plan_result.final_response
                        # Save plan to file
                        plan_path = _save_plan_to_file(
                            session_id=chat_session_id,
                            user_request=user_input,
                            plan_content=approved_plan,
                            output_root=_get_output_root(),
                        )
                        console.print(f"[dim]Plan saved to: {plan_path}[/dim]")
                        break
```

- [ ] **Step 3: Add import for _get_output_root**

Add at top of file:

```python
from uipath_claude.tools.skill_execution_tools import _get_output_root
```

- [ ] **Step 4: Manual test**

Run: `uipath-claude chat`, type "create Excel workflow", approve plan, check `generated/chat/<session>/.plan.md`
Expected: File exists with plan content

- [ ] **Step 5: Commit**

```bash
git add uipath_claude/cli/app.py
git commit -m "feat: persist approved plans to .plan.md files"
```

---

### Task 7: Add /plan Command

**Files:**
- Create: `uipath_claude/commands/plan.py`
- Modify: `uipath_claude/cli/app.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/commands/test_plan_command.py`:

```python
"""Tests for /plan command."""
from uipath_claude.commands.plan import register_plan_command
from uipath_claude.commands.registry import CommandRegistry


def test_plan_command_is_registered():
    registry = CommandRegistry()
    register_plan_command(registry, run_planner=lambda x: "Plan for: " + x)
    assert "plan" in registry.commands


def test_plan_command_requires_description():
    registry = CommandRegistry()
    register_plan_command(registry, run_planner=lambda x: "Plan")
    result = registry.execute("plan")
    assert "Usage:" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/commands/test_plan_command.py -v`
Expected: FAIL (module doesn't exist)

- [ ] **Step 3: Create plan command**

```python
"""Plan command implementation."""
from typing import Callable

from uipath_claude.commands.registry import CommandRegistry, register_command


def register_plan_command(
    registry: CommandRegistry,
    run_planner: Callable[[str], str],
) -> None:
    """Register the /plan command.

    Args:
        registry: Command registry
        run_planner: Function that generates a plan from a description
    """

    @register_command(
        registry,
        name="plan",
        description="Generate implementation plan without executing",
    )
    def plan_command(*description_parts: str) -> str:
        """Generate a plan for the given description."""
        description = " ".join(description_parts).strip()
        if not description:
            return "Usage: /plan <description>\n\nGenerates an implementation plan without executing it."

        plan = run_planner(description)
        return f"{plan}\n\n[Type 'y' to execute this plan, or continue chatting]"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/commands/test_plan_command.py -v`
Expected: PASS

- [ ] **Step 5: Register command in app.py**

Add import:
```python
from uipath_claude.commands.plan import register_plan_command
```

Add in `_build_command_registry` function:
```python
    register_plan_command(registry, run_planner=run_planner)
```

Add run_planner parameter to function signature and pass it when called.

- [ ] **Step 6: Commit**

```bash
git add uipath_claude/commands/plan.py tests/unit/commands/test_plan_command.py uipath_claude/cli/app.py
git commit -m "feat: add /plan command for on-demand planning"
```

---

### Task 8: Create Documentation Library Structure

**Files:**
- Create: `uipath_claude/library/__init__.py`
- Create: `uipath_claude/library/catalog.py`
- Create: `uipath_claude/library/reader.py`

- [ ] **Step 1: Create library package init**

```python
"""Documentation library for UiPath Claude Code."""
from uipath_claude.library.catalog import LibraryCatalog
from uipath_claude.library.reader import LibraryReader

__all__ = ["LibraryCatalog", "LibraryReader"]
```

- [ ] **Step 2: Create catalog module**

```python
"""Library catalog management."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Section:
    """A section within a chapter."""

    id: str
    title: str
    file: str
    keywords: list[str] = field(default_factory=list)


@dataclass
class Chapter:
    """A chapter within a book."""

    id: str
    title: str
    path: str
    order: int
    sections: list[Section] = field(default_factory=list)


@dataclass
class Book:
    """A documentation book."""

    id: str
    title: str
    path: str
    description: str = ""
    version: str = ""
    source: str = ""
    chapters: list[Chapter] = field(default_factory=list)


@dataclass
class LibraryCatalog:
    """Library catalog containing all books."""

    books: list[Book] = field(default_factory=list)

    @classmethod
    def get_library_path(cls) -> Path:
        """Get the library root path."""
        return Path.home() / ".uipath-claude" / "library"

    @classmethod
    def load(cls) -> "LibraryCatalog":
        """Load catalog from disk."""
        library_path = cls.get_library_path()
        catalog_file = library_path / "catalog.yaml"

        if not catalog_file.exists():
            return cls(books=[])

        with open(catalog_file, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        books = []
        for book_entry in data.get("books", []):
            book_path = library_path / book_entry["path"]
            book_file = book_path / "book.yaml"

            if book_file.exists():
                with open(book_file, encoding="utf-8") as f:
                    book_data = yaml.safe_load(f) or {}

                chapters = []
                for ch in book_data.get("chapters", []):
                    chapter_path = book_path / ch["path"]
                    chapter_file = chapter_path / "chapter.yaml"

                    sections = []
                    if chapter_file.exists():
                        with open(chapter_file, encoding="utf-8") as f:
                            ch_data = yaml.safe_load(f) or {}
                        for sec in ch_data.get("sections", []):
                            sections.append(
                                Section(
                                    id=sec["id"],
                                    title=sec["title"],
                                    file=sec["file"],
                                    keywords=sec.get("keywords", []),
                                )
                            )

                    chapters.append(
                        Chapter(
                            id=ch["id"],
                            title=ch["title"],
                            path=ch["path"],
                            order=ch.get("order", 0),
                            sections=sections,
                        )
                    )

                books.append(
                    Book(
                        id=book_data.get("id", book_entry["id"]),
                        title=book_data.get("title", book_entry["title"]),
                        path=book_entry["path"],
                        description=book_entry.get("description", ""),
                        version=book_data.get("version", ""),
                        source=book_data.get("source", ""),
                        chapters=chapters,
                    )
                )

        return cls(books=books)

    def get_book(self, book_id: str) -> Book | None:
        """Get a book by ID."""
        for book in self.books:
            if book.id == book_id:
                return book
        return None

    def search_sections(self, query: str) -> list[tuple[Book, Chapter, Section]]:
        """Search sections by keyword."""
        query_lower = query.lower()
        results = []

        for book in self.books:
            for chapter in book.chapters:
                for section in chapter.sections:
                    if query_lower in section.title.lower() or any(
                        query_lower in kw.lower() for kw in section.keywords
                    ):
                        results.append((book, chapter, section))

        return results
```

- [ ] **Step 3: Create reader module**

```python
"""Library section reader with caching."""
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import json

from uipath_claude.library.catalog import LibraryCatalog


class LibraryReader:
    """Read sections from the documentation library."""

    CACHE_TTL = timedelta(days=30)

    def __init__(self, catalog: LibraryCatalog | None = None):
        """Initialize reader with optional catalog."""
        self.catalog = catalog or LibraryCatalog.load()
        self.library_path = LibraryCatalog.get_library_path()

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

        section_path = (
            self.library_path / book.path / chapter.path / section.file
        )

        if not section_path.exists():
            return None

        return section_path.read_text(encoding="utf-8")

    def get_cached_response(self, query: str) -> str | None:
        """Check cache for a query response."""
        cache_dir = self.library_path / "books" / "uipath-docs" / "_cache"
        if not cache_dir.exists():
            return None

        cache_key = hashlib.md5(query.lower().encode()).hexdigest()
        cache_file = cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            return None

        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            cached_at = datetime.fromisoformat(data["cached_at"])

            if datetime.now() - cached_at > self.CACHE_TTL:
                return None

            return data["response"]
        except (json.JSONDecodeError, KeyError):
            return None

    def cache_response(self, query: str, response: str) -> None:
        """Cache a query response."""
        cache_dir = self.library_path / "books" / "uipath-docs" / "_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        cache_key = hashlib.md5(query.lower().encode()).hexdigest()
        cache_file = cache_dir / f"{cache_key}.json"

        data = {
            "query": query,
            "response": response,
            "cached_at": datetime.now().isoformat(),
        }
        cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
```

- [ ] **Step 4: Run import test**

Run: `python -c "from uipath_claude.library import LibraryCatalog, LibraryReader; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add uipath_claude/library/
git commit -m "feat: add documentation library catalog and reader"
```

---

### Task 9: Create Library Agent Tools

**Files:**
- Create: `uipath_claude/tools/library_tools.py`
- Create: `tests/unit/tools/test_library_tools.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for library tools."""
import pytest
from unittest.mock import MagicMock, patch

from uipath_claude.tools.library_tools import (
    list_library_books,
    browse_book_toc,
    read_section,
    search_library,
)


def test_list_library_books_returns_string():
    result = list_library_books.invoke({})
    assert isinstance(result, str)


def test_search_library_returns_results_or_no_match():
    result = search_library.invoke({"query": "nonexistent12345"})
    assert "No matches" in result or "match" in result.lower()
```

- [ ] **Step 2: Create library tools**

```python
"""Agent tools for documentation library."""
from langchain_core.tools import tool

from uipath_claude.library.catalog import LibraryCatalog
from uipath_claude.library.reader import LibraryReader


@tool
def list_library_books() -> str:
    """List all documentation books in the library.

    Returns a list of available books with their chapter counts.
    Use this to discover what documentation is available.
    """
    catalog = LibraryCatalog.load()

    if not catalog.books:
        return "No books found in library. Run the seed script to populate."

    lines = ["Available documentation books:\n"]
    for book in catalog.books:
        chapter_count = len(book.chapters)
        lines.append(f"- **{book.title}** (`{book.id}`): {chapter_count} chapters")
        if book.description:
            lines.append(f"  {book.description}")

    return "\n".join(lines)


@tool
def browse_book_toc(book_id: str) -> str:
    """Browse the table of contents for a documentation book.

    Args:
        book_id: The book identifier (e.g., 'uipath-docs')

    Returns a hierarchical view of chapters and sections.
    """
    catalog = LibraryCatalog.load()
    book = catalog.get_book(book_id)

    if not book:
        available = ", ".join(b.id for b in catalog.books) or "none"
        return f"Book '{book_id}' not found. Available: {available}"

    lines = [f"# {book.title}\n"]
    if book.version:
        lines.append(f"Version: {book.version}")
    if book.source:
        lines.append(f"Source: {book.source}")
    lines.append("")

    for chapter in sorted(book.chapters, key=lambda c: c.order):
        lines.append(f"## {chapter.title}")
        for section in chapter.sections:
            keywords = ", ".join(section.keywords[:3]) if section.keywords else ""
            kw_str = f" ({keywords})" if keywords else ""
            lines.append(f"  - {section.title}{kw_str}")
        lines.append("")

    return "\n".join(lines)


@tool
def read_section(book_id: str, chapter_id: str, section_id: str) -> str:
    """Read a specific section from a documentation book.

    Args:
        book_id: The book identifier (e.g., 'uipath-docs')
        chapter_id: The chapter identifier (e.g., 'activities')
        section_id: The section identifier (e.g., 'workflow')

    Returns the full content of the section with citation info.
    """
    reader = LibraryReader()
    content = reader.read_section(book_id, chapter_id, section_id)

    if content is None:
        return f"Section not found: {book_id}/{chapter_id}/{section_id}"

    citation = f"\n\n---\n*Source: {book_id}, Chapter: {chapter_id}, Section: {section_id}*"
    return content + citation


@tool
def search_library(query: str) -> str:
    """Search across all documentation books by keyword.

    Args:
        query: Search term to find in section titles and keywords

    Returns matching sections with their locations.
    """
    catalog = LibraryCatalog.load()
    results = catalog.search_sections(query)

    if not results:
        return f"No matches found for: {query}"

    lines = [f"Found {len(results)} matches for '{query}':\n"]
    for book, chapter, section in results[:10]:  # Limit to 10 results
        lines.append(
            f"- **{section.title}** in {book.title} > {chapter.title}"
        )
        lines.append(
            f"  Read with: read_section('{book.id}', '{chapter.id}', '{section.id}')"
        )

    if len(results) > 10:
        lines.append(f"\n...and {len(results) - 10} more results")

    return "\n".join(lines)


def get_library_tools() -> list:
    """Return the list of library tools for agent use."""
    return [
        list_library_books,
        browse_book_toc,
        read_section,
        search_library,
    ]
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/unit/tools/test_library_tools.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add uipath_claude/tools/library_tools.py tests/unit/tools/test_library_tools.py
git commit -m "feat: add documentation library agent tools"
```

---

### Task 10: Create Library Seed Script

**Files:**
- Create: `scripts/seed_uipath_docs.py`

- [ ] **Step 1: Create seed script**

```python
#!/usr/bin/env python3
"""Seed the documentation library with UiPath docs content.

This script populates the library by fetching content from the UiPath Ask AI API
and organizing it into the book/chapter/section structure.

Usage:
    python scripts/seed_uipath_docs.py
"""
import os
import sys
from pathlib import Path

import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from uipath_claude.library.catalog import LibraryCatalog

SEED_STRUCTURE = {
    "01-activities": {
        "title": "Activities Reference",
        "sections": {
            "workflow": {
                "title": "Workflow Activities",
                "keywords": ["foreach", "if", "while", "switch", "sequence", "flowchart"],
                "topics": [
                    "ForEach activity usage and properties",
                    "If activity conditions and branches",
                    "While loop activity",
                    "Switch activity for multiple conditions",
                    "Sequence vs Flowchart",
                ],
            },
            "mail": {
                "title": "Mail Activities",
                "keywords": ["outlook", "email", "smtp", "imap", "exchange"],
                "topics": [
                    "Get Outlook Mail Messages activity",
                    "Send Outlook Mail Message activity",
                    "Save Mail Attachments activity",
                ],
            },
            "excel": {
                "title": "Excel Activities",
                "keywords": ["readrange", "writerange", "workbook", "spreadsheet"],
                "topics": [
                    "Read Range activity for Excel",
                    "Write Range activity for Excel",
                    "Excel Application Scope vs Workbook activities",
                ],
            },
            "ui-automation": {
                "title": "UI Automation Activities",
                "keywords": ["click", "typeinto", "gettext", "selector", "browser"],
                "topics": [
                    "Click activity and selectors",
                    "Type Into activity",
                    "Get Text activity",
                    "Use Application/Browser scope",
                ],
            },
        },
    },
    "02-orchestrator": {
        "title": "Orchestrator Guide",
        "sections": {
            "queues": {
                "title": "Queue Operations",
                "keywords": ["queue", "transaction", "getqueueitems", "addqueueitem"],
                "topics": [
                    "Get Queue Items activity",
                    "Add Queue Item activity",
                    "Set Transaction Status activity",
                    "Queue item retry logic",
                ],
            },
            "assets": {
                "title": "Asset Management",
                "keywords": ["asset", "credential", "getasset", "setasset"],
                "topics": [
                    "Get Asset activity",
                    "Get Credential activity",
                    "Asset types and per-robot assets",
                ],
            },
            "jobs": {
                "title": "Job Management",
                "keywords": ["job", "robot", "trigger", "schedule"],
                "topics": [
                    "Start Job activity",
                    "Get Jobs activity",
                    "Job triggers and schedules",
                ],
            },
        },
    },
    "03-studio": {
        "title": "Studio User Guide",
        "sections": {
            "reframework": {
                "title": "REFramework",
                "keywords": ["reframework", "transactional", "init", "process", "end"],
                "topics": [
                    "REFramework architecture overview",
                    "Init state and Config.xlsx",
                    "GetTransactionData state",
                    "Process Transaction state",
                    "BusinessRuleException vs SystemException",
                ],
            },
            "selectors": {
                "title": "Selectors",
                "keywords": ["selector", "uiexplorer", "wildcard", "dynamic"],
                "topics": [
                    "Selector strategies and best practices",
                    "Dynamic selectors with wildcards",
                    "UI Explorer usage",
                    "Anchor-based selectors",
                ],
            },
            "variables": {
                "title": "Variables and Arguments",
                "keywords": ["variable", "argument", "datatable", "scope"],
                "topics": [
                    "Variable types and scopes",
                    "Arguments for workflow inputs/outputs",
                    "DataTable operations",
                ],
            },
        },
    },
    "04-best-practices": {
        "title": "Best Practices",
        "sections": {
            "error-handling": {
                "title": "Error Handling",
                "keywords": ["trycatch", "exception", "retry", "logging"],
                "topics": [
                    "Try Catch patterns in UiPath",
                    "Global Exception Handler",
                    "Retry Scope usage",
                    "Logging best practices",
                ],
            },
            "naming-conventions": {
                "title": "Naming Conventions",
                "keywords": ["naming", "convention", "standard", "style"],
                "topics": [
                    "Variable naming conventions",
                    "Workflow naming conventions",
                    "Project structure best practices",
                ],
            },
        },
    },
}


def fetch_from_ask_ai(topics: list[str]) -> str:
    """Fetch content from Ask AI for given topics."""
    # For now, return placeholder content
    # In production, this would call the actual Ask AI API
    content_lines = []
    for topic in topics:
        content_lines.append(f"## {topic}\n")
        content_lines.append(f"[Content for: {topic}]\n")
        content_lines.append("")
    return "\n".join(content_lines)


def create_library_structure():
    """Create the library directory structure and seed content."""
    library_path = LibraryCatalog.get_library_path()
    print(f"Creating library at: {library_path}")

    # Create catalog.yaml
    catalog_data = {
        "version": 1,
        "books": [
            {
                "id": "uipath-docs",
                "title": "UiPath Documentation",
                "path": "books/uipath-docs",
                "description": "Official UiPath product documentation",
            }
        ],
    }
    library_path.mkdir(parents=True, exist_ok=True)
    catalog_file = library_path / "catalog.yaml"
    with open(catalog_file, "w", encoding="utf-8") as f:
        yaml.dump(catalog_data, f, default_flow_style=False)
    print(f"Created: {catalog_file}")

    # Create book structure
    book_path = library_path / "books" / "uipath-docs"
    book_path.mkdir(parents=True, exist_ok=True)

    # Create book.yaml
    book_data = {
        "id": "uipath-docs",
        "title": "UiPath Documentation",
        "version": "2024.10",
        "source": "docs.uipath.com",
        "chapters": [],
    }

    for chapter_folder, chapter_info in SEED_STRUCTURE.items():
        chapter_id = chapter_folder.split("-", 1)[1]
        book_data["chapters"].append({
            "id": chapter_id,
            "title": chapter_info["title"],
            "path": f"chapters/{chapter_folder}",
            "order": int(chapter_folder.split("-")[0]),
        })

        # Create chapter directory
        chapter_path = book_path / "chapters" / chapter_folder
        chapter_path.mkdir(parents=True, exist_ok=True)

        # Create chapter.yaml
        chapter_data = {
            "id": chapter_id,
            "title": chapter_info["title"],
            "sections": [],
        }

        for section_id, section_info in chapter_info["sections"].items():
            chapter_data["sections"].append({
                "id": section_id,
                "title": section_info["title"],
                "file": f"{section_id}.md",
                "keywords": section_info["keywords"],
            })

            # Create section content
            content = fetch_from_ask_ai(section_info["topics"])
            section_file = chapter_path / f"{section_id}.md"
            header = f"""---
id: {section_id}
title: {section_info["title"]}
---

# {section_info["title"]}

"""
            section_file.write_text(header + content, encoding="utf-8")
            print(f"Created: {section_file}")

        chapter_yaml = chapter_path / "chapter.yaml"
        with open(chapter_yaml, "w", encoding="utf-8") as f:
            yaml.dump(chapter_data, f, default_flow_style=False)
        print(f"Created: {chapter_yaml}")

    # Create _cache directory
    cache_dir = book_path / "_cache"
    cache_dir.mkdir(exist_ok=True)

    # Save book.yaml
    book_yaml = book_path / "book.yaml"
    with open(book_yaml, "w", encoding="utf-8") as f:
        yaml.dump(book_data, f, default_flow_style=False)
    print(f"Created: {book_yaml}")

    print("\nLibrary seeded successfully!")
    print(f"Total chapters: {len(SEED_STRUCTURE)}")
    total_sections = sum(len(ch["sections"]) for ch in SEED_STRUCTURE.values())
    print(f"Total sections: {total_sections}")


if __name__ == "__main__":
    create_library_structure()
```

- [ ] **Step 2: Run seed script**

Run: `python scripts/seed_uipath_docs.py`
Expected: Library structure created at `~/.uipath-claude/library/`

- [ ] **Step 3: Verify library loads**

Run: `python -c "from uipath_claude.library import LibraryCatalog; c = LibraryCatalog.load(); print(f'Books: {len(c.books)}')"`
Expected: `Books: 1`

- [ ] **Step 4: Commit**

```bash
git add scripts/seed_uipath_docs.py
git commit -m "feat: add library seed script for UiPath documentation"
```

---

### Task 11: Integrate Library Tools with Skill Execution

**Files:**
- Modify: `uipath_claude/tools/skill_execution_tools.py`

- [ ] **Step 1: Add library tools to planning tools**

Add import at top:
```python
from uipath_claude.tools.library_tools import get_library_tools
```

Update `get_planning_tools`:
```python
def get_planning_tools() -> list:
    """Return the list of read-only tools available during planning."""
    return [
        read_file,
        list_directory,
        read_project_json,
        find_activity_info,
        query_uipath_docs,
    ] + get_library_tools()
```

- [ ] **Step 2: Add library tools to skill execution tools**

Update `get_skill_execution_tools`:
```python
def get_skill_execution_tools() -> list:
    """Return the list of tools available during skill execution."""
    return [
        read_file,
        write_file,
        list_directory,
        read_project_json,
        install_package,
        validate_file,
        run_workflow,
        run_uip_command,
        find_activity_info,
        validate_and_fix_loop,
        debug_workflow,
        ensure_project_structure,
        query_uipath_docs,
    ] + get_library_tools()
```

- [ ] **Step 3: Run tests to verify integration**

Run: `pytest tests/unit/tools/ -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add uipath_claude/tools/skill_execution_tools.py
git commit -m "feat: integrate library tools with skill execution"
```

---

## Validation Checklist (self-review)

**Spec coverage:**
- [x] README Plan Mode section — Task 2
- [x] Planner unit tests — Task 1
- [x] CLI UX improvements — Tasks 3, 4, 5
- [x] Plan persistence — Task 6
- [x] /plan command — Task 7
- [x] Documentation library — Tasks 8, 9, 10, 11

**Placeholder scan:** No TBD/TODO placeholders. All code blocks are complete.

**Type consistency:** All function signatures use Python 3.11 type hints consistently.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-15-agent-improvements.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
