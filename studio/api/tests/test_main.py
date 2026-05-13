import json

from fastapi.testclient import TestClient
import pytest

from app import copilot_runtime
from app.copilot_runtime import (
    COPILOT_ACTION_NAMES,
    draft_section_preview_request,
    suggest_diagram_node,
    summarize_diagram_state,
)
from app import main
from app import state
from app import context_sources
from app.schemas import ContextSource, ContextSourceCategory, ContextSourcesResponse
from app.security import _host_without_port, is_loopback_client, is_loopback_host
from app.main import app


def test_preview_store_expires_stale_preview(monkeypatch) -> None:
    now = 1_000.0

    def fake_time() -> float:
        return now

    monkeypatch.setattr(state.time, "time", fake_time)
    store = state.PreviewStore(ttl_seconds=5, max_entries=10)
    store.set("preview-1", {"path": "plan.md", "content": "draft", "base_hash": "abc"})

    assert store.get("preview-1") is not None

    now = 1_006.0
    assert store.get("preview-1") is None
    assert "preview-1" not in store


def test_preview_store_prunes_oldest_entry_when_full(monkeypatch) -> None:
    now = 2_000.0

    def fake_time() -> float:
        return now

    monkeypatch.setattr(state.time, "time", fake_time)
    store = state.PreviewStore(ttl_seconds=60, max_entries=2)

    store.set("oldest", {"path": "spec.md", "content": "v1", "base_hash": "h1"})
    now = 2_001.0
    store.set("newer", {"path": "plan.md", "content": "v2", "base_hash": "h2"})
    now = 2_002.0
    store.set("newest", {"path": "tasks.md", "content": "v3", "base_hash": "h3"})

    assert store.get("oldest") is None
    assert store.get("newer") is not None
    assert store.get("newest") is not None


def test_health_routes_match_exposed_endpoints() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "/generate/section-preview" in payload["routes"]
    assert "/generate/diagram-preview" in payload["routes"]
    assert "/generate/apply" in payload["routes"]
    assert "/lifecycle/readiness" in payload["routes"]
    assert "/diagram/load" in payload["routes"]
    assert "/diagram/save" in payload["routes"]
    assert "/bundle/save" not in payload["routes"]
    assert "/agent/context-sources" in payload["routes"]


def test_studio_api_rejects_non_loopback_host() -> None:
    client = TestClient(app)

    response = client.get("/health", headers={"host": "studio.example.com"})

    assert response.status_code == 403
    assert response.json()["detail"] == "UiPlan Studio API is local-only."


def test_studio_api_allows_loopback_host() -> None:
    client = TestClient(app)

    response = client.get("/health", headers={"host": "127.0.0.1:8000"})

    assert response.status_code == 200
    assert response.json()["metadata"]["network_policy"] == "local-only"


def test_studio_api_rejects_remote_client_even_with_loopback_host() -> None:
    client = TestClient(app, client=("203.0.113.42", 50000))

    response = client.get("/health", headers={"host": "127.0.0.1:8000"})

    assert response.status_code == 403
    assert response.json()["detail"] == "UiPlan Studio API is local-only."


def test_studio_api_allows_unbracketed_ipv6_loopback_host() -> None:
    assert is_loopback_host("::1") is True


@pytest.mark.parametrize(
    ("host_header", "expected"),
    [
        ("", ""),
        ("LOCALHOST", "localhost"),
        ("[::1]:8000", "::1"),
        ("127.0.0.1:8000", "127.0.0.1"),
        ("::1", "::1"),
    ],
)
def test_host_without_port_handles_loopback_host_forms(
    host_header: str,
    expected: str,
) -> None:
    assert _host_without_port(host_header) == expected


@pytest.mark.parametrize(
    ("client_host", "expected"),
    [
        ("127.0.0.1", True),
        ("::1", True),
        ("testclient", True),
        ("localhost", True),
        ("203.0.113.42", False),
        ("remote-host", False),
    ],
)
def test_is_loopback_client_filters_remote_clients(client_host: str, expected: bool) -> None:
    assert is_loopback_client(client_host) is expected


def test_bundle_load_accepts_relative_repo_path_when_cwd_differs(monkeypatch, tmp_path) -> None:
    repo_root = tmp_path / "repo"
    plans_root = repo_root / ".cursor" / "plans"
    bundle_root = plans_root / "example"
    bundle_root.mkdir(parents=True)
    (bundle_root / ".meta.yaml").write_text("slug: example\nstatus: draft\n", encoding="utf-8")
    for document_name in ("spec.md", "plan.md", "tasks.md"):
        (bundle_root / document_name).write_text(f"# {document_name}\n", encoding="utf-8")
    other_cwd = tmp_path / "service-cwd"
    other_cwd.mkdir()
    monkeypatch.setattr(state, "PLANS_ROOT", plans_root.resolve())
    monkeypatch.chdir(other_cwd)

    client = TestClient(app)
    response = client.get("/bundle/load", params={"bundle_root": ".cursor/plans/example"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["root"] == str(bundle_root.resolve())
    assert payload["documents"]["spec.md"] == "# spec.md\n"


def test_bundle_save_is_legacy_internal_and_guarded(monkeypatch, tmp_path) -> None:
    plans_root = tmp_path / "plans"
    bundle_root = plans_root / "example"
    bundle_root.mkdir(parents=True)
    target = bundle_root / "spec.md"
    target.write_text("# Spec\n", encoding="utf-8")
    monkeypatch.setattr(state, "PLANS_ROOT", plans_root.resolve())

    client = TestClient(app)
    direct_response = client.post(
        "/bundle/save",
        json={
            "bundle_root": str(bundle_root),
            "document_name": "spec.md",
            "content": "# Direct write\n",
        },
    )

    assert direct_response.status_code == 403
    assert "legacy internal endpoint" in direct_response.json()["detail"]
    assert target.read_text(encoding="utf-8") == "# Spec\n"

    legacy_response = client.post(
        "/bundle/save",
        json={
            "bundle_root": str(bundle_root),
            "document_name": "spec.md",
            "content": "# Internal write\n",
            "legacy_internal": True,
            "write_policy": main.LEGACY_DIRECT_SAVE_POLICY,
        },
    )

    assert legacy_response.status_code == 200
    assert target.read_text(encoding="utf-8") == "# Internal write\n"


def test_cors_allows_localhost_origin_preflight() -> None:
    client = TestClient(app)
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_agent_library_context_returns_ranked_items(monkeypatch) -> None:
    from app import library_service
    monkeypatch.setattr(
        library_service,
        "search_library_context",
        lambda _query, _top_n: [
            {
                "book_id": "uipath-cli",
                "chapter_id": "03-agent",
                "section_id": "deploy",
                "score": 8,
                "snippet": "Deploy section",
                "full_text": "Full deploy section text",
            }
        ],
    )
    client = TestClient(app)
    response = client.post("/agent/library-context", json={"query": "deploy", "top_n": 3})
    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "deploy"
    assert len(payload["items"]) == 1
    assert payload["items"][0]["book_id"] == "uipath-cli"


def test_agent_context_sources_returns_builder_categories_and_core_skills() -> None:
    client = TestClient(app)
    response = client.get("/agent/context-sources")

    assert response.status_code == 200
    payload = response.json()
    categories = {category["id"]: category for category in payload["categories"]}
    assert set(categories) == {"skills", "library", "documents", "review"}

    skill_ids = {source["id"] for source in categories["skills"]["sources"]}
    assert {
        "uipath-rpa",
        "uipath-agents",
        "uipath-platform",
        "uipath-human-in-the-loop",
        "uipath-solution-design",
    }.issubset(skill_ids)
    assert "uiplan-full" in skill_ids

    library_sources = categories["library"]["sources"]
    assert any(source["id"] == "uipath-cli" for source in library_sources)
    assert all("full_text" not in source for source in library_sources)


def test_copilotkit_info_exposes_builder_actions() -> None:
    client = TestClient(app)
    response = client.get("/copilotkit/info")

    assert response.status_code == 200
    payload = response.json()
    action_names = {action["name"] for action in payload["actions"]}
    assert set(COPILOT_ACTION_NAMES).issubset(action_names)
    agents = payload["agents"]
    if isinstance(agents, dict):
        if "default" in agents:
            assert agents["default"]["description"]
    else:
        assert isinstance(agents, list)
    assert payload["runtime"]["mode"] in {"official-fastapi", "metadata-fallback"}
    if payload["runtime"]["official_fastapi"]:
        assert payload["runtime"]["fallback_reason"] is None
    else:
        assert payload["runtime"]["fallback_reason"]


def test_copilotkit_info_exposes_package_drafting_actions() -> None:
    client = TestClient(app)
    response = client.get("/copilotkit/info")

    assert response.status_code == 200
    action_names = {action["name"] for action in response.json()["actions"]}
    assert "draft_plan_package_request" in action_names
    assert "draft_scaffold_package_request" in action_names


def test_copilot_package_drafting_actions_are_preview_only() -> None:
    client = TestClient(app)
    response = client.post(
        "/copilotkit/runtime/action/draft_plan_package_request",
        json={
            "arguments": {
                "bundle_root": ".cursor/plans/example",
                "graph_id": "graph-1",
                "selected_node_id": "intake",
            }
        },
    )

    assert response.status_code == 200
    result = response.json()["result"]
    assert result["endpoint"] == "/generation/packages"
    assert result["method"] == "POST"
    assert result["write_policy"] == "approval_package_only"
    assert result["body"]["stages"] == ["01-plan"]


def test_official_copilotkit_runtime_endpoint_exposes_actions() -> None:
    client = TestClient(app)
    response = client.get("/copilotkit/runtime")

    assert response.status_code == 200
    payload = response.json()
    action_names = {action["name"] for action in payload["actions"]}
    assert "suggest_diagram_node" in action_names
    assert "draft_section_preview_request" in action_names
    assert "sdkVersion" in payload


def test_official_copilotkit_runtime_executes_builder_action() -> None:
    client = TestClient(app)
    response = client.post(
        "/copilotkit/runtime/action/suggest_diagram_node",
        json={
            "arguments": {
                "source_kind": "library",
                "title": "CLI pack docs",
                "description": "Package and analyze guidance.",
                "source": "uipath-cli/package-pack",
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()["result"]
    assert payload["operation"] == "suggest_only"
    assert payload["suggested_node"]["kind"] == "library"


@pytest.mark.parametrize(
    ("action_name", "arguments", "expected_detail"),
    [
        ("suggest_diagram_node", {}, "Missing required argument(s): description, source_kind, title"),
        (
            "list_context_sources",
            {"category_id": "skills", "unexpected": True},
            "Unexpected argument(s): unexpected",
        ),
        ("search_library_context", {"query": 123}, "query must be a string"),
        ("search_library_context", {"query": "deploy", "top_n": "many"}, "top_n must be an integer"),
        ("search_library_context", {"query": "deploy", "top_n": 0}, "top_n must be between 1 and 20"),
        ("search_library_context", {"query": "deploy", "top_n": 21}, "top_n must be between 1 and 20"),
    ],
)
def test_fallback_copilot_runtime_rejects_malformed_action_arguments(
    action_name: str,
    arguments: dict[str, object],
    expected_detail: str,
) -> None:
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        f"/copilotkit/runtime/action/{action_name}",
        json={"arguments": arguments},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == expected_detail


def test_copilot_runtime_action_route_uses_local_validation_even_with_sdk() -> None:
    action_routes = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/copilotkit/runtime/action/{action_name}"
        and "POST" in getattr(route, "methods", set())
    ]

    assert action_routes
    assert action_routes[0].endpoint.__module__ == "app.copilot_runtime"


def test_copilot_runtime_action_rejects_non_object_arguments() -> None:
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/copilotkit/runtime/action/suggest_diagram_node",
        json={"arguments": "not-an-object"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "arguments must be an object"


def test_search_library_context_action_validates_and_clamps_result_limit(monkeypatch) -> None:
    calls: list[tuple[str, int]] = []

    def fake_search_library_context(query: str, top_n: int) -> list[dict[str, object]]:
        calls.append((query, top_n))
        return []

    monkeypatch.setattr(copilot_runtime, "search_library_context", fake_search_library_context)
    client = TestClient(app)

    response = client.post(
        "/copilotkit/runtime/action/search_library_context",
        json={"arguments": {"query": " deploy ", "top_n": 20}},
    )

    assert response.status_code == 200
    assert response.json()["result"] == {"query": "deploy", "items": []}
    assert calls == [("deploy", 20)]


def test_copilotkit_generate_response_is_configured() -> None:
    client = TestClient(app)
    response = client.post("/copilotkit", json={"operationName": "GenerateCopilotResponse"})

    assert response.status_code == 200
    payload = response.json()["data"]["generateCopilotResponse"]
    assert payload["status"]["code"] == "SUCCESS"
    assert payload["status"]["reason"] != "RUNTIME_NOT_CONFIGURED"
    assert payload["messages"] == []
    action_names = {action["name"] for action in payload["actions"]}
    assert "suggest_diagram_node" in action_names


def test_copilotkit_get_returns_runtime_info() -> None:
    client = TestClient(app)
    response = client.get("/copilotkit")

    assert response.status_code == 200
    payload = response.json()
    action_names = {action["name"] for action in payload["actions"]}
    assert set(COPILOT_ACTION_NAMES).issubset(action_names)


def test_frontend_copilotkit_runtime_accepts_graphql_generate_response() -> None:
    client = TestClient(app)
    response = client.post(
        "/copilotkit",
        json={
            "operationName": "generateCopilotResponse",
            "query": "mutation generateCopilotResponse { generateCopilotResponse { threadId runId status { code reason message } } }",
            "variables": {
                "data": {
                    "messages": [],
                    "frontend": {"actions": []},
                }
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]["generateCopilotResponse"]
    assert payload["threadId"] == "local"
    assert payload["status"]["code"] == "SUCCESS"
    assert payload["status"]["reason"] != "RUNTIME_NOT_CONFIGURED"
    action_names = {action["name"] for action in payload["actions"]}
    assert set(COPILOT_ACTION_NAMES).issubset(action_names)


def test_copilotkit_available_agents_handles_lowercase_operation() -> None:
    client = TestClient(app)
    response = client.post(
        "/copilotkit",
        json={"operationName": "availableAgents"},
    )

    assert response.status_code == 200
    payload = response.json()["data"]["availableAgents"]
    assert "agents" in payload
    assert isinstance(payload["agents"], list)


def test_copilotkit_load_agent_state_handles_lowercase_operation() -> None:
    client = TestClient(app)
    response = client.post(
        "/copilotkit",
        json={
            "operationName": "loadAgentState",
            "variables": {"data": {"threadId": "thread-123"}},
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]["loadAgentState"]
    assert payload["threadId"] == "thread-123"
    assert payload["threadExists"] is False
    assert payload["state"] == {}
    assert payload["messages"] == []


def test_copilot_action_handlers_preview_without_writing() -> None:
    node = suggest_diagram_node(
        source_kind="skill",
        title="uipath-platform",
        description="Use for Orchestrator and solution lifecycle.",
        source=".cursor/skills/uipath-platform",
        existing_nodes=[{"id": "plan", "kind": "workflow"}],
    )["suggested_node"]
    assert node["kind"] == "skill"
    assert node["source"] == ".cursor/skills/uipath-platform"

    summary = summarize_diagram_state(
        nodes=[node, {"id": "plan", "title": "Plan", "kind": "workflow"}],
        edges=[{"from": "plan", "to": node["id"], "label": "uses"}],
        selected_node_id=node["id"],
    )
    assert summary["node_count"] == 2
    assert summary["selected_node"]["title"] == "uipath-platform"

    preview = draft_section_preview_request(
        bundle_root=".cursor/plans/example",
        document_name="plan.md",
        diagram_summary=summary["summary"],
        context_focus="uipath-platform",
    )
    assert preview["endpoint"] == "/generate/section-preview"
    assert preview["method"] == "POST"
    assert preview["body"]["document_name"] == "plan.md"
    assert preview["write_policy"] == "preview_only"


def test_diagram_load_returns_default_when_missing(monkeypatch, tmp_path) -> None:
    plans_root = tmp_path / "plans"
    bundle_root = plans_root / "example"
    bundle_root.mkdir(parents=True)
    monkeypatch.setattr(state, "PLANS_ROOT", plans_root.resolve())

    client = TestClient(app)
    response = client.get("/diagram/load", params={"bundle_root": str(bundle_root)})

    assert response.status_code == 200
    payload = response.json()
    assert payload["defaulted"] is True
    assert payload["path"] is None
    assert {node["kind"] for node in payload["nodes"]} == {
        "document",
        "workflow",
        "skill",
        "library",
        "review",
    }
    assert any(edge["from"] == "plan" and edge["to"] == "review" for edge in payload["edges"])


def test_diagram_save_and_load_round_trip(monkeypatch, tmp_path) -> None:
    plans_root = tmp_path / "plans"
    bundle_root = plans_root / "example"
    bundle_root.mkdir(parents=True)
    monkeypatch.setattr(state, "PLANS_ROOT", plans_root.resolve())

    diagram = {
        "nodes": [
            {
                "id": "plan",
                "title": "Plan",
                "kind": "workflow",
                "description": "Persist me",
                "x": 10,
                "y": 20,
                "source": "plan.md",
            }
        ],
        "edges": [{"id": "self", "from": "plan", "to": "plan", "label": "loops"}],
    }

    client = TestClient(app)
    save_response = client.post(
        "/diagram/save",
        json={"bundle_root": str(bundle_root), **diagram},
    )

    assert save_response.status_code == 200
    save_payload = save_response.json()
    assert save_payload["bytes_written"] > 0
    assert save_payload["nodes"] == diagram["nodes"]
    assert save_payload["edges"] == diagram["edges"]

    load_response = client.get("/diagram/load", params={"bundle_root": str(bundle_root)})
    assert load_response.status_code == 200
    load_payload = load_response.json()
    assert load_payload["defaulted"] is False
    assert load_payload["nodes"] == diagram["nodes"]
    assert load_payload["edges"] == diagram["edges"]


def test_diagram_save_and_load_preserves_typed_project_graph_fields(monkeypatch, tmp_path) -> None:
    plans_root = tmp_path / "plans"
    bundle_root = plans_root / "example"
    bundle_root.mkdir(parents=True)
    monkeypatch.setattr(state, "PLANS_ROOT", plans_root.resolve())

    diagram = {
        "nodes": [
            {
                "id": "plan",
                "title": "Workflow Plan",
                "kind": "workflow",
                "description": "Typed ProjectGraph node",
                "x": 10,
                "y": 20,
                "source": "plan.md",
                "role": "project_component",
                "output_type": "project_scaffold",
                "project_types": ["solution", "coded-agent"],
                "context_policy": "strict",
                "strict_citation": "required",
                "layer": "agent",
                "status": "ready",
                "metadata": {
                    "projectGraphNodeId": "planning_agent",
                    "visualRole": "central_action",
                },
            }
        ],
        "edges": [
            {
                "id": "plan-review",
                "from": "plan",
                "to": "review",
                "label": "validates",
                "edge_type": "validates",
                "status": "ready",
                "metadata": {"projectGraphEdgeId": "planning_agent:drives:if_ready"},
            }
        ],
    }

    client = TestClient(app)
    save_response = client.post(
        "/diagram/save",
        json={"bundle_root": str(bundle_root), **diagram},
    )
    assert save_response.status_code == 200
    assert save_response.json()["nodes"] == diagram["nodes"]
    assert save_response.json()["edges"] == diagram["edges"]

    stored = json.loads((bundle_root / "diagram.json").read_text(encoding="utf-8"))
    assert stored["nodes"] == diagram["nodes"]
    assert stored["edges"] == diagram["edges"]

    load_response = client.get("/diagram/load", params={"bundle_root": str(bundle_root)})
    assert load_response.status_code == 200
    assert load_response.json()["nodes"] == diagram["nodes"]
    assert load_response.json()["edges"] == diagram["edges"]


def test_command_registry_endpoint_returns_read_only_registry() -> None:
    client = TestClient(app)

    response = client.get("/generation/command-registry")

    assert response.status_code == 200
    payload = response.json()
    command_ids = {command["command_id"] for command in payload["commands"]}
    assert {"plan.markdown.readiness", "scaffold.manifest.readiness"}.issubset(command_ids)
    assert all(command["mutation_classification"] == "read-only" for command in payload["commands"])


def test_diagram_save_sanitizes_unavailable_curated_sources(monkeypatch, tmp_path) -> None:
    plans_root = tmp_path / "plans"
    bundle_root = plans_root / "example"
    bundle_root.mkdir(parents=True)
    monkeypatch.setattr(state, "PLANS_ROOT", plans_root.resolve())
    monkeypatch.setattr(
        context_sources,
        "get_context_sources",
        lambda: ContextSourcesResponse(
            categories=[
                ContextSourceCategory(
                    id="skills",
                    title="Skills",
                    description="Curated skills.",
                    sources=[
                        ContextSource(
                            id="uipath-missing",
                            title="Missing skill",
                            kind="skill",
                            category="skills",
                            description="Unavailable skill.",
                            source=".cursor/skills/uipath-missing",
                            available=False,
                        )
                    ],
                )
            ]
        ),
    )

    client = TestClient(app)
    response = client.post(
        "/diagram/save",
        json={
            "bundle_root": str(bundle_root),
            "nodes": [
                {
                    "id": "source-skills-uipath-missing",
                    "title": "Missing skill",
                    "kind": "skill",
                    "description": "Should not become context.",
                    "x": 10,
                    "y": 20,
                    "source": ".cursor/skills/uipath-missing",
                },
                {
                    "id": "freeform",
                    "title": "Freeform workflow",
                    "kind": "workflow",
                    "description": "Manual node stays editable.",
                    "x": 20,
                    "y": 30,
                    "source": "invoice.flow",
                },
            ],
            "edges": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    sources_by_id = {node["id"]: node.get("source") for node in payload["nodes"]}
    assert sources_by_id["source-skills-uipath-missing"] is None
    assert sources_by_id["freeform"] == "invoice.flow"


@pytest.mark.parametrize(
    ("document_name", "expected"),
    [
        ("spec.md", "### Visual Builder Scope"),
        ("plan.md", "### Implementation Sequence"),
        ("tasks.md", "### Flow-Ordered Checklist"),
    ],
)
def test_diagram_preview_generates_supported_documents_without_writing(
    monkeypatch,
    tmp_path,
    document_name,
    expected,
) -> None:
    plans_root = tmp_path / "plans"
    bundle_root = plans_root / "example"
    bundle_root.mkdir(parents=True)
    monkeypatch.setattr(state, "PLANS_ROOT", plans_root.resolve())
    main._PENDING_GENERATION_PREVIEWS.clear()

    target = bundle_root / document_name
    target.write_text(f"# {document_name}\nOriginal content.\n", encoding="utf-8")
    before = target.read_text(encoding="utf-8")

    client = TestClient(app)
    response = client.post(
        "/generate/diagram-preview",
        json={
            "bundle_root": str(bundle_root),
            "document_name": document_name,
            "nodes": [
                {
                    "id": "workflow",
                    "title": "Workflow",
                    "kind": "workflow",
                    "description": "Build deterministic flow",
                    "x": 10,
                    "y": 20,
                    "source": "plan.md",
                },
                {
                    "id": "skill-platform",
                    "title": "uipath-platform",
                    "kind": "skill",
                    "description": "Use platform lifecycle guidance",
                    "x": 20,
                    "y": 30,
                    "source": ".cursor/skills/uipath-platform",
                },
                {
                    "id": "review",
                    "title": "Review Gates",
                    "kind": "review",
                    "description": "Check preview before apply",
                    "x": 30,
                    "y": 40,
                    "source": "review service",
                },
            ],
            "edges": [
                {
                    "id": "workflow-skill",
                    "from": "workflow",
                    "to": "skill-platform",
                    "label": "uses",
                },
                {
                    "id": "workflow-review",
                    "from": "workflow",
                    "to": "review",
                    "label": "validates",
                },
            ],
            "focus": "skill-platform",
            "context": [
                {
                    "book_id": "uipath-cli",
                    "chapter_id": "package",
                    "section_id": "analyze",
                    "score": 9,
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["preview_id"]
    assert expected in payload["proposed_content"]
    assert "uiplan-diagram-generated:start" in payload["proposed_content"]
    assert f"--- {document_name}" in payload["diff"]
    assert target.read_text(encoding="utf-8") == before


def test_diagram_preview_omits_unavailable_curated_sources(monkeypatch, tmp_path) -> None:
    plans_root = tmp_path / "plans"
    bundle_root = plans_root / "example"
    bundle_root.mkdir(parents=True)
    monkeypatch.setattr(state, "PLANS_ROOT", plans_root.resolve())
    monkeypatch.setattr(
        context_sources,
        "get_context_sources",
        lambda: ContextSourcesResponse(
            categories=[
                ContextSourceCategory(
                    id="skills",
                    title="Skills",
                    description="Curated skills.",
                    sources=[
                        ContextSource(
                            id="uipath-missing",
                            title="Missing skill",
                            kind="skill",
                            category="skills",
                            description="Unavailable skill.",
                            source=".cursor/skills/uipath-missing",
                            available=False,
                        )
                    ],
                )
            ]
        ),
    )
    target = bundle_root / "spec.md"
    target.write_text("# Spec\n", encoding="utf-8")

    client = TestClient(app)
    response = client.post(
        "/generate/diagram-preview",
        json={
            "bundle_root": str(bundle_root),
            "document_name": "spec.md",
            "nodes": [
                {
                    "id": "source-skills-uipath-missing",
                    "title": "Missing skill",
                    "kind": "skill",
                    "description": "Unavailable curated source.",
                    "x": 10,
                    "y": 20,
                    "source": ".cursor/skills/uipath-missing",
                }
            ],
            "edges": [],
            "focus": "source-skills-uipath-missing",
        },
    )

    assert response.status_code == 200
    proposed = response.json()["proposed_content"]
    assert ".cursor/skills/uipath-missing" not in proposed
    assert "- Missing skill (skill): diagram" in proposed


def test_diagram_preview_apply_uses_existing_pending_store(monkeypatch, tmp_path) -> None:
    plans_root = tmp_path / "plans"
    bundle_root = plans_root / "example"
    bundle_root.mkdir(parents=True)
    monkeypatch.setattr(state, "PLANS_ROOT", plans_root.resolve())
    main._PENDING_GENERATION_PREVIEWS.clear()

    target = bundle_root / "plan.md"
    target.write_text("# Plan\nOriginal content.\n", encoding="utf-8")

    client = TestClient(app)
    preview_response = client.post(
        "/generate/diagram-preview",
        json={
            "bundle_root": str(bundle_root),
            "document_name": "plan.md",
            "nodes": [
                {
                    "id": "workflow",
                    "title": "Workflow",
                    "kind": "workflow",
                    "description": "Build deterministic flow",
                    "x": 10,
                    "y": 20,
                }
            ],
            "edges": [],
        },
    )
    assert preview_response.status_code == 200
    assert "Generated From Visual Builder" not in target.read_text(encoding="utf-8")

    apply_response = client.post(
        "/generate/apply",
        json={"preview_id": preview_response.json()["preview_id"]},
    )

    assert apply_response.status_code == 200
    assert "Generated From Visual Builder" in target.read_text(encoding="utf-8")


def test_generation_package_endpoint_creates_plan_package_without_target_write(
    monkeypatch, tmp_path
):
    plans_root = tmp_path / "plans"
    bundle_root = plans_root / "example"
    bundle_root.mkdir(parents=True)
    monkeypatch.setattr(state, "PLANS_ROOT", plans_root.resolve())
    target_doc = bundle_root / "docs" / "uiplan-generation-plan.md"

    client = TestClient(app)
    response = client.post(
        "/generation/packages",
        json={
            "bundle_root": str(bundle_root),
            "reviewer": "Daniela",
            "write_policy": "approval_package_only",
            "stages": ["01-plan"],
            "graph": {
                "graph_id": "graph-api",
                "bundle_root": str(bundle_root),
                "created_from": "test",
                "nodes": [
                    {
                        "id": "plan-node",
                        "title": "Plan Node",
                        "role": "process_step",
                        "output_type": "document",
                        "project_types": ["docs"],
                        "description": "Create implementation plan.",
                    }
                ],
                "edges": [],
                "context_attachments": [],
                "generation_profile": {"allowed_project_types": ["docs"]},
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["generated_stages"] == ["01-plan"]
    assert not target_doc.exists()


def test_generation_package_endpoint_uses_graph_ref_snapshot_metadata(monkeypatch, tmp_path) -> None:
    plans_root = tmp_path / "plans"
    bundle_root = plans_root / "example"
    bundle_root.mkdir(parents=True)
    monkeypatch.setattr(state, "PLANS_ROOT", plans_root.resolve())

    client = TestClient(app)
    response = client.post(
        "/generation/packages",
        json={
            "bundle_root": str(bundle_root),
            "reviewer": "Daniela",
            "write_policy": "approval_package_only",
            "stages": ["01-plan"],
            "graph_ref": {"graph_id": "workspace-graph-1", "selected_node_id": "plan-node"},
            "graph": {
                "graph_id": "different-graph-id",
                "bundle_root": str(bundle_root),
                "created_from": "test-client",
                "nodes": [
                    {
                        "id": "plan-node",
                        "title": "Plan Node",
                        "role": "process_step",
                        "output_type": "document",
                        "project_types": ["docs"],
                        "description": "Create implementation plan.",
                    }
                ],
                "edges": [],
                "context_attachments": [],
                "generation_profile": {"allowed_project_types": ["docs"]},
            },
        },
    )

    assert response.status_code == 200
    manifest = response.json()
    assert manifest["graph_id"] == "workspace-graph-1"

    package_root = (
        bundle_root / ".uiplan" / "generation" / "packages" / manifest["package_id"]
    )
    graph_snapshot = json.loads((package_root / "graph.snapshot.json").read_text(encoding="utf-8"))
    assert graph_snapshot["graph_id"] == "workspace-graph-1"
    assert graph_snapshot["created_from"] == "test-client:selected_node:plan-node"


def test_generation_package_endpoint_rejects_non_preview_first_write_policy(
    monkeypatch, tmp_path
) -> None:
    plans_root = tmp_path / "plans"
    bundle_root = plans_root / "example"
    bundle_root.mkdir(parents=True)
    monkeypatch.setattr(state, "PLANS_ROOT", plans_root.resolve())

    client = TestClient(app)
    response = client.post(
        "/generation/packages",
        json={
            "bundle_root": str(bundle_root),
            "reviewer": "Daniela",
            "write_policy": "direct_write",
            "stages": ["01-plan"],
            "graph": {
                "graph_id": "graph-api",
                "bundle_root": str(bundle_root),
                "created_from": "test",
                "nodes": [],
                "edges": [],
                "context_attachments": [],
                "generation_profile": {"allowed_project_types": ["docs"]},
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only approval_package_only write_policy is supported."


def test_generation_package_endpoint_rejects_scaffold_without_plan_or_approved_prior(
    monkeypatch, tmp_path
) -> None:
    plans_root = tmp_path / "plans"
    bundle_root = plans_root / "example"
    bundle_root.mkdir(parents=True)
    monkeypatch.setattr(state, "PLANS_ROOT", plans_root.resolve())
    client = TestClient(app)

    response = client.post(
        "/generation/packages",
        json={
            "bundle_root": str(bundle_root),
            "reviewer": "Daniela",
            "write_policy": "approval_package_only",
            "stages": ["02-scaffold"],
            "graph": {
                "graph_id": "graph-scaffold-missing-plan",
                "bundle_root": str(bundle_root),
                "created_from": "test",
                "nodes": [
                    {
                        "id": "intake",
                        "title": "Customer Intake",
                        "role": "process_step",
                        "output_type": "document",
                        "project_types": ["docs", "coded-agent"],
                        "description": "Prepare scaffold manifests.",
                    }
                ],
                "edges": [],
                "context_attachments": [],
                "generation_profile": {"allowed_project_types": ["docs", "coded-agent"]},
            },
        },
    )

    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "approved prior plan package" in detail
    assert "matching graph lineage" in detail


def test_generation_package_endpoint_scaffold_uses_approved_prior_plan_and_never_writes_target(
    monkeypatch, tmp_path
) -> None:
    plans_root = tmp_path / "plans"
    bundle_root = plans_root / "example"
    bundle_root.mkdir(parents=True)
    monkeypatch.setattr(state, "PLANS_ROOT", plans_root.resolve())
    client = TestClient(app)

    graph_payload = {
        "graph_id": "graph-scaffold-approved-prior",
        "bundle_root": str(bundle_root),
        "created_from": "test",
        "nodes": [
            {
                "id": "intake",
                "title": "Customer Intake",
                "role": "process_step",
                "output_type": "document",
                "project_types": ["docs", "coded-agent"],
                "description": "Prepare scaffold manifests.",
            }
        ],
        "edges": [],
        "context_attachments": [],
        "generation_profile": {"allowed_project_types": ["docs", "coded-agent"]},
    }

    plan_response = client.post(
        "/generation/packages",
        json={
            "bundle_root": str(bundle_root),
            "reviewer": "Daniela",
            "write_policy": "approval_package_only",
            "stages": ["01-plan"],
            "graph": graph_payload,
        },
    )
    assert plan_response.status_code == 200
    plan_package_id = plan_response.json()["package_id"]
    prior_state_path = (
        bundle_root
        / ".uiplan"
        / "generation"
        / "packages"
        / plan_package_id
        / "approval-state.json"
    )
    prior_state = json.loads(prior_state_path.read_text(encoding="utf-8"))
    prior_state["stage_statuses"]["01-plan"] = "approved"
    prior_state_path.write_text(json.dumps(prior_state, indent=2) + "\n", encoding="utf-8")

    scaffold_response = client.post(
        "/generation/packages",
        json={
            "bundle_root": str(bundle_root),
            "reviewer": "Daniela",
            "write_policy": "approval_package_only",
            "stages": ["02-scaffold"],
            "graph": graph_payload,
        },
    )
    assert scaffold_response.status_code == 200
    scaffold_payload = scaffold_response.json()
    assert scaffold_payload["generated_stages"] == ["02-scaffold"]

    scaffold_package_id = scaffold_payload["package_id"]
    scaffold_root = (
        bundle_root
        / ".uiplan"
        / "generation"
        / "packages"
        / scaffold_package_id
        / "stages"
        / "02-scaffold"
    )
    assert (scaffold_root / "proposals" / "projects-customer-intake-manifest.json").exists()
    assert not (bundle_root / "projects" / "CustomerIntake" / "project.manifest.json").exists()
    scaffold_state = json.loads(
        (
            bundle_root / ".uiplan" / "generation" / "packages" / scaffold_package_id / "approval-state.json"
        ).read_text(encoding="utf-8")
    )
    assert scaffold_state["stage_statuses"]["01-plan"] == "not_started"
    assert scaffold_state["stage_statuses"]["02-scaffold"] == "ready_for_review"


def test_generation_package_endpoint_rejects_scaffold_with_unrelated_approved_prior_plan(
    monkeypatch, tmp_path
) -> None:
    plans_root = tmp_path / "plans"
    bundle_root = plans_root / "example"
    bundle_root.mkdir(parents=True)
    monkeypatch.setattr(state, "PLANS_ROOT", plans_root.resolve())
    client = TestClient(app)

    prior_graph_payload = {
        "graph_id": "graph-approved-prior",
        "bundle_root": str(bundle_root),
        "created_from": "test",
        "nodes": [
            {
                "id": "intake",
                "title": "Customer Intake",
                "role": "process_step",
                "output_type": "document",
                "project_types": ["docs", "coded-agent"],
                "description": "Prepare scaffold manifests.",
            }
        ],
        "edges": [],
        "context_attachments": [],
        "generation_profile": {"allowed_project_types": ["docs", "coded-agent"]},
    }
    request_graph_payload = {**prior_graph_payload, "graph_id": "graph-current-request"}

    plan_response = client.post(
        "/generation/packages",
        json={
            "bundle_root": str(bundle_root),
            "reviewer": "Daniela",
            "write_policy": "approval_package_only",
            "stages": ["01-plan"],
            "graph": prior_graph_payload,
        },
    )
    assert plan_response.status_code == 200
    plan_package_id = plan_response.json()["package_id"]
    prior_state_path = (
        bundle_root
        / ".uiplan"
        / "generation"
        / "packages"
        / plan_package_id
        / "approval-state.json"
    )
    prior_state = json.loads(prior_state_path.read_text(encoding="utf-8"))
    prior_state["stage_statuses"]["01-plan"] = "approved"
    prior_state_path.write_text(json.dumps(prior_state, indent=2) + "\n", encoding="utf-8")

    scaffold_response = client.post(
        "/generation/packages",
        json={
            "bundle_root": str(bundle_root),
            "reviewer": "Daniela",
            "write_policy": "approval_package_only",
            "stages": ["02-scaffold"],
            "graph": request_graph_payload,
        },
    )
    assert scaffold_response.status_code == 400
    detail = scaffold_response.json()["detail"].lower()
    assert "approved prior plan package" in detail
    assert "matching graph lineage" in detail


def test_generation_packages_list_and_detail_contract(monkeypatch, tmp_path) -> None:
    plans_root = tmp_path / "plans"
    bundle_root = plans_root / "example"
    bundle_root.mkdir(parents=True)
    monkeypatch.setattr(state, "PLANS_ROOT", plans_root.resolve())
    client = TestClient(app)

    create_response = client.post(
        "/generation/packages",
        json={
            "bundle_root": str(bundle_root),
            "reviewer": "Daniela",
            "write_policy": "approval_package_only",
            "stages": ["01-plan"],
            "graph": {
                "graph_id": "graph-list-detail",
                "bundle_root": str(bundle_root),
                "created_from": "test",
                "nodes": [
                    {
                        "id": "plan-node",
                        "title": "Plan Node",
                        "role": "process_step",
                        "output_type": "document",
                        "project_types": ["docs"],
                        "description": "Generate only plan proposal.",
                    }
                ],
                "edges": [],
                "context_attachments": [],
                "generation_profile": {"allowed_project_types": ["docs"]},
            },
        },
    )
    assert create_response.status_code == 200
    package_id = create_response.json()["package_id"]

    list_response = client.get(
        "/generation/packages",
        params={"bundle_root": str(bundle_root)},
    )
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert "packages" in list_payload
    assert isinstance(list_payload["packages"], list)
    assert any(pkg["package_id"] == package_id for pkg in list_payload["packages"])
    package_summary = next(pkg for pkg in list_payload["packages"] if pkg["package_id"] == package_id)
    assert package_summary["graph_id"] == "graph-list-detail"
    assert package_summary["generated_stages"] == ["01-plan"]
    assert package_summary["approval_state_path"] == "approval-state.json"

    detail_response = client.get(
        f"/generation/packages/{package_id}",
        params={"bundle_root": str(bundle_root)},
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert set(detail_payload) == {"manifest", "approval_state", "stages", "proposals"}
    assert detail_payload["manifest"]["package_id"] == package_id
    assert detail_payload["approval_state"]["package_id"] == package_id
    assert detail_payload["stages"][0]["stage_id"] == "01-plan"
    assert detail_payload["proposals"][0]["stage_id"] == "01-plan"
    assert detail_payload["proposals"][0]["target_path"] == "docs/uiplan-generation-plan.md"


def test_generation_package_approval_preview_and_apply_routes(monkeypatch, tmp_path) -> None:
    plans_root = tmp_path / "plans"
    bundle_root = plans_root / "example"
    bundle_root.mkdir(parents=True)
    monkeypatch.setattr(state, "PLANS_ROOT", plans_root.resolve())
    main._PENDING_GENERATION_PREVIEWS.clear()
    client = TestClient(app)

    graph_payload = {
        "graph_id": "graph-approval-routes",
        "bundle_root": str(bundle_root),
        "created_from": "test",
        "nodes": [
            {
                "id": "plan-node",
                "title": "Plan Node",
                "role": "process_step",
                "output_type": "document",
                "project_types": ["docs"],
                "description": "Generate plan proposal.",
            }
        ],
        "edges": [],
        "context_attachments": [],
        "generation_profile": {"allowed_project_types": ["docs"]},
    }
    create_response = client.post(
        "/generation/packages",
        json={
            "bundle_root": str(bundle_root),
            "reviewer": "Daniela",
            "write_policy": "approval_package_only",
            "stages": ["01-plan"],
            "graph": graph_payload,
        },
    )
    assert create_response.status_code == 200
    package_id = create_response.json()["package_id"]

    detail_response = client.get(
        f"/generation/packages/{package_id}",
        params={"bundle_root": str(bundle_root)},
    )
    assert detail_response.status_code == 200
    proposal_id = detail_response.json()["proposals"][0]["proposal_id"]

    preview_before_approval = client.post(
        f"/generation/packages/{package_id}/proposals/{proposal_id}/preview",
        json={"bundle_root": str(bundle_root)},
    )
    assert preview_before_approval.status_code == 200
    preview_id = preview_before_approval.json()["preview_id"]
    assert preview_before_approval.json()["target_path"] == "docs/uiplan-generation-plan.md"
    assert preview_before_approval.json()["proposal_id"] == proposal_id
    assert "--- docs/uiplan-generation-plan.md" in preview_before_approval.json()["diff"]

    apply_before_approval = client.post(
        f"/generation/packages/{package_id}/proposals/{proposal_id}/apply",
        json={"bundle_root": str(bundle_root), "preview_id": preview_id},
    )
    assert apply_before_approval.status_code == 409
    assert "approved" in apply_before_approval.json()["detail"].lower()

    approval_response = client.post(
        f"/generation/packages/{package_id}/approval",
        json={
            "bundle_root": str(bundle_root),
            "target": "proposal",
            "target_id": proposal_id,
            "next_status": "approved",
            "reviewer": "Daniela",
            "note": "Looks good",
        },
    )
    assert approval_response.status_code == 200
    assert (
        approval_response.json()["approval_state"]["proposals"][proposal_id]["review_status"]
        == "approved"
    )

    apply_after_approval = client.post(
        f"/generation/packages/{package_id}/proposals/{proposal_id}/apply",
        json={"bundle_root": str(bundle_root), "preview_id": preview_id},
    )
    assert apply_after_approval.status_code == 200
    assert (
        apply_after_approval.json()["approval_state"]["proposals"][proposal_id]["apply_status"]
        == "applied"
    )
    assert (bundle_root / "docs" / "uiplan-generation-plan.md").exists()


@pytest.mark.parametrize("stage_id", ["03-code", "04-tests", "05-validation"])
def test_generation_package_endpoint_rejects_deferred_stages(monkeypatch, tmp_path, stage_id) -> None:
    plans_root = tmp_path / "plans"
    bundle_root = plans_root / "example"
    bundle_root.mkdir(parents=True)
    monkeypatch.setattr(state, "PLANS_ROOT", plans_root.resolve())
    client = TestClient(app)

    response = client.post(
        "/generation/packages",
        json={
            "bundle_root": str(bundle_root),
            "reviewer": "Daniela",
            "write_policy": "approval_package_only",
            "stages": [stage_id],
            "graph": {
                "graph_id": f"graph-{stage_id}",
                "bundle_root": str(bundle_root),
                "created_from": "test",
                "nodes": [],
                "edges": [],
                "context_attachments": [],
                "generation_profile": {"allowed_project_types": ["docs"]},
            },
        },
    )

    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "deferred" in detail
    assert stage_id in detail


def test_generation_package_endpoint_rejects_deferred_stage(monkeypatch, tmp_path):
    plans_root = tmp_path / "plans"
    bundle_root = plans_root / "example"
    bundle_root.mkdir(parents=True)
    monkeypatch.setattr(state, "PLANS_ROOT", plans_root.resolve())

    client = TestClient(app)
    response = client.post(
        "/generation/packages",
        json={
            "bundle_root": str(bundle_root),
            "write_policy": "approval_package_only",
            "stages": ["03-code"],
            "graph": {
                "graph_id": "graph-api",
                "bundle_root": str(bundle_root),
                "created_from": "test",
                "nodes": [],
                "edges": [],
                "context_attachments": [],
                "generation_profile": {"allowed_project_types": ["docs"]},
            },
        },
    )

    assert response.status_code == 400
    assert "stage generation is deferred: 03-code" in response.json()["detail"]
