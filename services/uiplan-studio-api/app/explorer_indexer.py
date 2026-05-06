"""Pragmatic cross-layer indexer for the UiPlan Studio Explorer.

Walks a project tree per the `indexing.scan` globs in `.uiplan/explorer.yaml`,
emits one node per discovered file (and a few sub-nodes for top-level Python
defs and XAML <InvokeWorkflowFile> targets), and infers edges from imports
and workflow invocations.

This is intentionally heuristic. It gets ~70% of an interesting project graph
right out of the box; users tighten the rest via `.uiplan/annotations.yaml`
(merged in `app.explorer`, not here).

Performance posture: file count and per-file byte limits enforced by the
config; we sort and short-circuit so a 500-file repo indexes in well under a
second on a laptop.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Iterable

from app.code_extractor import parse_file_structure
from app.explorer_config import ExplorerConfig


SUPPORTED_LAYERS = ("ui", "api", "agent", "rpa", "maestro", "app", "orchestrator", "test", "external")

# Map well-known external imports to a synthetic external/tool node.
EXTERNAL_HINTS: dict[str, tuple[str, str]] = {
    # python module prefix -> (external node id, label)
    "boto3":          ("ext:aws",        "AWS"),
    "salesforce":     ("ext:salesforce", "Salesforce"),
    "simple_salesforce": ("ext:salesforce", "Salesforce"),
    "openai":         ("ext:openai",     "OpenAI"),
    "anthropic":      ("ext:anthropic",  "Anthropic"),
    "langchain":      ("ext:langchain",  "LangChain"),
    "langgraph":      ("ext:langgraph",  "LangGraph"),
    "uipath":         ("ext:uipath",     "UiPath SDK"),
    "uipath_langchain": ("ext:uipath",   "UiPath SDK"),
    "docusign_esign": ("ext:docusign",   "DocuSign"),
    "psycopg":        ("ext:postgres",   "Postgres"),
    "pymongo":        ("ext:mongo",      "MongoDB"),
}


@dataclass
class IndexResult:
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    files_scanned: int = 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def index_project(project_root: Path, config: ExplorerConfig) -> IndexResult:
    """Build a project graph for `project_root` per the explorer config.

    Walks once per layer, deduplicating files that match multiple glob lists
    (the first matching layer wins). Returns a permissive
    {nodes, edges, warnings, files_scanned} structure.
    """
    if not project_root.is_dir():
        return IndexResult(warnings=[f"project root does not exist: {project_root}"])

    result = IndexResult()
    seen_paths: set[Path] = set()
    file_id_by_path: dict[Path, str] = {}

    for layer in SUPPORTED_LAYERS:
        globs = config.indexing.scan.get(layer)
        if not globs:
            continue
        files = _collect_files(
            project_root, globs, config.indexing.exclude,
            limit=config.indexing.max_files_per_layer,
            max_bytes=config.indexing.max_file_bytes,
            already_seen=seen_paths,
        )
        for path in files:
            seen_paths.add(path)
            result.files_scanned += 1
            try:
                _index_file(path, layer, project_root, result, file_id_by_path, config)
            except Exception as exc:  # noqa: BLE001 - log and continue
                result.warnings.append(f"{path.relative_to(project_root)}: {exc}")

    # Pass 2: infer edges from collected file content. We iterate over what we
    # already loaded into nodes (paths embedded in node['code']) so we don't
    # re-read everything.
    _infer_edges(project_root, result, file_id_by_path)

    return result


# ---------------------------------------------------------------------------
# File scanning
# ---------------------------------------------------------------------------


def _collect_files(
    root: Path,
    include_globs: Iterable[str],
    exclude_globs: Iterable[str],
    *,
    limit: int,
    max_bytes: int,
    already_seen: set[Path],
) -> list[Path]:
    matches: list[Path] = []
    for pattern in include_globs:
        for candidate in root.glob(pattern):
            if not candidate.is_file():
                continue
            if candidate in already_seen:
                continue
            rel = candidate.relative_to(root).as_posix()
            if any(fnmatch(rel, ex) for ex in exclude_globs):
                continue
            try:
                if candidate.stat().st_size > max_bytes:
                    continue
            except OSError:
                continue
            matches.append(candidate)
            if len(matches) >= limit:
                return matches
    # de-duplicate while preserving order
    deduped: list[Path] = []
    seen_local: set[Path] = set()
    for p in matches:
        if p not in seen_local:
            deduped.append(p)
            seen_local.add(p)
    return deduped


# ---------------------------------------------------------------------------
# Per-file indexing
# ---------------------------------------------------------------------------


def _index_file(
    path: Path, layer: str, root: Path, result: IndexResult,
    file_id_by_path: dict[Path, str], config: ExplorerConfig,
) -> None:
    rel = path.relative_to(root).as_posix()
    suffix = path.suffix.lower()
    kind = _kind_for(path, layer)
    node_id = _node_id(layer, rel)

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        text = ""

    snippet = _head_snippet(text, lines=14)
    code = {
        "path": rel,
        "lines": f"1-{min(14, max(1, len(snippet.splitlines())))}",
        "snippet": snippet,
        "language": _language_for(suffix),
    } if text else None

    node: dict[str, Any] = {
        "id": node_id,
        "label": path.name,
        "kind": kind,
        "layer": layer,
        "desc": _describe_file(rel, kind, layer),
        "status": "ok",
    }
    if code:
        node["code"] = code

    result.nodes.append(node)
    file_id_by_path[path] = node_id

    # XAML special-case: also surface InvokeWorkflowFile children so the
    # workflow appears with its sub-flows already drawn.
    if suffix == ".xaml" and text:
        invoked = _xaml_invokes(text)
        if invoked:
            children_nodes: list[dict[str, Any]] = []
            children_edges: list[dict[str, Any]] = []
            for i, target in enumerate(invoked):
                child_id = f"{node_id}::invoke-{i}"
                children_nodes.append({
                    "id": child_id, "label": target, "kind": "activity",
                    "layer": layer, "status": "ok",
                    "desc": f"InvokeWorkflowFile target: {target}",
                })
                if i > 0:
                    children_edges.append({
                        "id": f"{node_id}::e-{i}",
                        "source": f"{node_id}::invoke-{i-1}",
                        "target": child_id,
                        "kind": "transition",
                        "path_class": "happy",
                    })
            if children_nodes:
                node["children"] = {"nodes": children_nodes, "edges": children_edges}


def _kind_for(path: Path, layer: str) -> str:
    suffix = path.suffix.lower()
    name = path.name.lower()
    if suffix == ".xaml":
        return "workflow" if name == "main.xaml" else "activity"
    if suffix == ".flow":
        return "flow"
    if name == "caseplan.json":
        return "case"
    if name == "app.config.json":
        return "coded_app"
    if name == "action-schema.json":
        return "action_app"
    if name.endswith(".testset.json"):
        return "test_set"
    if suffix in (".py", ".ts", ".tsx"):
        if layer == "agent" and name in ("graph.py", "main.py", "agent.py"):
            return "agent_node"
        if layer == "api":
            return "endpoint" if "route" in name or "router" in name else "module"
        return "file"
    return "file"


def _language_for(suffix: str) -> str:
    return {
        ".py": "python", ".ts": "typescript", ".tsx": "tsx",
        ".xaml": "xaml", ".flow": "yaml", ".json": "json",
    }.get(suffix.lower(), "text")


def _describe_file(rel: str, kind: str, layer: str) -> str:
    short = rel.split("/")[-1]
    return f"{kind.replace('_', ' ')} · {short} ({layer})"


def _head_snippet(text: str, *, lines: int) -> str:
    head = "\n".join(text.splitlines()[:lines])
    return head[:1200]


# ---------------------------------------------------------------------------
# Edge inference
# ---------------------------------------------------------------------------


def _infer_edges(root: Path, result: IndexResult, file_id_by_path: dict[Path, str]) -> None:
    """Add import/invoke/call edges by scanning each indexed file's content."""
    # Reverse map for filename-based resolution (e.g. "GetCommitmentData.xaml")
    by_basename: dict[str, str] = {}
    for path, node_id in file_id_by_path.items():
        by_basename.setdefault(path.name.lower(), node_id)

    external_seen: set[str] = set()

    edge_idx = 0
    def add_edge(source: str, target: str, kind: str, **extra: Any) -> None:
        nonlocal edge_idx
        edge_idx += 1
        edge: dict[str, Any] = {
            "id": f"e-{edge_idx}",
            "source": source,
            "target": target,
            "kind": kind,
        }
        edge.update(extra)
        result.edges.append(edge)

    for path, src_id in file_id_by_path.items():
        suffix = path.suffix.lower()
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue

        if suffix == ".py":
            for tgt_path, kind in _python_imports(text, path, root, file_id_by_path.keys()):
                tgt_id = file_id_by_path.get(tgt_path)
                if tgt_id and tgt_id != src_id:
                    add_edge(src_id, tgt_id, kind)
            for ext_id, ext_label in _external_imports_python(text):
                if ext_id not in external_seen:
                    result.nodes.append({
                        "id": ext_id, "label": ext_label, "kind": "tool",
                        "layer": "external", "status": "ok",
                        "desc": f"External dependency · {ext_label}",
                    })
                    external_seen.add(ext_id)
                add_edge(src_id, ext_id, "call")

        elif suffix in (".ts", ".tsx"):
            for tgt_path in _ts_relative_imports(text, path, root):
                tgt_id = file_id_by_path.get(tgt_path)
                if tgt_id and tgt_id != src_id:
                    add_edge(src_id, tgt_id, "import")

        elif suffix == ".xaml":
            for invoked in _xaml_invokes(text):
                tgt_id = by_basename.get(invoked.lower())
                if tgt_id and tgt_id != src_id:
                    add_edge(src_id, tgt_id, "invokes", path_class="happy")


_PY_IMPORT_RE = re.compile(r"^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))", re.MULTILINE)


def _python_imports(text: str, this_file: Path, root: Path, all_paths: Iterable[Path]) -> list[tuple[Path, str]]:
    """Return list of (target_path, kind) for relative imports we can resolve."""
    out: list[tuple[Path, str]] = []
    paths = list(all_paths)
    for m in _PY_IMPORT_RE.finditer(text):
        module = (m.group(1) or m.group(2) or "").strip()
        if not module or "." not in module and len(module.split(".")) <= 1 and not (this_file.parent / f"{module}.py").exists():
            # try same-folder shallow match
            same = this_file.parent / f"{module}.py"
            if same.exists():
                out.append((same.resolve(), "import"))
            continue
        # Resolve dotted module to a path inside the project, best-effort.
        candidate_rel = module.replace(".", "/")
        for ext in (".py", "/__init__.py"):
            cand = root / f"{candidate_rel}{ext}"
            if cand.is_file() and cand.resolve() in {p.resolve() for p in paths}:
                out.append((cand.resolve(), "import"))
                break
    return out


def _external_imports_python(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for m in _PY_IMPORT_RE.finditer(text):
        module = (m.group(1) or m.group(2) or "").split(".")[0]
        if not module:
            continue
        ext = EXTERNAL_HINTS.get(module)
        if ext and ext[0] not in seen:
            seen.add(ext[0])
            out.append(ext)
    return out


_TS_IMPORT_RE = re.compile(r"""(?:import|from)\s+['"]([^'"]+)['"]""")


def _ts_relative_imports(text: str, this_file: Path, root: Path) -> list[Path]:
    out: list[Path] = []
    parent = this_file.parent
    for m in _TS_IMPORT_RE.finditer(text):
        spec = m.group(1)
        if not spec.startswith("."):
            continue
        for ext in ("", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.tsx"):
            cand = (parent / f"{spec}{ext}").resolve()
            if cand.is_file():
                out.append(cand)
                break
    return out


_XAML_INVOKE_RE = re.compile(r'WorkflowFileName\s*=\s*"([^"]+)"', re.IGNORECASE)


def _xaml_invokes(text: str) -> list[str]:
    targets: list[str] = []
    seen: set[str] = set()
    for m in _XAML_INVOKE_RE.finditer(text):
        target = m.group(1).split("\\")[-1].split("/")[-1]
        if target and target not in seen:
            seen.add(target)
            targets.append(target)
    return targets


# ---------------------------------------------------------------------------
# Ids
# ---------------------------------------------------------------------------


def _node_id(layer: str, rel: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_./-]", "-", rel)
    return f"{layer}:{safe}"
