from dataclasses import dataclass, replace
from typing import Any, Optional

CORE_NODE_IDS = {"spec", "plan", "tasks", "skills", "library", "review"}


@dataclass(frozen=True)
class GraphNodeV2:
    id: str
    type: str
    title: str
    summary: str = ""
    code: Optional[dict[str, Any]] = None  # {"path": str, "lines": str, "snippet": str, "language": str}
    concept: Optional[str] = None  # plain-language explanation


@dataclass(frozen=True)
class GraphEdgeV2:
    id: str
    type: str
    source: str
    target: str
    label: str = ""


@dataclass(frozen=True)
class GraphWorkspaceV2:
    version: str
    nodes: tuple[GraphNodeV2, ...]
    edges: tuple[GraphEdgeV2, ...]

    def can_delete_node(self, node_id: str) -> bool:
        return node_id not in CORE_NODE_IDS


def new_graph_workspace() -> GraphWorkspaceV2:
    nodes = (
        GraphNodeV2(id="spec", type="doc", title="spec.md"),
        GraphNodeV2(id="plan", type="doc", title="plan.md"),
        GraphNodeV2(id="tasks", type="doc", title="tasks.md"),
        GraphNodeV2(id="skills", type="skill", title="Skills Context"),
        GraphNodeV2(id="library", type="book_section", title="Library Context"),
        GraphNodeV2(id="review", type="review_gate", title="Review Gate"),
    )
    return GraphWorkspaceV2(version="uiplan_graph.v2", nodes=nodes, edges=())


def update_node_title(workspace: GraphWorkspaceV2, node_id: str, title: str) -> GraphWorkspaceV2:
    nodes = tuple(
        replace(node, title=title) if node.id == node_id else node for node in workspace.nodes
    )
    return GraphWorkspaceV2(version=workspace.version, nodes=nodes, edges=workspace.edges)
