from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_orchestrator_runbook_contains_safety_and_preflight_policy():
    text = _read("docs/ORCHESTRATOR_DEPLOYMENT.md")

    assert "Compatibility Preflight" in text
    assert "explicit human confirmation" in text
    assert "personal workspace" in text
    assert "named Dev folder" in text
    assert "Do not deploy to Production" in text
    assert "Maestro" in text
    assert "Solution" in text


def test_deployment_integration_redirects_without_stale_trigger_examples():
    text = _read("docs/legacy/DEPLOYMENT_INTEGRATION.md")

    assert "ORCHESTRATOR_DEPLOYMENT.md" in text
    assert "deploy_to_orchestrator" not in text
    assert "deploy to production" not in text.lower()
    assert "explicit human confirmation" in text


def test_workflow_docs_put_compatibility_preflight_before_scaffold_commands():
    text = _read("docs/uipath-workflows.md")

    preflight_index = text.index("Compatibility preflight")
    scaffold_index = text.index("### Scaffold commands")
    assert preflight_index < scaffold_index
    assert "ORCHESTRATOR_DEPLOYMENT.md" in text

