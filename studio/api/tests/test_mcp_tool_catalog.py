from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_mcp_tool_catalog_returns_categories_and_phase_mapping() -> None:
    client = TestClient(app)
    response = client.get("/agentops/mcp/tools")

    assert response.status_code == 200
    payload = response.json()
    assert payload["categories"]
    assert payload["phase_tool_mapping"]
    assert "deploy" in payload["phase_tool_mapping"]


def test_mcp_tool_catalog_exposes_risk_approval_and_demo_safe() -> None:
    client = TestClient(app)
    response = client.get("/agentops/mcp/tools")

    assert response.status_code == 200
    payload = response.json()
    assert payload["risk_levels"]
    assert payload["approval_requirements"]
    assert payload["demo_safe_actions"]
    assert "orchestrator.start_job" not in payload["demo_safe_actions"]

