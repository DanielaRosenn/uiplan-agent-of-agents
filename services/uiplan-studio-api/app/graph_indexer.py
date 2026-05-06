from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path

from app.graph_workspace import GraphEdgeV2, GraphNodeV2, GraphWorkspaceV2, new_graph_workspace

CORE_DOC_NODE_IDS = {"spec", "plan", "tasks"}
MARKDOWN_SUFFIX = ".md"
SOURCE_SUFFIXES = {".py", ".ts", ".tsx"}


@dataclass(frozen=True)
class IndexResult:
    workspace: GraphWorkspaceV2
    warnings: tuple[str, ...]


def _node_id(prefix: str, relative_path: Path) -> str:
    digest = sha1(relative_path.as_posix().encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def _index_workspace_sources_with_warnings(root: Path) -> IndexResult:
    workspace = new_graph_workspace()
    nodes = list(workspace.nodes)
    edges = list(workspace.edges)
    warnings: list[str] = []

    if not root.exists() or not root.is_dir():
        warnings.append(f"Workspace root does not exist: {root}")
        return IndexResult(
            workspace=GraphWorkspaceV2(version=workspace.version, nodes=tuple(nodes), edges=tuple(edges)),
            warnings=tuple(warnings),
        )

    existing_node_ids = {node.id for node in nodes}
    existing_edge_ids = {edge.id for edge in edges}

    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        relative_path = file_path.relative_to(root)
        suffix = file_path.suffix.lower()

        if suffix == MARKDOWN_SUFFIX:
            if relative_path.as_posix() in {"spec.md", "plan.md", "tasks.md"}:
                continue
            node_id = _node_id("doc", relative_path)
            if node_id not in existing_node_ids:
                nodes.append(GraphNodeV2(id=node_id, type="doc", title=relative_path.as_posix()))
                existing_node_ids.add(node_id)
            edge_id = f"context-{node_id}-plan"
            if edge_id not in existing_edge_ids:
                edges.append(
                    GraphEdgeV2(
                        id=edge_id,
                        type="context",
                        source=node_id,
                        target="plan",
                        label="context",
                    )
                )
                existing_edge_ids.add(edge_id)
            continue

        if suffix in SOURCE_SUFFIXES:
            node_id = _node_id("source", relative_path)
            if node_id not in existing_node_ids:
                nodes.append(GraphNodeV2(id=node_id, type="source_file", title=relative_path.as_posix()))
                existing_node_ids.add(node_id)

    return IndexResult(
        workspace=GraphWorkspaceV2(version=workspace.version, nodes=tuple(nodes), edges=tuple(edges)),
        warnings=tuple(warnings),
    )


def index_workspace_sources(root: Path) -> GraphWorkspaceV2:
    return _index_workspace_sources_with_warnings(root).workspace
