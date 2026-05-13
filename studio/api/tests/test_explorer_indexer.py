"""Tests for `app.explorer_indexer`: file scan, edge inference, XAML invokes."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.explorer_config import ExplorerConfig, IndexingSpec, ProjectSpec
from app.explorer_indexer import index_project


def _write(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _config(scan: dict[str, list[str]], project_type: str = "mixed") -> ExplorerConfig:
    return ExplorerConfig(
        project=ProjectSpec(name="fixture", type=project_type),
        indexing=IndexingSpec(scan={k: tuple(v) for k, v in scan.items()}),
    )


def test_index_empty_project_returns_empty_result(tmp_path: Path) -> None:
    config = _config({"ui": ["src/**/*.tsx"]})
    result = index_project(tmp_path, config)
    assert result.nodes == []
    assert result.edges == []
    assert result.files_scanned == 0


def test_index_python_files_creates_nodes_and_internal_imports(tmp_path: Path) -> None:
    _write(tmp_path / "agent" / "graph.py", "from agent.personas import ba_persona\n")
    _write(tmp_path / "agent" / "personas.py", "def ba_persona():\n    return 1\n")
    _write(tmp_path / "agent" / "__init__.py", "")
    config = _config({"agent": ["agent/**/*.py"]})
    result = index_project(tmp_path, config)

    ids = {n["id"] for n in result.nodes}
    assert any("graph.py" in n["label"] for n in result.nodes)
    assert any("personas.py" in n["label"] for n in result.nodes)
    # Internal import edge present
    assert any(e["kind"] == "import" for e in result.edges), \
        f"expected import edge, got {result.edges}"
    # Layer is propagated
    assert all(n["layer"] == "agent" for n in result.nodes)
    # No duplicate ids
    assert len(ids) == len(result.nodes)


def test_index_python_external_imports_become_external_nodes(tmp_path: Path) -> None:
    _write(tmp_path / "agent" / "main.py", "import boto3\nimport openai\n")
    config = _config({"agent": ["agent/**/*.py"]})
    result = index_project(tmp_path, config)

    external_ids = {n["id"] for n in result.nodes if n["layer"] == "external"}
    assert "ext:aws" in external_ids
    assert "ext:openai" in external_ids
    # Edges from main.py to each external
    call_targets = {e["target"] for e in result.edges if e["kind"] == "call"}
    assert "ext:aws" in call_targets
    assert "ext:openai" in call_targets


def test_index_xaml_extracts_invokes_and_emits_edges(tmp_path: Path) -> None:
    _write(tmp_path / "Main.xaml", """
<Activity>
  <Sequence>
    <InvokeWorkflowFile WorkflowFileName="GetCommitmentData.xaml" />
    <InvokeWorkflowFile WorkflowFileName="RequestApproval.xaml" />
  </Sequence>
</Activity>
""")
    _write(tmp_path / "GetCommitmentData.xaml", "<Activity />\n")
    _write(tmp_path / "RequestApproval.xaml", "<Activity />\n")
    config = _config({"rpa": ["**/*.xaml"]}, project_type="rpa")
    result = index_project(tmp_path, config)

    main = next(n for n in result.nodes if n["label"] == "Main.xaml")
    assert main["kind"] == "workflow"
    # Children are populated for the workflow node
    assert "children" in main
    assert len(main["children"]["nodes"]) == 2
    # Top-level invoke edges resolve to the sibling files
    invokes = [e for e in result.edges if e["kind"] == "invokes"]
    invoke_targets = {next((n["label"] for n in result.nodes if n["id"] == e["target"]), None) for e in invokes}
    assert "GetCommitmentData.xaml" in invoke_targets
    assert "RequestApproval.xaml" in invoke_targets


def test_index_excludes_respected(tmp_path: Path) -> None:
    _write(tmp_path / "agent" / "good.py", "x = 1\n")
    _write(tmp_path / "node_modules" / "lib" / "bad.py", "x = 1\n")
    config = ExplorerConfig(
        project=ProjectSpec(name="x", type="mixed"),
        indexing=IndexingSpec(
            scan={"agent": ("**/*.py",)},
            exclude=("node_modules/**",),
        ),
    )
    result = index_project(tmp_path, config)
    labels = {n["label"] for n in result.nodes}
    assert "good.py" in labels
    assert "bad.py" not in labels


def test_index_typescript_relative_imports_resolve(tmp_path: Path) -> None:
    _write(tmp_path / "src" / "App.tsx",
           'import { CheckoutForm } from "./CheckoutForm";\nexport const App = () => null;\n')
    _write(tmp_path / "src" / "CheckoutForm.tsx",
           'export const CheckoutForm = () => null;\n')
    config = _config({"ui": ["src/**/*.tsx"]})
    result = index_project(tmp_path, config)
    import_edges = [e for e in result.edges if e["kind"] == "import"]
    assert len(import_edges) == 1
    targets = {e["target"] for e in import_edges}
    sources = {e["source"] for e in import_edges}
    label_for = {n["id"]: n["label"] for n in result.nodes}
    assert "App.tsx" in {label_for[s] for s in sources}
    assert "CheckoutForm.tsx" in {label_for[t] for t in targets}
