"""Test UiPath AskAI tool."""

from unittest.mock import MagicMock, patch

from uipath_claude.tools.uipath.askai import uipath_askai_tool


def test_askai_requires_configuration(monkeypatch):
    """Tool returns setup guidance when endpoint missing."""
    monkeypatch.delenv("UIPATH_ASKAI_ENDPOINT", raising=False)
    out = uipath_askai_tool.invoke({"query": "how to use queues?"})
    assert "not configured" in out.lower()


def test_askai_success(monkeypatch):
    """Tool returns answer field from API response."""
    monkeypatch.setenv("UIPATH_ASKAI_ENDPOINT", "https://example.com/askai")
    with patch("uipath_claude.tools.uipath.askai.httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"answer": "Use Add Queue Item."}
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp
        out = uipath_askai_tool.invoke({"query": "queues?"})
    assert "add queue item" in out.lower()

