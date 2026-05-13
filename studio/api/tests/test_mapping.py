"""Tests for the Copilot-first mapping endpoint."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_map_folder_validates_path_exists(tmp_path: Path) -> None:
    """Mapping endpoint returns 404 for non-existent folders."""
    client = TestClient(app)
    response = client.post(
        "/mapping/map-folder",
        json={"path": str(tmp_path / "does-not-exist")},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_map_folder_validates_path_in_allowlist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mapping endpoint returns 403 for folders outside the allow-list."""
    (tmp_path / "project").mkdir()
    client = TestClient(app)
    
    # Without allowlist extension, tmp_path is not allowed
    response = client.post(
        "/mapping/map-folder",
        json={"path": str(tmp_path / "project")},
    )
    assert response.status_code == 403
    assert "allow-list" in response.json()["detail"]


def test_map_folder_returns_copilot_unavailable_when_sdk_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mapping endpoint returns explicit error when Copilot SDK is unavailable."""
    (tmp_path / "project").mkdir()
    (tmp_path / "project" / ".uiplan").mkdir()
    (tmp_path / "project" / ".uiplan" / "explorer.yaml").write_text(
        "project:\n  name: Test\n  type: unknown\n"
    )
    monkeypatch.setenv("UIPATH_EXPLORER_ROOTS", str(tmp_path))
    
    client = TestClient(app)
    response = client.post(
        "/mapping/map-folder",
        json={"path": str(tmp_path / "project")},
    )
    
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "deterministic-fallback"
    assert body["meta"]["copilot_available"] is False
    assert any(
        "Copilot SDK unavailable" in err["message"]
        for err in body["errors"]
    )


def test_map_folder_returns_deterministic_fallback_with_copilot_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mapping endpoint returns deterministic index when Copilot is available but not yet wired."""
    (tmp_path / "project").mkdir()
    (tmp_path / "project" / ".uiplan").mkdir()
    (tmp_path / "project" / ".uiplan" / "explorer.yaml").write_text(
        "project:\n  name: Test\n  type: rpa\n"
    )
    (tmp_path / "project" / "Main.xaml").write_text("<Activity />")
    monkeypatch.setenv("UIPATH_EXPLORER_ROOTS", str(tmp_path))
    
    client = TestClient(app)
    response = client.post(
        "/mapping/map-folder",
        json={"path": str(tmp_path / "project")},
    )
    
    assert response.status_code == 200
    body = response.json()
    # Until Copilot action is wired, source is still fallback
    assert body["source"] in ("deterministic-fallback", "copilot")
    assert isinstance(body["nodes"], list)
    assert isinstance(body["edges"], list)
    assert "project_type" in body["meta"]
