from pathlib import Path

from app.graph_indexer import index_workspace_sources


def test_index_workspace_sources_detects_markdown_and_python(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (tmp_path / "agent.py").write_text("print('hello')\n", encoding="utf-8")

    workspace = index_workspace_sources(tmp_path)

    node_types = {node.type for node in workspace.nodes}
    assert "doc" in node_types
    assert "source_file" in node_types
