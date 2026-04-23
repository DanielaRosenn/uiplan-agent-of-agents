"""Test that the new package structure exists."""
import importlib.util
from pathlib import Path


def test_root_package_exists():
    """Test that uipath_claude package exists."""
    spec = importlib.util.find_spec("uipath_claude")
    assert spec is not None, "uipath_claude package not found"


def test_subpackages_exist():
    """Test that all required subpackages exist."""
    subpackages = [
        "query",
        "agents",
        "artifacts",
        "tools",
        "tools.uipath",
        "skills",
        "commands",
        "context",
        "memory",
        "hooks",
        "rendering",
        "cli",
    ]
    
    for subpkg in subpackages:
        spec = importlib.util.find_spec(f"uipath_claude.{subpkg}")
        assert spec is not None, f"uipath_claude.{subpkg} package not found"


def test_legacy_agent_package_migration_is_repo_local():
    """Use repo-local checks to avoid environment-dependent import resolution."""
    repo_root = Path(__file__).resolve().parents[3]
    assert (repo_root / "framework" / "uipath_claude" / "agents").is_dir(), (
        "Expected migrated agent package under framework/uipath_claude/agents"
    )


def test_architecture_doc_mentions_runtime_controls_and_recall():
    """Architecture doc should describe tool profiles, approval gate, and recall."""
    architecture_doc = (
        Path(__file__).resolve().parents[3] / "docs" / "ARCHITECTURE.md"
    ).read_text(encoding="utf-8")

    required_references = [
        "UIPATH_CLAUDE_TOOL_PROFILE",
        "UIPATH_CLAUDE_REQUIRE_APPROVAL",
        "/recall <term>",
        "uipath_claude.query.session_search",
    ]

    for reference in required_references:
        assert reference in architecture_doc, (
            f"Expected architecture doc to mention: {reference}"
        )
