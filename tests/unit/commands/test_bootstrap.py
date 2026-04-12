"""Test bootstrap command."""

from uipath_claude.commands.bootstrap import register_bootstrap_command
from uipath_claude.commands.registry import CommandRegistry


async def _fake_bootstrap(_request: str) -> dict:
    return {
        "pdd": "pdd out",
        "sdd": "sdd out",
        "code": "code out",
        "validation": "validation out",
        "paths": {"pdd": "/tmp/pdd.md", "sdd": "/tmp/sdd.md"},
    }


def test_bootstrap_command_usage():
    """Test /bootstrap without request returns usage."""
    registry = CommandRegistry()
    register_bootstrap_command(registry, run_bootstrap=_fake_bootstrap)
    out = registry.execute("bootstrap")
    assert "usage: /bootstrap" in out.lower()


def test_bootstrap_command_runs_flow():
    """Test /bootstrap executes flow and renders output."""
    registry = CommandRegistry()
    register_bootstrap_command(registry, run_bootstrap=_fake_bootstrap)
    out = registry.execute("bootstrap", "build", "invoice")
    assert "bootstrap complete" in out.lower()
    assert "artifacts written" in out.lower()
    assert "pdd:" in out.lower()
    assert "summaries" in out.lower()

