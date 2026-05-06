import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.project_graph.templates import (
    STARTER_PROJECT_GRAPH_TEMPLATE_METADATA,
    create_starter_project_graph_template,
)

STARTER_TEMPLATE_CONTRACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "test-fixtures"
    / "project-graph"
    / "starter-template-contract.json"
)
STARTER_TEMPLATE_CONTRACT = json.loads(
    STARTER_TEMPLATE_CONTRACT_PATH.read_text(encoding="utf-8")
)


def assert_no_null_values(value: Any) -> None:
    if isinstance(value, dict):
        for child in value.values():
            assert_no_null_values(child)
        return
    if isinstance(value, list):
        for child in value:
            assert_no_null_values(child)
        return
    assert value is not None


def test_starter_project_graph_template_helper_returns_normalized_graph() -> None:
    graph = create_starter_project_graph_template()
    nodes_by_id = {node.id: node for node in graph.nodes}

    assert graph.projectType == "solution"
    assert graph.errors == []
    assert list(nodes_by_id) == STARTER_TEMPLATE_CONTRACT["nodeIds"]
    assert nodes_by_id["planning_agent"].kind == "project_component"
    assert nodes_by_id["planning_agent"].metadata["visualRole"] == "central_action"
    assert nodes_by_id["if_ready"].kind == "review_gate"
    assert nodes_by_id["if_ready"].metadata["visualRole"] == "decision_branch"
    assert all(node.metadata["source"] == "projectGraph.starterTemplate" for node in graph.nodes)

    edge_signatures = [
        [edge.source, edge.target, edge.kind, edge.label]
        for edge in graph.edges
    ]
    assert edge_signatures == STARTER_TEMPLATE_CONTRACT["edgeSignatures"]


def test_starter_project_graph_template_metadata_describes_visual_layout() -> None:
    metadata = STARTER_PROJECT_GRAPH_TEMPLATE_METADATA

    assert metadata["id"] == "visual-template"
    assert metadata["nodeCount"] == STARTER_TEMPLATE_CONTRACT["metadata"]["nodeCount"]
    assert set(STARTER_TEMPLATE_CONTRACT["metadata"]["tags"]).issubset(metadata["tags"])
    assert (
        metadata["recommendedLayout"]["direction"]
        == STARTER_TEMPLATE_CONTRACT["metadata"]["layoutDirection"]
    )
    assert "context" in metadata["recommendedLayout"]["layers"]
    for node_id, icon_hint in STARTER_TEMPLATE_CONTRACT["metadata"]["iconHints"].items():
        assert metadata["iconHints"][node_id] == icon_hint


def test_starter_project_graph_template_endpoint_returns_metadata_and_graph() -> None:
    client = TestClient(app)
    response = client.get("/project-graph/templates/starter")

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["id"] == "visual-template"
    assert payload["metadata"]["nodeCount"] == STARTER_TEMPLATE_CONTRACT["metadata"]["nodeCount"]
    assert [node["id"] for node in payload["graph"]["nodes"]] == STARTER_TEMPLATE_CONTRACT["nodeIds"]
    assert payload["graph"]["errors"] == []


def test_starter_project_graph_template_endpoint_omits_nested_null_fields() -> None:
    client = TestClient(app)
    response = client.get("/project-graph/templates/starter")

    assert response.status_code == 200
    payload = response.json()
    assert_no_null_values(payload["graph"])
    for edge in payload["graph"]["edges"]:
        if edge["id"] in {
            "chat_trigger:drives:planning_agent",
            "planning_agent:uses_context:context_library",
        }:
            assert "label" not in edge


def test_starter_project_graph_template_matches_shared_parity_contract() -> None:
    graph = create_starter_project_graph_template()
    node_kinds = {
        node.id: node.kind
        for node in graph.nodes
        if node.id in STARTER_TEMPLATE_CONTRACT["nodeKinds"]
    }
    edge_signatures = [
        [edge.source, edge.target, edge.kind, edge.label]
        for edge in graph.edges
    ]

    assert STARTER_PROJECT_GRAPH_TEMPLATE_METADATA["id"] == STARTER_TEMPLATE_CONTRACT["metadata"]["id"]
    assert node_kinds == STARTER_TEMPLATE_CONTRACT["nodeKinds"]
    assert edge_signatures == STARTER_TEMPLATE_CONTRACT["edgeSignatures"]
