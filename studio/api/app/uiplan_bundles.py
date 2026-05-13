"""Scan a project for UiPlan bundle artefacts and emit explorer nodes.

A UiPlan bundle is the trio of `spec.md` / `plan.md` / `tasks.md`. We find them
in three places:

  1. Top-level: `<project>/spec.md`, `<project>/plan.md`, `<project>/tasks.md`.
  2. Cursor plans: `<project>/.cursor/plans/*.md`.
  3. Superpowers plans: `<project>/docs/superpowers/plans/*.md`.
  4. Nested UiPlan bundles: any directory that contains a `.meta.yaml` plus
     at least one of the trio (e.g. `docs/uiplan/<slug>/`).

For each `tasks.md` we parse markdown checkboxes:

    - [ ] pending
    - [x] done
    - [-] cancelled
    - [ ] something **IN_PROGRESS**

and surface per-task children plus an aggregate progress summary on the
parent file node.

Additionally, if .uiplan/explorer.yaml contains a `views` section, we emit
`uiplan_view_as_is` and `uiplan_view_to_be` child nodes for stakeholder-facing
AS-IS (manual process) and TO-BE (automated solution) canvases.

This module is intentionally side-effect free; `app.explorer` calls
`collect_uiplan_nodes` once per `/explorer/graph` request and merges the
result alongside the regular indexer output.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

UIPLAN_LAYER = "uiplan"
BUNDLE_FILES = ("spec.md", "plan.md", "tasks.md")
# Surface draft plan files as mini-bundles so explorer users can browse
# accepted and in-progress planning documents even when they are single-file.
# Keep the globs narrow to avoid pulling unrelated markdown docs into the rail.
PLAN_GLOBS: tuple[str, ...] = (
    ".cursor/plans/*.md",
    "docs/superpowers/plans/*.md",
)
# Directories which, if they contain any of the bundle files, are treated as
# nested UiPlan bundles. The presence of `.meta.yaml` is preferred (provides a
# slug) but not required.
NESTED_BUNDLE_PARENT_GLOBS = (
    "docs/uiplan/*",
    ".uiplan/bundles/*",
    ".cursor/plans/*",
    "docs/superpowers/plans/*",
)
MAX_FILE_BYTES = 256_000
MAX_TASKS_PER_FILE = 200
MAX_SNIPPET_LINES = 24

_CHECKBOX_RE = re.compile(r"^\s*[-*+]\s*\[(?P<mark>[ xX\-~])\]\s*(?P<text>.+?)\s*$")
_HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<text>.+?)\s*$")
_IN_PROGRESS_RE = re.compile(r"\b(IN[_ ]?PROGRESS|WIP)\b", re.IGNORECASE)


@dataclass(frozen=True)
class TaskItem:
    line: int
    text: str
    status: str  # "done" | "pending" | "cancelled" | "in_progress"
    section: str | None = None


@dataclass
class TaskSummary:
    total: int = 0
    done: int = 0
    pending: int = 0
    in_progress: int = 0
    cancelled: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "total": self.total,
            "done": self.done,
            "pending": self.pending,
            "in_progress": self.in_progress,
            "cancelled": self.cancelled,
        }


@dataclass
class UiplanCollectResult:
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def collect_uiplan_nodes(project_root: Path, indexed_graph: dict[str, Any] | None = None, overview_actors: list[Any] | None = None) -> UiplanCollectResult:
    """Return UiPlan nodes/edges for the given project root.

    The root bundle (top-level spec/plan/tasks) is grouped under a synthetic
    `uiplan:bundle:root` parent. Each additional plan file or nested bundle
    becomes its own parent so the explorer can show them side by side.
    
    If indexed_graph and overview_actors are provided, also emits AS-IS and
    TO-BE view nodes based on .uiplan/explorer.yaml::views configuration.
    """
    result = UiplanCollectResult()
    if not project_root.is_dir():
        return result

    root = project_root.resolve()

    # 1. Root bundle (spec/plan/tasks at the project root).
    root_files = _existing_bundle_files(root)
    if root_files:
        _emit_bundle(
            result,
            bundle_id="uiplan:bundle:root",
            label="UiPlan Bundle",
            desc="Root spec / plan / tasks for this project.",
            bundle_root=root,
            files=root_files,
            project_root=root,
            indexed_graph=indexed_graph,
            overview_actors=overview_actors,
        )

    # 2. Cursor + superpowers plan files (each treated as its own mini-bundle).
    for pattern in PLAN_GLOBS:
        for path in sorted(root.glob(pattern)):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            bundle_id = f"uiplan:plan:{_safe(rel)}"
            _emit_bundle(
                result,
                bundle_id=bundle_id,
                label=path.name,
                desc=f"Plan document · {rel}",
                bundle_root=path.parent,
                files=[path],
                project_root=root,
                indexed_graph=indexed_graph,
                overview_actors=overview_actors,
            )

    # 3. Nested UiPlan bundles (subdirs containing bundle files).
    seen_dirs: set[Path] = set()
    for pattern in NESTED_BUNDLE_PARENT_GLOBS:
        for bundle_dir in sorted(root.glob(pattern)):
            if not bundle_dir.is_dir():
                continue
            bundle_dir = bundle_dir.resolve()
            if bundle_dir in seen_dirs or bundle_dir == root:
                continue
            files = _existing_bundle_files(bundle_dir)
            if not files:
                continue
            seen_dirs.add(bundle_dir)
            rel_dir = bundle_dir.relative_to(root).as_posix()
            bundle_id = f"uiplan:bundle:{_safe(rel_dir)}"
            meta_path = bundle_dir / ".meta.yaml"
            slug = _read_meta_slug(meta_path) if meta_path.is_file() else None
            _emit_bundle(
                result,
                bundle_id=bundle_id,
                label=slug or bundle_dir.name,
                desc=f"UiPlan bundle · {rel_dir}",
                bundle_root=bundle_dir,
                files=files,
                project_root=root,
                indexed_graph=indexed_graph,
                overview_actors=overview_actors,
            )

    return result


# ---------------------------------------------------------------------------
# Bundle emission
# ---------------------------------------------------------------------------


def _emit_bundle(
    result: UiplanCollectResult,
    *,
    bundle_id: str,
    label: str,
    desc: str,
    bundle_root: Path,
    files: list[Path],
    project_root: Path,
    indexed_graph: dict[str, Any] | None = None,
    overview_actors: list[Any] | None = None,
) -> None:
    child_nodes: list[dict[str, Any]] = []
    child_edges: list[dict[str, Any]] = []
    aggregate = TaskSummary()
    file_nodes_for_canvas: list[dict[str, Any]] = []

    for path in files:
        file_node, file_summary, task_children = _build_file_node(
            path=path, project_root=project_root, parent_id=bundle_id,
        )
        file_nodes_for_canvas.append(file_node)
        # Children-of-bundle: file node, with tasks nested under it.
        bundled_file_node = dict(file_node)
        if task_children:
            bundled_file_node["children"] = {"nodes": task_children, "edges": []}
        child_nodes.append(bundled_file_node)
        if file_summary is not None:
            aggregate.total += file_summary.total
            aggregate.done += file_summary.done
            aggregate.pending += file_summary.pending
            aggregate.in_progress += file_summary.in_progress
            aggregate.cancelled += file_summary.cancelled

    # Add AS-IS and TO-BE view nodes if config exists
    if indexed_graph is not None and overview_actors is not None:
        try:
            from .view_resolver import load_views_config, resolve_as_is, resolve_to_be
            from .explorer_config import ActorSpec
            
            views_spec = load_views_config(project_root)
            
            # Convert overview_actors to ActorSpec list
            actor_specs = []
            for actor in (overview_actors or []):
                if isinstance(actor, ActorSpec):
                    actor_specs.append(actor)
                elif isinstance(actor, dict):
                    actor_specs.append(ActorSpec(
                        name=actor.get("name", ""),
                        role=actor.get("role", "")
                    ))
            
            # AS-IS view
            try:
                as_is_view = resolve_as_is(project_root, views_spec, actor_specs)
                as_is_node: dict[str, Any] = {
                    "id": f"{bundle_id}::view-as-is",
                    "label": "AS-IS (Manual Process)",
                    "kind": "uiplan_view_as_is",
                    "layer": UIPLAN_LAYER,
                    "desc": "How work happens today, manually — actors, handoffs, channels, pain points.",
                    "status": "ok",
                    "meta": {"view": as_is_view.to_dict()},
                }
                child_nodes.append(as_is_node)
            except Exception:
                # Silently skip if AS-IS view can't be resolved
                pass
            
            # TO-BE view
            try:
                to_be_view = resolve_to_be(project_root, views_spec, indexed_graph)
                to_be_node: dict[str, Any] = {
                    "id": f"{bundle_id}::view-to-be",
                    "label": "TO-BE (Automated Solution)",
                    "kind": "uiplan_view_to_be",
                    "layer": UIPLAN_LAYER,
                    "desc": "Automated solution architecture — workflows, integrations, HITL, evidence.",
                    "status": "ok",
                    "meta": {"view": to_be_view.to_dict()},
                }
                child_nodes.append(to_be_node)
            except Exception:
                # Silently skip if TO-BE view can't be resolved
                pass
        except ImportError:
            # view_resolver not available, skip views
            pass

    summary_meta: dict[str, Any] = {}
    if aggregate.total > 0:
        summary_meta = {
            "tasks_total": aggregate.total,
            "tasks_done": aggregate.done,
            "tasks_pending": aggregate.pending,
            "tasks_in_progress": aggregate.in_progress,
            "tasks_cancelled": aggregate.cancelled,
        }

    bundle_node: dict[str, Any] = {
        "id": bundle_id,
        "label": label,
        "kind": "uiplan_bundle",
        "layer": UIPLAN_LAYER,
        "desc": desc,
        "status": "ok",
        "children": {"nodes": child_nodes, "edges": []},
    }
    if summary_meta:
        bundle_node["meta"] = summary_meta
        bundle_node["task_summary"] = aggregate.to_dict()
    result.nodes.append(bundle_node)

    # Also surface the file nodes at the top level so they're directly
    # selectable on the canvas without drilling into the bundle.
    for fn in file_nodes_for_canvas:
        result.nodes.append(fn)
        result.edges.append({
            "id": f"e:{bundle_id}->{fn['id']}",
            "source": bundle_id,
            "target": fn["id"],
            "kind": "data",
            "path_class": "happy",
        })


def _build_file_node(
    *, path: Path, project_root: Path, parent_id: str,
) -> tuple[dict[str, Any], TaskSummary | None, list[dict[str, Any]]]:
    rel = _safe_relpath(path, project_root)
    text = _safe_read(path)
    snippet = "\n".join(text.splitlines()[:MAX_SNIPPET_LINES])

    name = path.name.lower()
    is_tasks = name == "tasks.md" or name.endswith(".plan.md")
    kind = "uiplan_tasks" if is_tasks else "uiplan_doc"

    file_id = f"uiplan:file:{_safe(rel)}"
    node: dict[str, Any] = {
        "id": file_id,
        "label": path.name,
        "kind": kind,
        "layer": UIPLAN_LAYER,
        "desc": _file_desc(path.name),
        "status": "ok",
        "code": {
            "path": rel,
            "lines": f"1-{min(MAX_SNIPPET_LINES, max(1, len(snippet.splitlines())))}",
            "snippet": snippet,
            "language": "markdown",
        },
        "meta": {"parent_bundle": parent_id, "full_path": rel},
    }
    # Always attach the full body for the inspector markdown renderer.
    node["meta"]["body"] = text[: MAX_FILE_BYTES]

    if not is_tasks:
        return node, None, []

    tasks = _parse_tasks(text)
    summary = _summarise(tasks)
    node["meta"].update(summary.to_dict_with_prefix("tasks_"))
    node["task_summary"] = summary.to_dict()
    if summary.total > 0:
        # Encode percent-done into status so the colored pip means something.
        if summary.done == summary.total:
            node["status"] = "ok"
        elif summary.in_progress > 0:
            node["status"] = "warn"
        else:
            node["status"] = "draft"

    children = [
        {
            "id": f"{file_id}::task-{i}",
            "label": _truncate(t.text, 80),
            "kind": "uiplan_task",
            "layer": UIPLAN_LAYER,
            "desc": (t.section or "task"),
            "status": _task_status_to_node_status(t.status),
            "meta": {
                "task_status": t.status,
                "task_line": t.line,
                "task_section": t.section or "",
                "source_file": rel,
            },
        }
        for i, t in enumerate(tasks[:MAX_TASKS_PER_FILE])
    ]
    return node, summary, children


# ---------------------------------------------------------------------------
# Markdown task parser
# ---------------------------------------------------------------------------


def _parse_tasks(text: str) -> list[TaskItem]:
    tasks: list[TaskItem] = []
    section: str | None = None
    for idx, raw in enumerate(text.splitlines(), start=1):
        h = _HEADING_RE.match(raw)
        if h:
            section = h.group("text").strip()
            continue
        m = _CHECKBOX_RE.match(raw)
        if not m:
            continue
        mark = m.group("mark")
        body = m.group("text").strip()
        status = _classify(mark, body)
        tasks.append(TaskItem(line=idx, text=body, status=status, section=section))
    return tasks


def _classify(mark: str, body: str) -> str:
    if mark in ("x", "X"):
        return "done"
    if mark in ("-", "~"):
        return "cancelled"
    if _IN_PROGRESS_RE.search(body):
        return "in_progress"
    return "pending"


def _summarise(tasks: Iterable[TaskItem]) -> TaskSummary:
    s = TaskSummary()
    for t in tasks:
        s.total += 1
        if t.status == "done":
            s.done += 1
        elif t.status == "in_progress":
            s.in_progress += 1
        elif t.status == "cancelled":
            s.cancelled += 1
        else:
            s.pending += 1
    return s


def _task_status_to_node_status(status: str) -> str:
    return {
        "done": "ok",
        "in_progress": "warn",
        "cancelled": "stale",
    }.get(status, "draft")


# Attach a helper directly to TaskSummary for serialisation with a prefix.
def _summary_to_dict_with_prefix(self: TaskSummary, prefix: str) -> dict[str, int]:
    return {f"{prefix}{k}": v for k, v in self.to_dict().items()}


TaskSummary.to_dict_with_prefix = _summary_to_dict_with_prefix  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _existing_bundle_files(root: Path) -> list[Path]:
    return [p for name in BUNDLE_FILES if (p := root / name).is_file()]


def _safe_read(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return path.read_text(encoding="utf-8", errors="ignore")[:MAX_FILE_BYTES]
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _safe_relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _safe(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_./-]", "-", s)


def _truncate(s: str, n: int) -> str:
    s = s.strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def _file_desc(filename: str) -> str:
    name = filename.lower()
    if name == "spec.md":
        return "Specification — what is being built and why."
    if name == "plan.md":
        return "Implementation plan."
    if name == "tasks.md":
        return "Task checklist with done / pending status."
    return f"UiPlan document · {filename}"


def _read_meta_slug(meta_path: Path) -> str | None:
    try:
        for line in meta_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("slug:"):
                return stripped.split(":", 1)[1].strip().strip('"').strip("'")
    except OSError:
        return None
    return None
