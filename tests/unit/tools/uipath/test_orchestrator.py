"""Test UiPath Orchestrator tool."""

from unittest.mock import MagicMock, patch

from uipath_claude.tools.uipath.orchestrator import orchestrator_api_tool


def test_orchestrator_requires_configuration(monkeypatch):
    """Tool returns setup guidance when env vars missing."""
    monkeypatch.delenv("UIPATH_ORCHESTRATOR_URL", raising=False)
    monkeypatch.delenv("UIPATH_ORCHESTRATOR_TOKEN", raising=False)
    out = orchestrator_api_tool.invoke({"endpoint": "odata/Jobs", "method": "GET"})
    assert "not configured" in out.lower()


def test_orchestrator_json_success(monkeypatch):
    """Tool returns JSON payload as text on success."""
    monkeypatch.setenv("UIPATH_ORCHESTRATOR_URL", "https://orch.example.com")
    monkeypatch.setenv("UIPATH_ORCHESTRATOR_TOKEN", "token")
    with patch("uipath_claude.tools.uipath.orchestrator.httpx.request") as mock_request:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.headers = {"content-type": "application/json"}
        mock_resp.json.return_value = {"count": 2}
        mock_request.return_value = mock_resp
        out = orchestrator_api_tool.invoke({"endpoint": "odata/Jobs", "method": "GET"})
    assert "count" in out.lower()

