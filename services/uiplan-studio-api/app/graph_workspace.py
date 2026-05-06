from dataclasses import dataclass

CORE_NODE_IDS = {"spec", "plan", "tasks", "skills", "library", "review"}


@dataclass
class GraphNodeV2:
    id: str
    type: str
    title: str
    summary: str = ""


@dataclass
class GraphEdgeV2:
    id: str
    type: str
    source: str
    target: str
    label: str = ""


@dataclass
class GraphWorkspaceV2:
    version: str
    nodes: list[GraphNodeV2]
    edges: list[GraphEdgeV2]

    def can_delete_node(self, node_id: str) -> bool:
        return node_id not in CORE_NODE_IDS


def new_graph_workspace() -> GraphWorkspaceV2:
    core_node_order = ["spec", "plan", "tasks", "skills", "library", "review"]
    nodes = [
        GraphNodeV2(id=node_id, type="core", title=node_id.capitalize()) for node_id in core_node_order
    ]
    return GraphWorkspaceV2(version="uiplan_graph.v2", nodes=nodes, edges=[])


def update_node_title(workspace: GraphWorkspaceV2, node_id: str, title: str) -> GraphWorkspaceV2:
    for node in workspace.nodes:
        if node.id == node_id:
            node.title = title
            break
    return workspace
