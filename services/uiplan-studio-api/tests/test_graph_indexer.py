from pathlib import Path

from app.graph_indexer import index_workspace_sources


def test_index_workspace_sources_detects_markdown_and_python(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "extra.md").write_text("# Extra\n", encoding="utf-8")
    (tmp_path / "agent.py").write_text("print('hello')\n", encoding="utf-8")

    workspace = index_workspace_sources(tmp_path)

    indexed_nodes = {(node.title, node.type) for node in workspace.nodes}
    assert ("docs/extra.md", "doc") in indexed_nodes
    # Note: The new implementation creates nodes per function/class, not per file
    # So we won't see "agent.py" directly, but any functions/classes within it


def test_index_workspace_sources_extracts_code_snippets(tmp_path: Path) -> None:
    """Integration test: verify code snippets are extracted from real project files."""
    # Create a Python file with functions
    python_file = tmp_path / "utils.py"
    python_code = """def calculate_total(items):
    return sum(items)

class DataProcessor:
    def process(self, data):
        return data
"""
    python_file.write_text(python_code, encoding="utf-8")
    
    # Create a TypeScript file
    ts_file = tmp_path / "helper.ts"
    ts_code = """export function formatName(name: string): string {
    return name.toUpperCase();
}

export class Validator {
    validate(input: string) {
        return input.length > 0;
    }
}
"""
    ts_file.write_text(ts_code, encoding="utf-8")
    
    # Index the workspace
    workspace = index_workspace_sources(tmp_path)
    
    # Find Python function node
    python_func_nodes = [n for n in workspace.nodes if "calculate_total" in n.title]
    assert len(python_func_nodes) == 1
    func_node = python_func_nodes[0]
    
    # Verify node has code data
    assert func_node.code is not None
    assert func_node.code["language"] == "python"
    assert func_node.code["path"] == "utils.py"
    assert "calculate_total" in func_node.code["snippet"]
    assert func_node.code["lines"] == "1-2"
    
    # Verify concept explanation exists
    assert func_node.concept is not None
    assert "function" in func_node.concept.lower()
    assert "calculate_total" in func_node.concept
    
    # Find Python class node
    python_class_nodes = [n for n in workspace.nodes if "DataProcessor" in n.title]
    assert len(python_class_nodes) == 1
    class_node = python_class_nodes[0]
    
    assert class_node.code is not None
    assert class_node.code["language"] == "python"
    assert "DataProcessor" in class_node.code["snippet"]
    assert class_node.concept is not None
    assert "class" in class_node.concept.lower()
    
    # Find TypeScript function node
    ts_func_nodes = [n for n in workspace.nodes if "formatName" in n.title]
    assert len(ts_func_nodes) == 1
    ts_func_node = ts_func_nodes[0]
    
    assert ts_func_node.code is not None
    assert ts_func_node.code["language"] == "typescript"
    assert ts_func_node.code["path"] == "helper.ts"
    assert "formatName" in ts_func_node.code["snippet"]
    
    # Find TypeScript class node
    ts_class_nodes = [n for n in workspace.nodes if "Validator" in n.title]
    assert len(ts_class_nodes) == 1
    ts_class_node = ts_class_nodes[0]
    
    assert ts_class_node.code is not None
    assert ts_class_node.code["language"] == "typescript"
    assert "Validator" in ts_class_node.code["snippet"]


def test_index_workspace_sources_handles_large_files(tmp_path: Path) -> None:
    """Verify large files are skipped with warning."""
    # Create a large file (>500KB)
    large_file = tmp_path / "large.py"
    large_content = "# Large file\n" * 50000  # ~700KB
    large_file.write_text(large_content, encoding="utf-8")
    
    from app.graph_indexer import index_workspace_sources_with_warnings
    result = index_workspace_sources_with_warnings(tmp_path)
    
    # Should have warning about large file
    assert any("large.py" in w and "large file" in w.lower() for w in result.warnings)


def test_index_workspace_sources_handles_parse_errors(tmp_path: Path) -> None:
    """Verify files with syntax errors are handled gracefully."""
    # Create a Python file with syntax error
    bad_file = tmp_path / "broken.py"
    bad_file.write_text("def bad syntax here\n", encoding="utf-8")
    
    from app.graph_indexer import index_workspace_sources_with_warnings
    result = index_workspace_sources_with_warnings(tmp_path)
    
    # Should have warning about parse error (or just no nodes for this file)
    # The indexer should not crash
    assert result.workspace is not None

