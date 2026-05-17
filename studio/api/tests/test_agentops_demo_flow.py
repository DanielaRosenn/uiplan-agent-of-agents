from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import fixtures as fixtures_router


def _demo_intake_payload() -> dict[str, object]:
    intake_path = (
        Path(__file__).resolve().parents[3] / "samples" / "invoice-exception" / "intake.json"
    )
    return json.loads(intake_path.read_text(encoding="utf-8"))


def test_agentops_demo_run_returns_cockpit_payload() -> None:
    client = TestClient(app)
    response = client.post("/agentops/demo/run", json=_demo_intake_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["orchestrator_state"]["current_phase"]
    assert isinstance(payload["specialist_assignments"], list)
    assert isinstance(payload["as_is_view_model"]["handoffs"], list)
    assert isinstance(payload["to_be_view_model"]["workflows"], list)
    assert isinstance(payload["verification_checklist"], list)
    assert payload["deployment_readiness_status"]["status"] in {"blocked", "ready", "deployed"}
    assert "summary" in payload["handoff_summary"]
    assert isinstance(payload["build_queue"], list)


def test_agentops_demo_run_rejects_missing_business_goal() -> None:
    client = TestClient(app)
    response = client.post("/agentops/demo/run", json={"systems": ["ERP"]})

    assert response.status_code == 422


def test_fixtures_demo_intake_returns_expected_shape() -> None:
    client = TestClient(app)
    response = client.get("/fixtures/demo/intake")

    assert response.status_code == 200
    payload = response.json()
    assert payload["businessGoal"]
    assert isinstance(payload["systems"], list)
    assert isinstance(payload["constraints"], list)
    assert isinstance(payload["successCriteria"], list)


def test_fixtures_demo_intake_missing_file_hides_absolute_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(fixtures_router, "_repo_root", lambda: tmp_path)
    client = TestClient(app)
    response = client.get("/fixtures/demo/intake")

    assert response.status_code == 404
    assert response.json()["detail"] == "Demo intake file is unavailable"
    assert str(tmp_path) not in response.json()["detail"]


def test_fixtures_demo_intake_invalid_json_returns_500(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    demo_dir = tmp_path / "samples" / "invoice-exception"
    demo_dir.mkdir(parents=True)
    (demo_dir / "intake.json").write_text("{not-json", encoding="utf-8")
    monkeypatch.setattr(fixtures_router, "_repo_root", lambda: tmp_path)

    client = TestClient(app)
    response = client.get("/fixtures/demo/intake")

    assert response.status_code == 500
    assert "invalid JSON" in response.json()["detail"]


@pytest.mark.parametrize(
    "output_name",
    [
        "../evil",
        "..\\evil",
        "evil/name",
        "evil\\name",
        "evil.ts",
        "123bad",
        "bad-name",
        "bad name",
    ],
)
def test_export_demo_fixture_rejects_malicious_output_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, output_name: str
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir(parents=True)
    monkeypatch.setattr(fixtures_router, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(fixtures_router, "_allowed_worktree_roots", lambda: [tmp_path])

    async def _fake_graph(_path: str) -> dict[str, object]:
        return {"projectType": "demo", "meta": {}, "nodes": [], "edges": []}

    monkeypatch.setattr(fixtures_router, "get_project_graph", _fake_graph)

    client = TestClient(app)
    response = client.post(
        "/fixtures/export-demo",
        params={"source_path": str(source_dir), "output_name": output_name},
    )

    assert response.status_code == 400
    assert "Invalid output_name" in response.json()["detail"]
