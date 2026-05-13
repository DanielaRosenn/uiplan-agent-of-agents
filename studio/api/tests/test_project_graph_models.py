import json
from pathlib import Path

from app.project_graph.models import (
    ProjectGraph,
    ProjectGraphAdapterInput,
    ProjectGraphCluster,
    ProjectGraphEdge,
    ProjectGraphIssue,
    ProjectGraphNode,
)
from app.project_graph import ProjectGraph as ExportedProjectGraph

GOLDEN_GRAPH_PATH = (
    Path(__file__).resolve().parents[3] / "test-fixtures" / "project-graph" / "golden.json"
)


def test_project_graph_defaults_arrays_and_metadata() -> None:
    graph = ProjectGraph(
        projectType="docs",
        nodes=[ProjectGraphNode(id="plan", label="Plan", kind="generated_artifact", layer="artifact")],
        edges=[],
    )

    assert graph.clusters == []
    assert graph.errors == []
    assert graph.nodes[0].metadata == {}


def test_project_graph_serializes_camel_case_contract() -> None:
    graph = ProjectGraph(
        projectType="solution",
        nodes=[ProjectGraphNode(id="intake", label="Customer Intake", kind="process_step")],
        edges=[],
        errors=[
            ProjectGraphIssue(
                id="missing-context",
                message="Strict context is missing.",
                severity="warning",
                targetId="intake",
            )
        ],
    )

    payload = graph.model_dump()

    assert payload["projectType"] == "solution"
    assert payload["nodes"][0]["metadata"] == {}
    assert payload["errors"][0]["targetId"] == "intake"


def test_project_graph_omits_optional_null_fields_from_serialized_contract() -> None:
    graph = ProjectGraph(
        projectType="docs",
        nodes=[ProjectGraphNode(id="plan", label="Plan", kind="generated_artifact", layer=None)],
        edges=[ProjectGraphEdge(id="plan-review", source="plan", target="review", kind="documents")],
        clusters=[ProjectGraphCluster(id="docs", label="Docs", nodeIds=["plan"], kind=None)],
        errors=[
            ProjectGraphIssue(
                id="note",
                message="Advisory only.",
                severity="note",
                targetId=None,
            )
        ],
    )

    payload = graph.model_dump()

    assert "layer" not in payload["nodes"][0]
    assert "label" not in payload["edges"][0]
    assert "kind" not in payload["clusters"][0]
    assert "targetId" not in payload["errors"][0]


def test_project_graph_json_omits_optional_null_fields_from_serialized_contract() -> None:
    graph = ProjectGraph(
        projectType="docs",
        nodes=[ProjectGraphNode(id="plan", label="Plan", kind="generated_artifact", layer=None)],
        edges=[ProjectGraphEdge(id="plan-review", source="plan", target="review", kind="documents")],
        clusters=[ProjectGraphCluster(id="docs", label="Docs", nodeIds=["plan"], kind=None)],
        errors=[
            ProjectGraphIssue(
                id="note",
                message="Advisory only.",
                severity="note",
                targetId=None,
            )
        ],
    )

    payload = json.loads(graph.model_dump_json())

    assert "layer" not in payload["nodes"][0]
    assert "label" not in payload["edges"][0]
    assert "kind" not in payload["clusters"][0]
    assert "targetId" not in payload["errors"][0]


def test_project_graph_preserves_dangling_references_with_diagnostics() -> None:
    graph = ProjectGraph(
        projectType="solution",
        nodes=[ProjectGraphNode(id="intake", label="Customer Intake", kind="process_step")],
        edges=[ProjectGraphEdge(id="intake-agent", source="intake", target="agent", kind="drives")],
        clusters=[ProjectGraphCluster(id="automation", label="Automation", nodeIds=["intake", "agent"])],
    )

    assert graph.errors == [
        ProjectGraphIssue(
            id="edge:intake-agent:missing-target",
            message="Edge target references missing node 'agent'.",
            severity="warning",
            targetId="intake-agent",
            metadata={"source": "projectGraph.normalize"},
        ),
        ProjectGraphIssue(
            id="cluster:automation:missing-member:agent",
            message="Cluster member references missing node 'agent'.",
            severity="warning",
            targetId="automation",
            metadata={"source": "projectGraph.normalize"},
        ),
    ]


def test_project_graph_matches_shared_golden_json_fixture() -> None:
    fixture = json.loads(GOLDEN_GRAPH_PATH.read_text(encoding="utf-8"))
    graph = ProjectGraph.model_validate(fixture)

    assert graph.model_dump() == fixture


def test_project_graph_adapter_input_accepts_arbitrary_source_payload() -> None:
    adapter_input = ProjectGraphAdapterInput(
        projectType="coded-agent",
        source={"graph_id": "generation-graph-1", "nodes": []},
        context={"bundleRoot": ".cursor/plans/example"},
    )

    assert adapter_input.projectType == "coded-agent"
    assert adapter_input.source["graph_id"] == "generation-graph-1"
    assert adapter_input.context == {"bundleRoot": ".cursor/plans/example"}


def test_project_graph_package_exports_public_contract() -> None:
    assert ExportedProjectGraph is ProjectGraph
