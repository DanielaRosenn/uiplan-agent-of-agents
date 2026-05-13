"""Project Explorer API surface.

Exposes endpoints consumed by `studio/web` (the project explorer):

  GET /explorer/worktrees                    -> list real worktrees / projects
  GET /explorer/graph?worktree=<id>          -> structured project graph
  GET /explorer/knowledge?node=&q=&worktree= -> ranked library citations + skills
  GET /explorer/library/section?book=&...    -> full body of a single library section

These routes serve the project-wide explorer view used by
`studio/web` and follow a permissive schema (status, BA fields,
recursive children, edge metadata, etc.).

Skills + library are read through the official internal modules so this stays
in sync with `uipath_skill_*` / `uipath_library_*` MCP tools.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Iterable

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.explorer_config import (
    ANNOTATIONS_FILENAME,
    CONFIG_DIRNAME,
    CONFIG_FILENAME,
    ExplorerConfig,
    ExplorerConfigError,
    load_config,
    render_starter_config,
)
from app.explorer_indexer import index_project
from app.explorer_skills import (
    aggregate_skill_graph_context,
    match_skills_for_query,
    read_skill_detail,
)
from app.library_service import search_library_context
from app.schemas import LibraryContextItem
from app.uiplan_bundles import collect_uiplan_nodes


# Optional yaml — already a dependency, but importing here keeps the read of
# annotations.yaml encapsulated.
import yaml


def _ensure_framework_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    framework_dir = repo_root / "framework"
    if str(framework_dir) not in sys.path:
        sys.path.insert(0, str(framework_dir))


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ExplorerWorktree(BaseModel):
    id: str
    label: str
    path: str
    branch: str | None = None
    project_type: str | None = None


class ExplorerWorktreesResponse(BaseModel):
    items: list[ExplorerWorktree] = Field(default_factory=list)
    source: str = "filesystem"


class ExplorerCitation(BaseModel):
    book_id: str
    chapter_id: str
    section_id: str
    snippet: str
    score: int | None = None


class ExplorerSkill(BaseModel):
    id: str
    path: str
    reason: str | None = None
    origin: str | None = None
    score: int | None = None
    tags: list[str] = Field(default_factory=list)
    triggers: list[str] = Field(default_factory=list)


class ExplorerKnowledgeResponse(BaseModel):
    citations: list[ExplorerCitation] = Field(default_factory=list)
    skills: list[ExplorerSkill] = Field(default_factory=list)


class ExplorerLibrarySectionResponse(BaseModel):
    book_id: str
    chapter_id: str
    section_id: str
    title: str | None = None
    body: str


class ExplorerSkillDetailResponse(BaseModel):
    id: str
    description: str = ""
    path: str = ""
    origin: str | None = None
    tags: list[str] = Field(default_factory=list)
    triggers: list[str] = Field(default_factory=list)
    body: str = ""


# Project graph schema is exposed as a permissive dict because the frontend
# extends the shape continuously; we serialise whatever the producer emitted.
class ExplorerGraphResponse(BaseModel):
    projectType: str = "unknown"
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    overview: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None


class ExplorerRefreshStateResponse(BaseModel):
    worktree_id: str
    stamp: str | None = None
    source_count: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _list_worktrees() -> list[ExplorerWorktree]:
    """Return whatever git worktrees the host repo has plus the repo itself.

    The CLI 'git worktree list --porcelain' output is parsed; on any failure
    we return just the repo root so the dropdown is never empty.
    """
    import subprocess

    repo = _repo_root()
    items: list[ExplorerWorktree] = [
        ExplorerWorktree(
            id="repo-root",
            label=f"{repo.name} (root)",
            path=str(repo),
            branch=_safe_git_branch(repo),
            project_type=_detect_project_type(repo),
        )
    ]

    try:
        out = subprocess.check_output(
            ["git", "worktree", "list", "--porcelain"],
            cwd=str(repo),
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return items

    current: dict[str, str] = {}
    for line in out.splitlines() + [""]:
        if not line.strip():
            if current and current.get("worktree") and current["worktree"] != str(repo):
                wt_path = Path(current["worktree"])
                items.append(
                    ExplorerWorktree(
                        id=wt_path.name or current["worktree"],
                        label=wt_path.name,
                        path=current["worktree"],
                        branch=current.get("branch", "").replace("refs/heads/", "") or None,
                        project_type=_detect_project_type(wt_path),
                    )
                )
            current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    return items


def _safe_git_branch(path: Path) -> str | None:
    import subprocess

    try:
        return subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"],
            text=True, stderr=subprocess.DEVNULL, timeout=2,
        ).strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _detect_project_type(path: Path) -> str:
    """Best-effort project-type detection per CLAUDE.md §1.

    Order matters: more specific markers (Solution, Maestro Case, Coded App)
    are checked before generic ones (RPA `project.json`).
    """
    if not path.is_dir():
        return "unknown"
    # Multi-project containers first.
    if (path / "solution.uipx").exists():
        return "solution"
    # Coded paradigms (Python).
    if (path / "langgraph.json").exists():
        return "langgraph"
    if (path / "agent_framework.json").exists():
        return "coded-agent"
    if (path / "llama_index.json").exists():
        return "llama-index"
    # Low-code / Studio Web paradigms.
    if (path / "agent.json").exists():
        return "low-code-agent"
    if (path / "caseplan.json").exists():
        return "case"
    if (path / "api-workflow.json").exists():
        return "api-workflow"
    if (path / "app.config.json").exists() or (path / "action-schema.json").exists():
        return "coded-app"
    # Maestro: BPMN under a Studio Web project.
    if any(path.glob("*.bpmn")) or any(path.glob("**/*.bpmn")):
        return "maestro"
    # RPA: classic / coded automation projects.
    if any(path.glob("*.uiproj")) or (path / "project.json").exists():
        return "rpa"
    return "unknown"


def _allowed_worktree_roots() -> list[Path]:
    """Return the union of paths the `/explorer/graph` endpoint may index.

    By default this is the repo root plus any registered git worktrees.
    Operators can extend with `UIPATH_EXPLORER_ROOTS` (`os.pathsep`-separated
    absolute paths) to allow indexing projects outside this checkout.
    """
    import os

    roots: list[Path] = [_repo_root().resolve()]
    for wt in _list_worktrees():
        try:
            roots.append(Path(wt.path).resolve())
        except (OSError, ValueError):
            continue
    extra = os.environ.get("UIPATH_EXPLORER_ROOTS", "")
    for raw in extra.split(os.pathsep):
        raw = raw.strip()
        if not raw:
            continue
        try:
            roots.append(Path(raw).resolve())
        except (OSError, ValueError):
            continue
    # Deduplicate while preserving order.
    seen: set[str] = set()
    deduped: list[Path] = []
    for root in roots:
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(root)
    return deduped


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _resolve_project_path(worktree: str) -> tuple[Path, str, str | None]:
    items = {wt.id: wt for wt in _list_worktrees()}
    if worktree in items:
        wt = items[worktree]
        return Path(wt.path).resolve(), wt.id, wt.branch

    candidate = Path(worktree)
    if not candidate.is_absolute():
        candidate = (_repo_root() / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if not candidate.is_dir():
        raise HTTPException(status_code=404, detail=f"unknown worktree: {worktree}")
    allowed = _allowed_worktree_roots()
    if not any(_is_within(candidate, root) for root in allowed):
        raise HTTPException(
            status_code=403,
            detail=(
                "worktree path is not in the allow-list. Set UIPATH_EXPLORER_ROOTS "
                "(os.pathsep-separated absolute paths) to opt in."
            ),
        )
    return candidate, candidate.name or worktree, _safe_git_branch(candidate)


def _plan_refresh_sources(project_path: Path) -> list[Path]:
    sources: list[Path] = []
    marker = project_path / ".uiplan" / "studio-refresh.json"
    if marker.is_file():
        sources.append(marker)
    for root in (project_path / ".cursor" / "plans", project_path / "docs" / "plans"):
        if not root.is_dir():
            continue
        for pattern in ("spec.md", "plan.md", "tasks.md", "*.md"):
            sources.extend(path for path in root.glob(f"**/{pattern}") if path.is_file())
    deduped: dict[str, Path] = {}
    for source in sources:
        deduped[str(source.resolve())] = source
    return list(deduped.values())


def _plan_refresh_stamp(project_path: Path) -> tuple[str | None, int]:
    mtimes: list[float] = []
    for source in _plan_refresh_sources(project_path):
        try:
            mtimes.append(source.stat().st_mtime)
        except OSError:
            continue
    if not mtimes:
        return None, 0
    return str(max(mtimes)), len(mtimes)


def _to_citation(item: LibraryContextItem) -> ExplorerCitation:
    return ExplorerCitation(
        book_id=item.book_id,
        chapter_id=item.chapter_id,
        section_id=item.section_id,
        snippet=item.snippet,
        score=item.score,
    )


def _match_skills(query: str, top_k: int = 5) -> list[ExplorerSkill]:
    """Rank registered skills against a free-form query."""
    matches = match_skills_for_query(_repo_root(), query, top_k=top_k)
    return [
        ExplorerSkill(
            id=m.id,
            path=m.path,
            reason=m.reason,
            origin=m.origin,
            score=m.score,
            tags=list(m.tags),
            triggers=list(m.triggers),
        )
        for m in matches
    ]


def _read_library_section(book_id: str, chapter_id: str, section_id: str) -> str | None:
    _ensure_framework_on_path()
    try:
        from uipath_claude.library.catalog import LibraryCatalog
        from uipath_claude.library.reader import LibraryReader
    except Exception:
        return None
    try:
        catalog = LibraryCatalog.load()
        reader = LibraryReader(catalog=catalog)
        return reader.read_section(book_id, chapter_id, section_id)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


router = APIRouter(prefix="/explorer", tags=["explorer"])


@router.get("/worktrees", response_model=ExplorerWorktreesResponse)
def list_worktrees() -> ExplorerWorktreesResponse:
    return ExplorerWorktreesResponse(items=_list_worktrees(), source="filesystem")


@router.get("/refresh-state", response_model=ExplorerRefreshStateResponse)
def get_refresh_state(worktree: str = Query("repo-root")) -> ExplorerRefreshStateResponse:
    project_path, wt_id, _ = _resolve_project_path(worktree)
    stamp, source_count = _plan_refresh_stamp(project_path)
    return ExplorerRefreshStateResponse(
        worktree_id=wt_id,
        stamp=stamp,
        source_count=source_count,
    )


@router.get("/graph", response_model=ExplorerGraphResponse)
def get_project_graph(worktree: str = Query("repo-root")) -> ExplorerGraphResponse:
    """Return a structured project graph for the requested worktree.

    Resolution order for `worktree`:
      1. Match a registered worktree id (from `git worktree list` or the
         repo root). The corresponding path is indexed.
      2. Treat the value as a filesystem path (absolute or relative to repo
         root) and index it directly. Useful when the explorer is invoked
         via `uipath-claude explore` from inside a project that isn't a
         registered worktree.
    """
    project_path, wt_id, wt_branch = _resolve_project_path(worktree)

    try:
        config = load_config(project_path)
    except ExplorerConfigError as exc:
        raise HTTPException(status_code=400, detail=f"explorer.yaml invalid: {exc}") from exc

    index = index_project(project_path, config)
    annotations = _load_annotations(project_path)

    nodes = _apply_annotations(index.nodes, annotations.get("nodes") or {})
    skill_nodes, skill_edges = aggregate_skill_graph_context(_repo_root(), nodes)

    # Pass indexed graph and actors to enable AS-IS/TO-BE view emission
    indexed_graph = {"nodes": nodes, "edges": index.edges}
    overview_actors = list(config.overview.actors) if config.overview.actors else []
    uiplan = collect_uiplan_nodes(project_path, indexed_graph=indexed_graph, overview_actors=overview_actors)

    nodes = [*nodes, *skill_nodes, *uiplan.nodes]
    edges = [*index.edges, *skill_edges, *uiplan.edges]
    errors = [{"nodeId": w.split(":", 1)[0] if ":" in w else "indexer", "severity": "warn", "message": w}
              for w in index.warnings[:10]]

    overview = _build_overview_payload(config)

    return ExplorerGraphResponse(
        projectType=config.project.type,
        nodes=nodes,
        edges=edges,
        errors=errors,
        overview=overview,
        meta={
            "worktree_id": wt_id,
            "branch": wt_branch,
            "project_type": config.project.type,
            "config_source": config.source_path,
            "files_scanned": index.files_scanned,
            "skills_indexed": len(skill_nodes),
            "uiplan_bundles": sum(1 for n in uiplan.nodes if n.get("kind") == "uiplan_bundle"),
        },
    )


def _build_overview_payload(config: ExplorerConfig) -> dict[str, Any]:
    """Translate ExplorerConfig overview into the frontend ProjectOverview shape."""
    o = config.overview
    payload: dict[str, Any] = {
        "name": config.project.name,
        "summary": o.summary,
    }
    if config.project.owner:
        payload["owner"] = config.project.owner
    if o.stakeholders:
        payload["stakeholders"] = list(o.stakeholders)
    if o.triggers:
        payload["triggers"] = [{"kind": t.kind, "description": t.description} for t in o.triggers]
    if o.actors:
        payload["actors"] = [{"name": a.name, "role": a.role} for a in o.actors]
    if o.kpis:
        payload["kpis"] = [{"label": k.label, "value": k.value} for k in o.kpis]
    if config.project.pdd:
        payload["pdd"] = {"doc_id": config.project.name, "section": "PDD", "path": config.project.pdd}
    return payload


def _load_annotations(project_root: Path) -> dict[str, Any]:
    """Read `.uiplan/annotations.yaml` if it exists. Returns empty dict on any failure."""
    path = project_root / CONFIG_DIRNAME / ANNOTATIONS_FILENAME
    if not path.is_file():
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}
    return raw if isinstance(raw, dict) else {}


def _apply_annotations(
    nodes: list[dict[str, Any]],
    annotations: dict[str, Any],
) -> list[dict[str, Any]]:
    """Merge `.uiplan/annotations.yaml` overrides onto indexed nodes."""
    out: list[dict[str, Any]] = []
    for node in nodes:
        ann = annotations.get(node["id"]) or {}
        if isinstance(ann, dict):
            merged = dict(node)
            for key in ("status", "business_status", "desc", "concept", "roles",
                        "business_meta", "pdd_anchor", "skills", "citations"):
                if key in ann:
                    merged[key] = ann[key]
            out.append(merged)
        else:
            out.append(node)
    return out


# ---------------------------------------------------------------------------
# Bootstrap endpoint — used by `uipath-claude explore --init`
# ---------------------------------------------------------------------------


class ExplorerInitRequest(BaseModel):
    project_dir: str


class ExplorerInitResponse(BaseModel):
    config_path: str
    created: bool


@router.post("/init", response_model=ExplorerInitResponse)
def explorer_init(payload: ExplorerInitRequest) -> ExplorerInitResponse:
    project_path = Path(payload.project_dir)
    if not project_path.is_absolute():
        project_path = (_repo_root() / project_path).resolve()
    if not project_path.is_dir():
        raise HTTPException(status_code=404, detail=f"project_dir not found: {project_path}")

    config_dir = project_path / CONFIG_DIRNAME
    config_path = config_dir / CONFIG_FILENAME
    if config_path.exists():
        return ExplorerInitResponse(config_path=str(config_path), created=False)

    config_dir.mkdir(parents=True, exist_ok=True)
    config_path.write_text(render_starter_config(project_path), encoding="utf-8")
    annotations_path = config_dir / ANNOTATIONS_FILENAME
    if not annotations_path.exists():
        annotations_path.write_text(
            "# Per-node overrides for the explorer. Keys are node ids;\n"
            "# values are partial node payloads merged on top of the indexer output.\n"
            "# Example:\n"
            "#   rpa:Main.xaml:\n"
            "#     business_status: live\n"
            "#     business_meta: { owner: Sales Ops, sla: \"p95 8 min\", risk: medium }\n",
            encoding="utf-8",
        )
    return ExplorerInitResponse(config_path=str(config_path), created=True)


@router.get("/knowledge", response_model=ExplorerKnowledgeResponse)
def get_node_knowledge(
    worktree: str = Query("repo-root"),
    node: str = Query(..., min_length=1),
    q: str = Query(..., min_length=1),
    top_n: int = Query(5, ge=1, le=20),
) -> ExplorerKnowledgeResponse:
    citations: list[ExplorerCitation] = []
    skills: list[ExplorerSkill] = []
    try:
        items = search_library_context(q, top_n=top_n)
        citations = [_to_citation(i) for i in items]
    except Exception:
        citations = []
    try:
        skills = _match_skills(f"{node} {q}", top_k=top_n)
    except Exception:
        skills = []
    return ExplorerKnowledgeResponse(citations=citations, skills=skills)


@router.get("/skill", response_model=ExplorerSkillDetailResponse)
def get_skill_detail(
    id: str = Query(..., min_length=1),
) -> ExplorerSkillDetailResponse:
    detail = read_skill_detail(_repo_root(), id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"skill not found: {id}")
    return ExplorerSkillDetailResponse(**detail)


@router.get("/library/section", response_model=ExplorerLibrarySectionResponse)
def get_library_section(
    book: str = Query(..., min_length=1),
    chapter: str = Query(..., min_length=1),
    section: str = Query(..., min_length=1),
) -> ExplorerLibrarySectionResponse:
    body = _read_library_section(book, chapter, section)
    if body is None:
        raise HTTPException(status_code=404, detail="section not found")
    return ExplorerLibrarySectionResponse(
        book_id=book, chapter_id=chapter, section_id=section, body=body,
    )
