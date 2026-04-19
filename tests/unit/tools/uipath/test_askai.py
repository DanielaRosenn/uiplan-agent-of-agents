"""Test UiPath AskAI tool."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from uipath_claude.tools.uipath import askai
from uipath_claude.tools.uipath.askai import uipath_askai_tool


def test_askai_requires_configuration(monkeypatch):
    """Tool returns setup guidance when endpoint missing."""
    monkeypatch.delenv("UIPATH_ASKAI_ENDPOINT", raising=False)
    with patch.object(askai, "_skills_askai_dir", return_value=Path("/__no_such_skill__/askai")):
        out = uipath_askai_tool.invoke({"query": "how to use queues?"})
    assert "not available" in out.lower() or "endpoint" in out.lower()


def test_askai_success(monkeypatch):
    """Tool returns answer field from API response."""
    monkeypatch.setenv("UIPATH_ASKAI_ENDPOINT", "https://example.com/askai")
    with (
        patch.object(askai, "_skills_askai_dir", return_value=Path("/__no_such_skill__/askai")),
        patch("uipath_claude.tools.uipath.askai.httpx.post") as mock_post,
    ):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"answer": "Use Add Queue Item."}
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp
        out = uipath_askai_tool.invoke({"query": "queues?"})
    assert "add queue item" in out.lower()


def test_askai_mock_endpoint_returns_deterministic(monkeypatch):
    """mock:// endpoint short-circuits to a deterministic local response."""
    monkeypatch.setenv("UIPATH_ASKAI_ENDPOINT", "mock://localfixture")
    with patch.object(
        askai, "_skills_askai_dir", return_value=Path("/__no_such_skill__/askai")
    ):
        out = askai.query_uipath_documentation("what about queues?")
    assert out.ok
    assert "SOURCE: askai-mock" in out.message
    assert "queues" in out.message.lower()


def test_query_uipath_documentation_http_ok(monkeypatch):
    monkeypatch.setenv("UIPATH_ASKAI_ENDPOINT", "https://example.com/askai")
    with (
        patch.object(askai, "_skills_askai_dir", return_value=Path("/__no_such_skill__/askai")),
        patch("uipath_claude.tools.uipath.askai.httpx.post") as mock_post,
    ):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"answer": "HTTP answer"}
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp
        out = askai.query_uipath_documentation("q")
        assert out.ok and "HTTP answer" in out.message

