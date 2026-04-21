"""MCP tools for UiPath build planning and git-tracked implementation plans.

Includes ``uipath_plan_build`` (discovery-fronted planner) and CRUD-style
helpers under ``docs/plans/`` (save, list, read, status, mermaid extract).
"""
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import yaml
from mcp.types import Tool, ToolAnnotations

from uipath_claude.query.planner import run_planner_agent_with_discovery
from uipath_claude.skills.submodule_guard import verify as verify_guard
from uipath_claude.tools import design_store

_PLAN_STATUSES = frozenset({"draft", "in-progress", "done", "superseded"})
_PROJECT_TYPES = frozenset({"rpa", "coded-agent", "solution", "coded-app", "mixed"})
_SKIP_LIST = frozenset({"_TEMPLATE.md", "README.md"})
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,120}$")
_FILENAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9_-]+\.md$")
_MERMAID_BLOCK = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)


def _ro(title: str) -> ToolAnnotations:
    return ToolAnnotations(title=title, readOnlyHint=True)


def _write(title: str, *, destructive: bool = True, idempotent: bool = True) -> ToolAnnotations:
    return ToolAnnotations(
        title=title,
        readOnlyHint=False,
        destructiveHint=destructive,
        idempotentHint=idempotent,
    )


def _staging(title: str) -> ToolAnnotations:
    return ToolAnnotations(
        title=title,
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
    )


def get_plan_tools() -> list[Tool]:
    return [
        Tool(
            name="uipath_plan_build",
            description=(
                "Produce an executable UiPath build plan. First runs the "
                "submodule guard to ensure the UiPath/skills submodule is "
                "pinned and clean, then runs the uipath-project-discovery-"
                "agent from that submodule to populate "
                ".claude/rules/project-context.md, then invokes the read-only "
                "planner with the discovery document as context. Returns the "
                "planner's final response plus traceability metadata."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "user_request": {
                        "type": "string",
                        "description": "Natural-language build request.",
                    },
                    "project_root": {
                        "type": "string",
                        "description": (
                            "Optional absolute path to the UiPath project root. "
                            "Defaults to the workspace the MCP server is running in."
                        ),
                    },
                    "force_rediscover": {
                        "type": "boolean",
                        "description": (
                            "Force re-running the discovery agent even when a "
                            "recent project-context.md exists."
                        ),
                        "default": False,
                    },
                    "bypass_guard": {
                        "type": "boolean",
                        "description": (
                            "Opt-out of the submodule guard check. Only for "
                            "read-only tooling development; never set this in "
                            "production flows."
                        ),
                        "default": False,
                    },
                },
                "required": ["user_request"],
            },
            annotations=_ro("Plan a UiPath build (discovery-fronted)"),
        ),
        Tool(
            name="uipath_plan_save",
            description=(
                "Create or overwrite a markdown plan under docs/plans/. "
                "``content`` must include YAML front matter (slug, title, date, "
                "status, owner, project_type) and at least one ```mermaid block "
                "in the body. Filename defaults to {date}-{slug}.md. "
                "Regenerates docs/plans/README.md index when the save succeeds."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Full markdown file including --- front matter ---.",
                    },
                    "project_root": {
                        "type": "string",
                        "description": "Repository root (defaults to cwd).",
                    },
                    "filename": {
                        "type": "string",
                        "description": (
                            "Optional basename YYYY-MM-DD-slug.md; must match "
                            "front matter date/slug when omitted."
                        ),
                    },
                },
                "required": ["content"],
            },
            annotations=_write("Save implementation plan under docs/plans/", destructive=True),
        ),
        Tool(
            name="uipath_plan_list",
            description=(
                "List markdown plans in docs/plans/ (excludes _TEMPLATE.md and "
                "README.md), returning file names and parsed front-matter fields."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_root": {
                        "type": "string",
                        "description": "Repository root (defaults to cwd).",
                    },
                },
            },
            annotations=_ro("List docs/plans implementation plans"),
        ),
        Tool(
            name="uipath_plan_read",
            description=(
                "Read one plan file from docs/plans/ by basename (e.g. "
                "2026-04-21-my-slug.md) or by slug (must be unique among plan "
                "files)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_root": {
                        "type": "string",
                        "description": "Repository root (defaults to cwd).",
                    },
                    "filename": {
                        "type": "string",
                        "description": "Basename under docs/plans/, e.g. 2026-04-21-feature.md",
                    },
                    "slug": {
                        "type": "string",
                        "description": "Front-matter slug when filename is unknown.",
                    },
                },
            },
            annotations=_ro("Read one implementation plan"),
        ),
        Tool(
            name="uipath_plan_status_set",
            description=(
                "Update the status field in a plan's YAML front matter. "
                "Values: draft, in-progress, done, superseded. Transition to "
                "done requires an approved design for project_dir when "
                "UIPATH_DESIGN_APPROVAL_ENABLED is on (same gate as workflow writes)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_root": {
                        "type": "string",
                        "description": "Repository root (defaults to cwd).",
                    },
                    "filename": {"type": "string", "description": "Plan basename under docs/plans/."},
                    "slug": {
                        "type": "string",
                        "description": "Alternative to filename when basename is unknown.",
                    },
                    "new_status": {
                        "type": "string",
                        "enum": sorted(_PLAN_STATUSES),
                        "description": "New status value.",
                    },
                    "project_dir": {
                        "type": "string",
                        "description": (
                            "Project directory for design approval check when "
                            "new_status is done; defaults to project_root."
                        ),
                    },
                },
                "required": ["new_status"],
            },
            annotations=_staging("Set plan status in front matter"),
        ),
        Tool(
            name="uipath_plan_render_mermaid",
            description=(
                "Extract fenced ```mermaid blocks from a plan file for quick "
                "syntax review or reuse in docs."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_root": {
                        "type": "string",
                        "description": "Repository root (defaults to cwd).",
                    },
                    "filename": {"type": "string"},
                    "slug": {"type": "string"},
                },
            },
            annotations=_ro("Extract Mermaid blocks from a plan"),
        ),
    ]


def _result_to_dict(result: Any) -> dict[str, Any]:
    if is_dataclass(result):
        return asdict(result)
    return {"value": str(result)}


def _resolve_repo_root(project_root: str | None) -> Path:
    raw = project_root or sys.environ.get("WORKSPACE_ROOT") or "."
    return Path(raw).expanduser().resolve()


def _plans_dir(repo: Path) -> Path:
    return repo / "docs" / "plans"


def _regen_plan_index(repo: Path) -> dict[str, Any]:
    script = repo / "scripts" / "generate_plan_index.py"
    if not script.is_file():
        return {"skipped": True, "reason": "script missing"}
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
    }


def _split_front_matter(text: str) -> tuple[dict[str, Any], str]:
    if not text.lstrip().startswith("---"):
        raise ValueError("Plan must start with YAML front matter (---)")
    m = re.match(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n", text, re.DOTALL)
    if not m:
        raise ValueError("Invalid front matter: closing --- not found")
    meta = yaml.safe_load(m.group(1))
    if not isinstance(meta, dict):
        raise ValueError("Front matter must parse to a YAML mapping")
    body = text[m.end() :]
    return meta, body


def _compose_plan(meta: dict[str, Any], body: str) -> str:
    dumped = yaml.safe_dump(
        meta,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    ).rstrip()
    return f"---\n{dumped}\n---\n{body}"


def _validate_plan_meta(meta: dict[str, Any], *, full: bool) -> None:
    if full:
        for key in ("slug", "title", "date", "status", "owner", "project_type"):
            if key not in meta or meta[key] in (None, ""):
                raise ValueError(f"front matter missing required key: {key}")
        slug = str(meta["slug"])
        if not _SLUG_RE.match(slug):
            raise ValueError(
                "slug must be lowercase [a-z0-9-], start alphanumeric, length 2-121"
            )
        status = str(meta["status"])
        if status not in _PLAN_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(_PLAN_STATUSES))}")
        ptype = str(meta["project_type"])
        if ptype not in _PROJECT_TYPES:
            raise ValueError(
                f"project_type must be one of: {', '.join(sorted(_PROJECT_TYPES))}"
            )


def _ensure_mermaid(body: str) -> None:
    if "```mermaid" not in body.lower():
        raise ValueError("Plan body must contain at least one ```mermaid fenced block")


def _safe_plan_path(plans_dir: Path, basename: str) -> Path:
    name = Path(basename).name
    if name in _SKIP_LIST or name.startswith("."):
        raise ValueError(f"refusing to write reserved or hidden name: {name}")
    if ".." in name or "/" in name or "\\" in name:
        raise ValueError("filename must be a plain basename")
    if not _FILENAME_RE.match(name):
        raise ValueError("filename must match YYYY-MM-DD-slug.md (slug: lowercase letters, digits, hyphen, underscore)")
    path = (plans_dir / name).resolve()
    try:
        path.relative_to(plans_dir.resolve())
    except ValueError as exc:
        raise ValueError("path escapes docs/plans") from exc
    return path


def _find_plan_path(plans_dir: Path, filename: str | None, slug: str | None) -> Path:
    if filename:
        return _safe_plan_path(plans_dir, filename)
    if not slug:
        raise ValueError("provide filename or slug")
    if not _SLUG_RE.match(slug):
        raise ValueError("invalid slug")
    matches: list[Path] = []
    if plans_dir.is_dir():
        for p in plans_dir.glob("*.md"):
            if p.name in _SKIP_LIST:
                continue
            try:
                raw = p.read_text(encoding="utf-8")
                meta, _ = _split_front_matter(raw)
            except Exception:
                continue
            if str(meta.get("slug", "")) == slug:
                matches.append(p)
    if not matches:
        raise FileNotFoundError(f"no plan with slug {slug!r}")
    if len(matches) > 1:
        names = ", ".join(sorted(x.name for x in matches))
        raise ValueError(f"slug {slug!r} is ambiguous: {names}")
    return matches[0]


async def _call_plan_build(arguments: dict[str, Any]) -> dict[str, Any]:
    user_request = arguments.get("user_request", "")
    if not isinstance(user_request, str) or not user_request.strip():
        raise ValueError("'user_request' must be a non-empty string")

    project_root = arguments.get("project_root")
    force_rediscover = bool(arguments.get("force_rediscover", False))
    bypass_guard = bool(arguments.get("bypass_guard", False))

    guard_report: dict[str, Any] | None = None
    if not bypass_guard:
        guard_result = verify_guard(
            strict=True,
            repo_root=Path(project_root).resolve() if project_root else None,
        )
        guard_report = {
            "ok": guard_result.ok,
            "errors": list(guard_result.errors),
            "warnings": list(guard_result.warnings),
            "checked": list(guard_result.checked),
        }
        if not guard_result.ok:
            return {
                "status": "blocked",
                "reason": "submodule_guard_failed",
                "guard": guard_report,
                "plan": None,
            }

    planner_result = await run_planner_agent_with_discovery(
        user_request,
        repo_root=project_root,
        force_rediscover=force_rediscover,
    )

    return {
        "status": "ok",
        "guard": guard_report,
        "plan": _result_to_dict(planner_result),
    }


def _call_plan_save(arguments: dict[str, Any]) -> dict[str, Any]:
    repo = _resolve_repo_root(arguments.get("project_root"))
    content = arguments.get("content", "")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("'content' must be a non-empty string")
    meta, body = _split_front_matter(content)
    _validate_plan_meta(meta, full=True)
    _ensure_mermaid(body)
    fname_arg = arguments.get("filename")
    fname = fname_arg if isinstance(fname_arg, str) and fname_arg.strip() else None
    basename = _filename_for_save(meta, fname)
    plans_dir = _plans_dir(repo)
    plans_dir.mkdir(parents=True, exist_ok=True)
    path = _safe_plan_path(plans_dir, basename)
    path.write_text(_compose_plan(meta, body.lstrip("\n")), encoding="utf-8")
    idx = _regen_plan_index(repo)
    return {
        "status": "ok",
        "path": str(path),
        "relative": str(path.relative_to(repo)),
        "index_regen": idx,
    }


def _filename_for_save(meta: dict[str, Any], filename: str | None) -> str:
    if filename:
        return Path(filename.strip()).name
    date = str(meta.get("date", "")).strip()
    slug = str(meta.get("slug", "")).strip()
    return f"{date}-{slug}.md"


def _call_plan_list(arguments: dict[str, Any]) -> dict[str, Any]:
    repo = _resolve_repo_root(arguments.get("project_root"))
    plans_dir = _plans_dir(repo)
    items: list[dict[str, Any]] = []
    if not plans_dir.is_dir():
        return {"status": "ok", "plans": [], "plans_dir": str(plans_dir)}
    for path in sorted(plans_dir.glob("*.md"), reverse=True):
        if path.name in _SKIP_LIST:
            continue
        try:
            raw = path.read_text(encoding="utf-8")
            meta, _ = _split_front_matter(raw)
        except Exception:
            items.append({"file": path.name, "parse_error": True})
            continue
        items.append(
            {
                "file": path.name,
                "slug": meta.get("slug"),
                "title": meta.get("title"),
                "date": meta.get("date"),
                "status": meta.get("status"),
                "owner": meta.get("owner"),
                "project_type": meta.get("project_type"),
            }
        )
    return {"status": "ok", "plans": items, "plans_dir": str(plans_dir)}


def _call_plan_read(arguments: dict[str, Any]) -> dict[str, Any]:
    repo = _resolve_repo_root(arguments.get("project_root"))
    plans_dir = _plans_dir(repo)
    filename = arguments.get("filename")
    slug = arguments.get("slug")
    fn = filename if isinstance(filename, str) and filename.strip() else None
    sl = slug if isinstance(slug, str) and slug.strip() else None
    path = _find_plan_path(plans_dir, fn, sl)
    return {
        "status": "ok",
        "path": str(path),
        "relative": str(path.relative_to(repo)),
        "content": path.read_text(encoding="utf-8"),
    }


def _call_plan_status_set(arguments: dict[str, Any]) -> dict[str, Any]:
    repo = _resolve_repo_root(arguments.get("project_root"))
    plans_dir = _plans_dir(repo)
    new_status = arguments.get("new_status")
    if not isinstance(new_status, str) or new_status not in _PLAN_STATUSES:
        raise ValueError(f"new_status must be one of: {', '.join(sorted(_PLAN_STATUSES))}")

    filename = arguments.get("filename")
    slug = arguments.get("slug")
    fn = filename if isinstance(filename, str) and filename.strip() else None
    sl = slug if isinstance(slug, str) and slug.strip() else None
    path = _find_plan_path(plans_dir, fn, sl)

    if new_status == "done":
        pd = arguments.get("project_dir")
        project_dir = pd if isinstance(pd, str) and pd.strip() else str(repo)
        if not design_store.has_approved(project_dir):
            return {
                "status": "blocked",
                "reason": "design_not_approved",
                "message": (
                    "Cannot mark plan done without an approved design for "
                    f"project_dir={project_dir!r} (or set UIPATH_DESIGN_APPROVAL_ENABLED=0 for dev)."
                ),
            }

    raw = path.read_text(encoding="utf-8")
    meta, body = _split_front_matter(raw)
    meta["status"] = new_status
    path.write_text(_compose_plan(meta, body.lstrip("\n")), encoding="utf-8")
    idx = _regen_plan_index(repo)
    return {
        "status": "ok",
        "path": str(path),
        "new_status": new_status,
        "index_regen": idx,
    }


def _call_plan_render_mermaid(arguments: dict[str, Any]) -> dict[str, Any]:
    repo = _resolve_repo_root(arguments.get("project_root"))
    plans_dir = _plans_dir(repo)
    filename = arguments.get("filename")
    slug = arguments.get("slug")
    fn = filename if isinstance(filename, str) and filename.strip() else None
    sl = slug if isinstance(slug, str) and slug.strip() else None
    path = _find_plan_path(plans_dir, fn, sl)
    raw = path.read_text(encoding="utf-8")
    _, body = _split_front_matter(raw)
    blocks = [m.group(1).strip() for m in _MERMAID_BLOCK.finditer(body)]
    return {
        "status": "ok",
        "path": str(path),
        "blocks": blocks,
        "count": len(blocks),
    }


async def call_plan_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "uipath_plan_build":
        return await _call_plan_build(arguments)
    if name == "uipath_plan_save":
        return _call_plan_save(arguments)
    if name == "uipath_plan_list":
        return _call_plan_list(arguments)
    if name == "uipath_plan_read":
        return _call_plan_read(arguments)
    if name == "uipath_plan_status_set":
        return _call_plan_status_set(arguments)
    if name == "uipath_plan_render_mermaid":
        return _call_plan_render_mermaid(arguments)
    raise ValueError(f"Unknown plan tool: {name}")
