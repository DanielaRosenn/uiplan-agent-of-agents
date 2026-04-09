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


def test_old_agent_package_still_exists():
    """Test that old 'agent' package still exists (will be removed in Task 13)."""
    spec = importlib.util.find_spec("agent")
    assert spec is not None, "Old 'agent' package should still exist until Task 13"
