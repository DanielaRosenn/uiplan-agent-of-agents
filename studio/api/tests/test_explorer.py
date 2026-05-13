"""Tests for the project-explorer API surface (`/explorer/*`)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_explorer_worktrees_returns_at_least_repo_root() -> None:
    client = TestClient(app)
    response = client.get("/explorer/worktrees")
    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert isinstance(payload["items"], list)
    assert len(payload["items"]) >= 1
    repo_root = next(
        (w for w in payload["items"] if w["id"] == "repo-root"),
        None,
    )
    assert repo_root is not None
    assert repo_root["path"]


def test_explorer_graph_known_worktree_returns_indexed_payload() -> None:
    client = TestClient(app)
    response = client.get("/explorer/graph", params={"worktree": "repo-root"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["projectType"]
    assert isinstance(payload["nodes"], list)
    assert isinstance(payload["edges"], list)
    assert payload["meta"]["worktree_id"] == "repo-root"
    # The real indexer ran — files_scanned is populated.
    assert "files_scanned" in payload["meta"]


def test_explorer_graph_relative_path_is_indexed(tmp_path, monkeypatch) -> None:
    """An allow-listed path that isn't a registered worktree but is a valid directory works."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "App.tsx").write_text("export const App = () => null;\n", encoding="utf-8")
    monkeypatch.setenv("UIPATH_EXPLORER_ROOTS", str(tmp_path))
    client = TestClient(app)
    response = client.get("/explorer/graph", params={"worktree": str(tmp_path)})
    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["worktree_id"] == tmp_path.name


def test_explorer_refresh_state_tracks_plan_file_changes(tmp_path, monkeypatch) -> None:
    plan_dir = tmp_path / ".cursor" / "plans" / "demo"
    plan_dir.mkdir(parents=True)
    plan_file = plan_dir / "plan.md"
    plan_file.write_text("# Plan\n", encoding="utf-8")
    monkeypatch.setenv("UIPATH_EXPLORER_ROOTS", str(tmp_path))

    client = TestClient(app)
    response = client.get("/explorer/refresh-state", params={"worktree": str(tmp_path)})

    assert response.status_code == 200
    payload = response.json()
    assert payload["worktree_id"] == tmp_path.name
    assert payload["stamp"]
    assert payload["source_count"] == 1


def test_explorer_graph_path_outside_allowlist_is_403(tmp_path, monkeypatch) -> None:
    """A path that exists but is not under any allow-listed root is rejected."""
    monkeypatch.delenv("UIPATH_EXPLORER_ROOTS", raising=False)
    (tmp_path / "src").mkdir()
    client = TestClient(app)
    response = client.get("/explorer/graph", params={"worktree": str(tmp_path)})
    assert response.status_code == 403
    assert "allow-list" in response.json()["detail"]


def test_explorer_graph_unknown_worktree_404() -> None:
    client = TestClient(app)
    response = client.get("/explorer/graph", params={"worktree": "does-not-exist"})
    assert response.status_code == 404


def test_explorer_init_creates_yaml(tmp_path) -> None:
    client = TestClient(app)
    response = client.post("/explorer/init", json={"project_dir": str(tmp_path)})
    assert response.status_code == 200
    payload = response.json()
    assert payload["created"] is True
    config_path = tmp_path / ".uiplan" / "explorer.yaml"
    assert config_path.is_file()
    body = config_path.read_text(encoding="utf-8")
    assert "project:" in body
    assert "overview:" in body
    # Re-running is idempotent
    response2 = client.post("/explorer/init", json={"project_dir": str(tmp_path)})
    assert response2.status_code == 200
    assert response2.json()["created"] is False


def test_explorer_knowledge_returns_envelope() -> None:
    """Even when the library/skill backends return nothing, the response
    envelope must still be valid (citations + skills as lists)."""
    client = TestClient(app)
    response = client.get(
        "/explorer/knowledge",
        params={"worktree": "repo-root", "node": "Main", "q": "workflow analyzer"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload.get("citations"), list)
    assert isinstance(payload.get("skills"), list)


def test_explorer_skill_unknown_404() -> None:
    client = TestClient(app)
    response = client.get("/explorer/skill", params={"id": "no-such-skill"})
    assert response.status_code == 404


def test_explorer_library_section_unknown_404() -> None:
    client = TestClient(app)
    response = client.get(
        "/explorer/library/section",
        params={"book": "no-such-book", "chapter": "x", "section": "y"},
    )
    assert response.status_code == 404
