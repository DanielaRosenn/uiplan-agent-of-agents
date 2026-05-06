from copy import deepcopy


def _normalize_workspace(workspace: dict) -> dict:
    next_workspace = deepcopy(workspace) if isinstance(workspace, dict) else {}
    next_workspace["version"] = str(next_workspace.get("version") or "uiplan_graph.v2")
    next_workspace["nodes"] = list(next_workspace.get("nodes") or [])
    next_workspace["edges"] = list(next_workspace.get("edges") or [])
    return next_workspace


def _resolve_add_node_payload(payload: dict) -> dict | None:
    if not isinstance(payload, dict):
        return None
    node = payload.get("node")
    if isinstance(node, dict):
        return node
    if payload.get("id") is not None:
        return payload
    return None


def execute_graph_action(action: str, payload: dict, workspace: dict) -> dict:
    next_workspace = _normalize_workspace(workspace)

    if action == "add_node":
        node = _resolve_add_node_payload(payload)
        if isinstance(node, dict):
            next_workspace["nodes"].append(deepcopy(node))
            node_id = node.get("id", "unknown")
            return {"message": f"Added node {node_id}.", "workspace": next_workspace}
        return {"message": "No node provided for add_node.", "workspace": next_workspace}

    if action == "explain_node":
        node = payload.get("node") if isinstance(payload, dict) else None
        node_id = "unknown"
        if isinstance(node, dict):
            node_id = str(node.get("id", "unknown"))
        elif isinstance(payload, dict) and "node_id" in payload:
            node_id = str(payload["node_id"])
        return {"message": f"Node {node_id} is ready for review.", "workspace": next_workspace}

    return {"message": f"Unsupported action: {action}", "workspace": next_workspace}
