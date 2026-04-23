"""In-process MCP integration test that walks the 9 Cursor smoke steps in
``docs/SMOKE_TESTS.md`` (Cursor MCP block, lines ~168-217).

For each step we invoke the tool the smoke doc names, with the literal prompt
arguments, and assert the returned text has the shape Cursor would need to
chain to the next step.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from mcp_server.tools.doc_tools import call_doc_tool, get_doc_tools
from mcp_server.tools.library_tools import call_library_tool, get_library_tools
from uipath_claude.library.catalog import LIBRARY_PATH_ENV_VAR
from uipath_claude.library.proposals import PROPOSALS_ENV_VAR, ProposalStore


def _seed_library(root: Path) -> None:
    """Build a small but realistic uipath-docs book with an Orchestrator
    chapter so the smoke 'orchestrator schedule' query has something to find."""
    lib = root / "library"
    book_dir = lib / "books" / "uipath-docs"
    orch_dir = book_dir / "chapters" / "02-orchestrator"
    act_dir = book_dir / "chapters" / "01-activities"
    orch_dir.mkdir(parents=True)
    act_dir.mkdir(parents=True)

    (lib / "catalog.yaml").write_text(
        yaml.dump(
            {
                "books": [
                    {
                        "id": "uipath-docs",
                        "path": "books/uipath-docs",
                        "title": "UiPath Documentation",
                        "description": "Official UiPath product documentation",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (book_dir / "MANIFEST.yaml").write_text(
        yaml.dump(
            {
                "audience": "agent",
                "curator": "uipath-builder-agent",
                "license": "CC-BY-4.0",
            }
        ),
        encoding="utf-8",
    )
    (book_dir / "book.yaml").write_text(
        yaml.dump(
            {
                "id": "uipath-docs",
                "title": "UiPath Documentation",
                "version": "2024.10",
                "source": "docs.uipath.com",
                "chapters": [
                    {
                        "id": "activities",
                        "title": "Activities Reference",
                        "path": "chapters/01-activities",
                        "order": 1,
                    },
                    {
                        "id": "orchestrator",
                        "title": "Orchestrator Guide",
                        "path": "chapters/02-orchestrator",
                        "order": 2,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (act_dir / "chapter.yaml").write_text(
        yaml.dump(
            {
                "id": "activities",
                "sections": [
                    {
                        "id": "workflow",
                        "title": "Workflow Activities",
                        "file": "workflow.md",
                        "keywords": ["foreach", "if", "while"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (act_dir / "workflow.md").write_text("# Workflow Activities\n", encoding="utf-8")
    (orch_dir / "chapter.yaml").write_text(
        yaml.dump(
            {
                "id": "orchestrator",
                "sections": [
                    {
                        "id": "jobs",
                        "title": "Job Management",
                        "file": "jobs.md",
                        "keywords": ["job", "schedule", "trigger", "robot"],
                    },
                    {
                        "id": "queues",
                        "title": "Queue Operations",
                        "file": "queues.md",
                        "keywords": ["queue", "transaction"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (orch_dir / "jobs.md").write_text(
        "# Job Management\n\nUse a Time Trigger to schedule a job in Orchestrator.\n",
        encoding="utf-8",
    )
    (orch_dir / "queues.md").write_text("# Queue Operations\n", encoding="utf-8")


@pytest.fixture
def seeded_env(tmp_path, monkeypatch):
    _seed_library(tmp_path)
    monkeypatch.setenv(LIBRARY_PATH_ENV_VAR, str(tmp_path / "library"))
    monkeypatch.setenv(PROPOSALS_ENV_VAR, str(tmp_path / "props"))
    return tmp_path


def test_smoke_step_1_list_books(seeded_env):
    """Step 1: 'List all UiPath library books with their manifests.'"""
    out = pytest.importorskip("asyncio").run(
        call_library_tool("uipath_library_list", {})
    )
    assert "uipath-docs" in out
    assert "UiPath Documentation" in out
    assert "audience=agent" in out


def test_smoke_step_2_toc(seeded_env):
    """Step 2: 'Show the table of contents for the uipath-docs book.'"""
    import asyncio

    out = asyncio.run(
        call_library_tool("uipath_library_toc", {"book_id": "uipath-docs"})
    )
    assert "Orchestrator Guide" in out
    assert "Job Management" in out
    assert "Activities Reference" in out


def test_smoke_step_3_search_orchestrator_schedule_top_3(seeded_env):
    """Step 3: 'Search for "orchestrator schedule" and show the top 3 sections.'

    This is the regression that motivated the entire fix: must NOT return
    'No matches' for the literal phrase.
    """
    import asyncio

    out = asyncio.run(
        call_library_tool(
            "uipath_library_search",
            {"query": "orchestrator schedule", "top_n": 3},
        )
    )
    assert "No matches" not in out
    assert "id: uipath-docs/orchestrator/jobs" in out
    listed = [line for line in out.splitlines() if line.startswith("- **")]
    assert 1 <= len(listed) <= 3


def test_smoke_step_4_read_section_uses_id_from_step_3(seeded_env):
    """Step 4: 'Read section <paste id from step 3>.'"""
    import asyncio

    out = asyncio.run(
        call_library_tool(
            "uipath_library_read_section",
            {
                "book_id": "uipath-docs",
                "chapter_id": "orchestrator",
                "section_id": "jobs",
            },
        )
    )
    assert "Job Management" in out
    assert "Source: uipath-docs" in out


def test_smoke_step_5_full_lookup_emits_source_line(seeded_env, monkeypatch):
    """Step 5: lookup must always end with a SOURCE: line."""
    import asyncio

    from uipath_claude.tools._result import ToolOutcome

    monkeypatch.setattr(
        "uipath_claude.tools.knowledge_tools.query_uipath_documentation",
        lambda q: ToolOutcome(False, "ask offline"),
    )
    monkeypatch.delenv("UIPATH_WEB_SEARCH_ENABLED", raising=False)

    out = asyncio.run(
        call_library_tool(
            "uipath_library_lookup",
            {
                "question": "how do I schedule a job in orchestrator",
                "allow_network": False,
            },
        )
    )
    assert "SOURCE:" in out


def test_smoke_step_6_propose_chapter(seeded_env):
    """Step 6: propose_chapter is exposed and round-trips through list."""
    import asyncio

    out = asyncio.run(
        call_library_tool(
            "uipath_library_propose_chapter",
            {
                "book_id": "uipath-docs",
                "chapter_id": "patterns",
                "chapter_title": "Patterns",
                "rationale": "smoke test",
                "initial_sections_json": (
                    '[{"id": "retry-loops", "title": "Retry loops", '
                    '"content": "# Retry loops\\n", "keywords": ["retry"]}]'
                ),
            },
        )
    )
    assert "proposal_id" in out

    listed = asyncio.run(
        call_library_tool("uipath_library_list_proposals", {})
    )
    assert "patterns" in listed
    assert "new_chapter" in listed


def test_smoke_step_7_approve_proposal(seeded_env):
    """Step 7: approving a proposal writes files under data/library/."""
    import asyncio

    asyncio.run(
        call_library_tool(
            "uipath_library_propose_chapter",
            {
                "book_id": "uipath-docs",
                "chapter_id": "patterns",
                "chapter_title": "Patterns",
            },
        )
    )
    pid = ProposalStore().list_pending()[0].proposal_id

    out = asyncio.run(
        call_library_tool(
            "uipath_library_approve_proposal", {"proposal_id": pid}
        )
    )
    assert "Applied" in out or "applied" in out.lower()
    chapters_root = seeded_env / "library" / "books" / "uipath-docs" / "chapters"
    created = list(chapters_root.glob("*-patterns"))
    assert created, f"no patterns chapter under {chapters_root}"
    assert (created[0] / "chapter.yaml").exists()


def test_smoke_step_8_reject_proposal(seeded_env):
    """Step 8: rejecting a proposal removes it from the queue."""
    import asyncio

    asyncio.run(
        call_library_tool(
            "uipath_library_propose_section",
            {
                "book_id": "uipath-docs",
                "chapter_id": "orchestrator",
                "section_id": "throwaway",
                "section_title": "Throwaway",
                "content": "# Throwaway\n",
                "keywords": ["throwaway"],
            },
        )
    )
    pid = ProposalStore().list_pending()[0].proposal_id

    asyncio.run(
        call_library_tool(
            "uipath_library_reject_proposal", {"proposal_id": pid}
        )
    )
    assert ProposalStore().get(pid) is None


def test_smoke_step_9_query_uipath_docs_tool_exposed():
    """Step 9: the unified Ask AI tool is exposed under the documented name."""
    names = {t.name for t in get_doc_tools()}
    assert "query_uipath_docs" in names
    assert "uipath_doc_query" in names


def test_all_library_tool_descriptions_picker_friendly():
    for tool in get_library_tools():
        assert len(tool.description) >= 60
        assert "uipath" in tool.description.lower()
