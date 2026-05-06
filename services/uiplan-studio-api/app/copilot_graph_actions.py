from copy import deepcopy


def execute_graph_action(action: str, payload: dict, workspace: dict) -> dict:
    next_workspace = deepcopy(workspace) if isinstance(workspace, dict) else {}
    next_workspace["nodes"] = list(next_workspace.get("nodes") or [])
    next_workspace["edges"] = list(next_workspace.get("edges") or [])

    if action == "add_node":
        node = payload.get("node") if isinstance(payload, dict) else None
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
