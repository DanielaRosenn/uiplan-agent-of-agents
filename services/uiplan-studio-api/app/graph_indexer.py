from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path

from app.code_extractor import parse_file_structure, generate_concept_explanation
from app.graph_workspace import GraphEdgeV2, GraphNodeV2, GraphWorkspaceV2, new_graph_workspace

CORE_DOC_NODE_IDS = {"spec", "plan", "tasks"}
MARKDOWN_SUFFIX = ".md"
SOURCE_SUFFIXES = {".py", ".ts", ".tsx"}
XAML_SUFFIX = ".xaml"
MAX_FILE_SIZE_BYTES = 500 * 1024  # 500KB


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

        if suffix in SOURCE_SUFFIXES or suffix == XAML_SUFFIX:
            # Check file size limit
            try:
                file_size = file_path.stat().st_size
                if file_size > MAX_FILE_SIZE_BYTES:
                    warnings.append(f"Skipping large file: {relative_path} ({file_size} bytes)")
                    continue
            except OSError as e:
                warnings.append(f"Could not stat file: {relative_path} - {e}")
                continue

            # Read file content
            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                warnings.append(f"Could not read file: {relative_path} - {e}")
                continue

            # Determine language
            language = _detect_language(suffix)
            
            # Parse file structure
            try:
                definitions = parse_file_structure(content, language=language)
            except Exception as e:
                warnings.append(f"Could not parse file: {relative_path} - {e}")
                definitions = []

            # Create nodes for each top-level definition
            for definition in definitions:
                node_id = _node_id(f"source-{definition.kind}", relative_path / definition.name)
                if node_id not in existing_node_ids:
                    # Extract code snippet
                    lines = content.splitlines()
                    snippet_lines = lines[definition.start_line - 1:definition.end_line]
                    snippet = "\n".join(snippet_lines)
                    
                    # Build code metadata
                    code_data = {
                        "path": relative_path.as_posix(),
                        "lines": f"{definition.start_line}-{definition.end_line}",
                        "snippet": snippet,
                        "language": language,
                    }
                    
                    # Generate concept explanation
                    node_data = {
                        "type": "source_file",
                        "title": relative_path.as_posix(),
                        "code": code_data,
                    }
                    concept = generate_concept_explanation(node_data, definition)
                    
                    # Create node with enhanced data
                    nodes.append(GraphNodeV2(
                        id=node_id,
                        type="source_file",
                        title=f"{relative_path.as_posix()}:{definition.name}",
                        summary=concept,
                        code=code_data,
                        concept=concept,
                    ))
                    existing_node_ids.add(node_id)

    return IndexResult(
        workspace=GraphWorkspaceV2(version=workspace.version, nodes=tuple(nodes), edges=tuple(edges)),
        warnings=tuple(warnings),
    )


def _detect_language(suffix: str) -> str:
    """Map file suffix to language identifier."""
    mapping = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".xaml": "xaml",
    }
    return mapping.get(suffix.lower(), "unknown")


def index_workspace_sources_with_warnings(root: Path) -> IndexResult:
    return _index_workspace_sources_with_warnings(root)


def index_workspace_sources(root: Path) -> GraphWorkspaceV2:
    return index_workspace_sources_with_warnings(root).workspace
