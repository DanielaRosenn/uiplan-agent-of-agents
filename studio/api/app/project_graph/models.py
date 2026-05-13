from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

ProjectGraphProjectType = Literal[
    "rpa",
    "coded-automation",
    "coded-agent",
    "maestro-flow",
    "coded-app",
    "coded-action-app",
    "api-workflow",
    "solution",
    "library",
    "test",
    "docs",
    "platform-resource",
]
ProjectGraphNodeKind = Literal[
    "process_step",
    "project_component",
    "generated_artifact",
    "test",
    "tool",
    "asset",
    "queue",
    "docs_context",
    "skill",
    "deployment_gate",
    "review_gate",
]
ProjectGraphEdgeKind = Literal[
    "drives",
    "generates",
    "depends_on",
    "uses_context",
    "uses_skill",
    "validates",
    "blocks",
    "deploys",
    "observes",
    "documents",
]
ProjectGraphIssueSeverity = Literal["error", "warning", "note"]
ProjectGraphMetadata = dict[str, Any]


class ProjectGraphBaseModel(BaseModel):
    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(*args, **kwargs)

    def model_dump_json(self, *args: Any, **kwargs: Any) -> str:
        kwargs.setdefault("exclude_none", True)
        return super().model_dump_json(*args, **kwargs)


class ProjectGraphNode(ProjectGraphBaseModel):
    id: str
    label: str
    kind: ProjectGraphNodeKind
    layer: str | None = None
    metadata: ProjectGraphMetadata = Field(default_factory=dict)


class ProjectGraphEdge(ProjectGraphBaseModel):
    id: str
    source: str
    target: str
    kind: ProjectGraphEdgeKind
    label: str | None = None
    metadata: ProjectGraphMetadata = Field(default_factory=dict)


class ProjectGraphCluster(ProjectGraphBaseModel):
    id: str
    label: str
    nodeIds: list[str] = Field(default_factory=list)
    kind: str | None = None
    metadata: ProjectGraphMetadata = Field(default_factory=dict)


class ProjectGraphIssue(ProjectGraphBaseModel):
    id: str
    message: str
    severity: ProjectGraphIssueSeverity
    targetId: str | None = None
    metadata: ProjectGraphMetadata = Field(default_factory=dict)


class ProjectGraph(ProjectGraphBaseModel):
    projectType: ProjectGraphProjectType
    nodes: list[ProjectGraphNode] = Field(default_factory=list)
    edges: list[ProjectGraphEdge] = Field(default_factory=list)
    clusters: list[ProjectGraphCluster] = Field(default_factory=list)
    errors: list[ProjectGraphIssue] = Field(default_factory=list)

    @model_validator(mode="after")
    def add_reference_diagnostics(self) -> "ProjectGraph":
        diagnostics = find_reference_diagnostics(self)
        existing_issue_ids = {issue.id for issue in self.errors}
        self.errors.extend(
            diagnostic for diagnostic in diagnostics if diagnostic.id not in existing_issue_ids
        )
        return self


class ProjectGraphAdapterInput(ProjectGraphBaseModel):
    projectType: ProjectGraphProjectType
    source: Any
    context: ProjectGraphMetadata = Field(default_factory=dict)


class ProjectGraphAdapterResult(ProjectGraphBaseModel):
    graph: ProjectGraph
    issues: list[ProjectGraphIssue] = Field(default_factory=list)


def find_reference_diagnostics(graph: ProjectGraph) -> list[ProjectGraphIssue]:
    node_ids = {node.id for node in graph.nodes}
    diagnostics: list[ProjectGraphIssue] = []

    for edge in graph.edges:
        if edge.source not in node_ids:
            diagnostics.append(create_missing_edge_node_issue(edge.id, "source", edge.source))
        if edge.target not in node_ids:
            diagnostics.append(create_missing_edge_node_issue(edge.id, "target", edge.target))

    for cluster in graph.clusters:
        for node_id in cluster.nodeIds:
            if node_id not in node_ids:
                diagnostics.append(
                    ProjectGraphIssue(
                        id=f"cluster:{cluster.id}:missing-member:{node_id}",
                        message=f"Cluster member references missing node '{node_id}'.",
                        severity="warning",
                        targetId=cluster.id,
                        metadata={"source": "projectGraph.normalize"},
                    )
                )

    return diagnostics


def create_missing_edge_node_issue(
    edge_id: str,
    endpoint: Literal["source", "target"],
    node_id: str,
) -> ProjectGraphIssue:
    return ProjectGraphIssue(
        id=f"edge:{edge_id}:missing-{endpoint}",
        message=f"Edge {endpoint} references missing node '{node_id}'.",
        severity="warning",
        targetId=edge_id,
        metadata={"source": "projectGraph.normalize"},
    )
