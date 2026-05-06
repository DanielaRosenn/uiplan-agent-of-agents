from app.graph_workspace import (
    CORE_NODE_IDS,
    GraphEdgeV2,
    GraphNodeV2,
    GraphWorkspaceV2,
    new_graph_workspace,
    update_node_title,
)


def test_new_workspace_contains_core_nodes() -> None:
    workspace = new_graph_workspace()

    assert workspace.version == "uiplan_graph.v2"
    assert {node.id for node in workspace.nodes} == CORE_NODE_IDS
    assert workspace.edges == []


def test_core_node_cannot_be_deleted() -> None:
    workspace = GraphWorkspaceV2(
        version="uiplan_graph.v2",
        nodes=[GraphNodeV2(id="spec", type="document", title="Spec")],
        edges=[GraphEdgeV2(id="e1", type="link", source="spec", target="plan")],
    )

    assert workspace.can_delete_node("spec") is False
    assert workspace.can_delete_node("custom") is True


def test_update_node_title_mutates_non_core_node() -> None:
    custom_node = GraphNodeV2(id="n1", type="workflow", title="Old title")
    workspace = GraphWorkspaceV2(
        version="uiplan_graph.v2",
        nodes=[custom_node],
        edges=[],
    )

    updated = update_node_title(workspace, "n1", "New title")

    assert updated is workspace
    assert workspace.nodes[0].title == "New title"
