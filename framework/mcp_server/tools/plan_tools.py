"""MCP tools for UiPath build planning and implementation plans.

Surfaces:

- ``uipath_plan_build`` (discovery-fronted planner) and CRUD on the published
  ``docs/plans/`` tree (``save/list/read/status_set/render_mermaid``).
- A superpowers-style brainstorm loop: ``uipath_plan_new`` (scaffold draft under
  ``.cursor/plans/``), ``uipath_plan_brainstorm`` (grounding hints),
  ``uipath_plan_refine`` (structured patch), ``uipath_plan_diff``,
  ``uipath_plan_accept`` / ``uipath_plan_reject``, ``uipath_plan_publish``
  (draft -> ``docs/plans/``).
- Optional ``UIPATH_PLAN_GATE`` hook consumed by destructive workflow tools so
  an accepted plan can gate writes/publish/deploy.
"""
from __future__ import annotations

import datetime as _dt
import difflib
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import yaml
from mcp.types import Tool, ToolAnnotations

from mcp_server.tools.plan_folder import (
    collect_folder_plan_entries,
    is_folder_plan,
    load_folder_meta,
    read_uiplan_files,
    resolve_plan_path,
    save_folder_meta,
)
from mcp_server.tools.plan_uiplan import (
    call_uiplan_ground,
    call_uiplan_new,
    call_uiplan_plan_new,
    call_uiplan_review,
    call_uiplan_spec_new,
    call_uiplan_tasks_new,
    uiplan_publish_folder,
)
from uipath_claude.query.planner import run_planner_agent_with_discovery
from uipath_claude.skills.submodule_guard import verify as verify_guard
from uipath_claude.tools import design_store

_PLAN_STATUSES = frozenset(
    {
        "draft",
        "refining",
        "accepted",
        "rejected",
        "in-progress",
        "done",
        "superseded",
    }
)
_PROJECT_TYPES = frozenset({"rpa", "coded-agent", "solution", "coded-app", "mixed"})
_SKIP_LIST = frozenset({"_TEMPLATE.md", "README.md"})
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,120}$")
_FILENAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9_-]+\.md$")
_MERMAID_BLOCK = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
_LIST_SCOPES = frozenset({"drafts", "published", "both"})


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
                "List markdown plans, returning file names and parsed front-matter "
                "fields. Default scope 'published' reads docs/plans/ (git-tracked); "
                "'drafts' reads .cursor/plans/ (per-user, git-ignored); 'both' returns "
                "a combined list with a scope marker per entry."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_root": {
                        "type": "string",
                        "description": "Repository root (defaults to cwd).",
                    },
                    "scope": {
                        "type": "string",
                        "enum": sorted(_LIST_SCOPES),
                        "description": "drafts | published | both (default published).",
                    },
                },
            },
            annotations=_ro("List plans (drafts and/or published)"),
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
                "Update the status field in a plan's YAML front matter. Values: "
                "draft, refining, accepted, rejected, in-progress, done, "
                "superseded. Transition to 'done' requires an approved design for "
                "project_dir when UIPATH_DESIGN_APPROVAL_ENABLED is on (same gate "
                "as workflow writes). For acceptance/rejection prefer the "
                "dedicated uipath_plan_accept / uipath_plan_reject tools which "
                "also stamp actor/timestamp/reason."
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
                "syntax review or reuse in docs. Searches drafts under "
                ".cursor/plans/ first, then published under docs/plans/."
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
                    "scope": {
                        "type": "string",
                        "enum": sorted(_LIST_SCOPES),
                        "description": "Where to look: drafts, published, or both (default both).",
                    },
                },
            },
            annotations=_ro("Extract Mermaid blocks from a plan"),
        ),
        Tool(
            name="uipath_plan_new",
            description=(
                "Scaffold a new plan draft under .cursor/plans/ (per-user, "
                "git-ignored). Seeds front matter (slug, title, date, status=draft, "
                "owner, project_type) plus the docs/plans/_TEMPLATE.md skeleton "
                "and a placeholder ``## Context`` section for grounding output. "
                "Use uipath_plan_refine to add tasks and grounding, and "
                "uipath_plan_publish to promote to docs/plans/ after acceptance."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Short human-readable plan title.",
                    },
                    "intent": {
                        "type": "string",
                        "description": "One to two sentences describing the goal.",
                    },
                    "slug": {
                        "type": "string",
                        "description": (
                            "Lowercase-kebab slug; auto-derived from title when omitted."
                        ),
                    },
                    "owner": {
                        "type": "string",
                        "description": "GitHub/Cursor handle (default: $USER or 'local').",
                    },
                    "project_type": {
                        "type": "string",
                        "enum": sorted(_PROJECT_TYPES),
                        "description": "UiPath project type; defaults to 'mixed'.",
                    },
                    "project_root": {
                        "type": "string",
                        "description": "Repository root (defaults to cwd).",
                    },
                },
                "required": ["title", "intent"],
            },
            annotations=_write("Create a new plan draft", destructive=False, idempotent=False),
        ),
        Tool(
            name="uipath_plan_brainstorm",
            description=(
                "Read-only grounding helper for drafting plans. Given a draft's "
                "intent (or an explicit prompt), returns a context pack of "
                "hints the caller should use to flesh out tasks: suggested "
                "library searches (call uipath_library_search with these), "
                "candidate specialist skills to load (uipath_skill_get), PDD/SDD/ADD "
                "candidates under docs/, and up to three clarifying questions "
                "to batch back to the user. When UIPATH_PLAN_WEB=1 and no web "
                "tool is registered, the response notes that web research was "
                "requested but skipped. This tool does NOT write to the plan."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": (
                            "Free-text intent; when omitted the tool reads the "
                            "draft's title + Goal section."
                        ),
                    },
                    "slug": {
                        "type": "string",
                        "description": "Draft slug under .cursor/plans/ (optional).",
                    },
                    "filename": {
                        "type": "string",
                        "description": "Draft basename under .cursor/plans/ (optional).",
                    },
                    "project_root": {
                        "type": "string",
                        "description": "Repository root (defaults to cwd).",
                    },
                },
            },
            annotations=_ro("Brainstorm grounding hints"),
        ),
        Tool(
            name="uipath_plan_refine",
            description=(
                "Apply a structured patch to a draft under .cursor/plans/. "
                "Operations: set_title / set_goal / append_task / replace_body_section "
                "(section_heading + new_body) / add_mermaid (appends a fenced "
                "mermaid block under ``## Architecture diagram``). Validates that "
                "the resulting file still has front matter + at least one mermaid "
                "block. Flips status to 'refining' unless explicitly set."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string"},
                    "filename": {"type": "string"},
                    "operations": {
                        "type": "array",
                        "description": "List of patch operations to apply in order.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "op": {
                                    "type": "string",
                                    "enum": [
                                        "set_title",
                                        "set_goal",
                                        "append_task",
                                        "replace_body_section",
                                        "add_mermaid",
                                    ],
                                },
                                "value": {"type": "string"},
                                "section_heading": {"type": "string"},
                                "new_body": {"type": "string"},
                            },
                            "required": ["op"],
                        },
                    },
                    "project_root": {"type": "string"},
                },
                "required": ["operations"],
            },
            annotations=_write("Apply structured patch to draft plan", destructive=True),
        ),
        Tool(
            name="uipath_plan_diff",
            description=(
                "Return a unified diff for a plan. By default compares a draft in "
                ".cursor/plans/ against its published twin in docs/plans/ (same "
                "basename); pass mode='self' to diff the draft against its own "
                "last-saved snapshot when one exists in .cursor/plans/.snapshots/."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string"},
                    "filename": {"type": "string"},
                    "mode": {
                        "type": "string",
                        "enum": ["vs-published", "self"],
                        "description": "vs-published (default) or self.",
                    },
                    "project_root": {"type": "string"},
                },
            },
            annotations=_ro("Diff a plan draft"),
        ),
        Tool(
            name="uipath_plan_accept",
            description=(
                "Mark a draft plan as accepted: status='accepted', stamps "
                "accepted_at (UTC ISO) and accepted_by. The draft is the source "
                "of truth until uipath_plan_publish promotes it to docs/plans/. "
                "When UIPATH_PLAN_GATE=1, destructive workflow tools consult this "
                "acceptance record for project_dir before writing."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string"},
                    "filename": {"type": "string"},
                    "actor": {
                        "type": "string",
                        "description": "Who accepted (default: $USER or 'human').",
                    },
                    "note": {
                        "type": "string",
                        "description": "Optional short acceptance note.",
                    },
                    "project_root": {"type": "string"},
                },
            },
            annotations=_write("Accept a plan draft", destructive=True),
        ),
        Tool(
            name="uipath_plan_reject",
            description=(
                "Mark a draft as rejected and record the reason. Refuses when "
                "rejection_reason is empty; the rationale lives in front matter "
                "for auditability. Does NOT delete the draft - the caller may "
                "archive or supersede it."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string"},
                    "filename": {"type": "string"},
                    "rejection_reason": {
                        "type": "string",
                        "description": "Non-empty rationale recorded in front matter.",
                    },
                    "actor": {"type": "string"},
                    "project_root": {"type": "string"},
                },
                "required": ["rejection_reason"],
            },
            annotations=_write("Reject a plan draft", destructive=True),
        ),
        Tool(
            name="uipath_plan_publish",
            description=(
                "Promote an accepted draft from .cursor/plans/ to docs/plans/ "
                "(git-tracked). Refuses when status != 'accepted'. Stamps "
                "published_at (UTC ISO) and regenerates docs/plans/README.md. "
                "Overwrites any existing same-named file only when force=true."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string"},
                    "filename": {"type": "string"},
                    "force": {"type": "boolean", "default": False},
                    "project_root": {"type": "string"},
                },
            },
            annotations=_write("Publish accepted plan to docs/plans/", destructive=True),
        ),
        Tool(
            name="uipath_plan_ground",
            description=(
                "Build a grounding pack for UiPlan: project-context excerpt, "
                "CLAUDE.md excerpt, ranked skills, library search hits, PDD/SDD "
                "candidates, suggested project template path, constitution gates, "
                "and suggested citation strings. Read-only."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Feature or build intent to ground (non-empty).",
                    },
                    "project_root": {"type": "string"},
                },
                "required": ["topic"],
            },
            annotations=_ro("Ground UiPlan from workspace"),
        ),
        Tool(
            name="uipath_plan_spec_new",
            description=(
                "Create a UiPlan draft folder under .cursor/plans/ with spec.md "
                "from docs/plans/_uiplan/_spec-template.md plus .meta.yaml "
                "(plan_kind=uiplan). Optionally pass grounding_pack from "
                "uipath_plan_ground; otherwise grounding is computed from intent."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Human-readable feature title."},
                    "intent": {
                        "type": "string",
                        "description": "Goal description (same as topic if single field).",
                    },
                    "topic": {
                        "type": "string",
                        "description": "Alias for intent when intent is omitted.",
                    },
                    "slug": {"type": "string"},
                    "owner": {"type": "string"},
                    "project_type": {"type": "string", "enum": sorted(_PROJECT_TYPES)},
                    "project_root": {"type": "string"},
                    "grounding_pack": {
                        "type": "object",
                        "description": "Optional output from uipath_plan_ground.",
                    },
                },
                "required": ["title"],
            },
            annotations=_write("Create UiPlan spec.md draft folder", destructive=True),
        ),
        Tool(
            name="uipath_plan_plan_new",
            description=(
                "Write plan.md into an existing UiPlan folder (run "
                "uipath_plan_spec_new first). Fills Technical Context, "
                "Constitution Check from repo constitution, and structure decision."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string", "description": "UiPlan slug (meta.slug)."},
                    "project_root": {"type": "string"},
                    "grounding_pack": {"type": "object"},
                },
                "required": ["slug"],
            },
            annotations=_write("Write UiPlan plan.md", destructive=True),
        ),
        Tool(
            name="uipath_plan_tasks_new",
            description=(
                "Write tasks.md into an existing UiPlan folder after plan.md "
                "exists. Phase-grouped tasks with [USn] markers and test-first sections."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {
                        "type": "string",
                        "description": "UiPlan slug from .meta.yaml (same as folder meta slug).",
                    },
                    "project_root": {"type": "string"},
                    "grounding_pack": {"type": "object"},
                },
                "required": ["slug"],
            },
            annotations=_write("Write UiPlan tasks.md", destructive=True),
        ),
        Tool(
            name="uipath_plan_review",
            description=(
                "Run structured UiPlan review on spec.md/plan.md/tasks.md in a "
                "folder-shaped draft. Returns ok, findings[], next_action. "
                "stage: spec | plan | tasks | all (default all)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {
                        "type": "string",
                        "description": "UiPlan slug identifying the draft folder under .cursor/plans/.",
                    },
                    "stage": {
                        "type": "string",
                        "enum": ["spec", "plan", "tasks", "all"],
                        "description": "Which checks to run (default all).",
                    },
                    "project_root": {"type": "string"},
                },
                "required": ["slug"],
            },
            annotations=_ro("Review UiPlan bundle"),
        ),
        Tool(
            name="uipath_plan_uiplan_new",
            description=(
                "Orchestrator: uipath_plan_ground -> spec_new -> plan_new -> "
                "tasks_new -> uipath_plan_review(all). Returns paths and review "
                "payload; refine spec/plan/tasks before accept if review has errors."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Human-readable feature title for the UiPlan bundle.",
                    },
                    "intent": {"type": "string"},
                    "topic": {"type": "string", "description": "Alias for intent."},
                    "slug": {"type": "string"},
                    "owner": {"type": "string"},
                    "project_type": {"type": "string", "enum": sorted(_PROJECT_TYPES)},
                    "project_root": {"type": "string"},
                },
                "required": ["title"],
            },
            annotations=_write("Scaffold full UiPlan bundle", destructive=True),
        ),
    ]


def _result_to_dict(result: Any) -> dict[str, Any]:
    if is_dataclass(result):
        return asdict(result)
    return {"value": str(result)}


def _resolve_repo_root(project_root: str | None) -> Path:
    # os.environ: some Windows/embed builds omit sys.environ (AttributeError).
    raw = project_root or os.environ.get("WORKSPACE_ROOT") or "."
    return Path(raw).expanduser().resolve()


def _plans_dir(repo: Path) -> Path:
    return repo / "docs" / "plans"


def _drafts_dir(repo: Path) -> Path:
    return repo / ".cursor" / "plans"


def _snapshots_dir(repo: Path) -> Path:
    return _drafts_dir(repo) / ".snapshots"


def _utc_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")


def _derive_slug(text: str) -> str:
    lowered = text.strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    if not cleaned:
        cleaned = "plan"
    return cleaned[:80]


def _default_actor() -> str:
    return (
        os.environ.get("USER")
        or os.environ.get("USERNAME")
        or "local"
    )


def _default_plans_search(repo: Path) -> list[Path]:
    out: list[Path] = []
    for d in (_drafts_dir(repo), _plans_dir(repo)):
        if d.is_dir():
            out.append(d)
    return out


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
        raise ValueError(f"path escapes {plans_dir}") from exc
    return path


def _find_plan_path(
    plans_dir: Path,
    filename: str | None,
    slug: str | None,
    *,
    extra_dirs: list[Path] | None = None,
) -> Path:
    resolved = resolve_plan_path(plans_dir, filename, slug, extra_dirs=extra_dirs or [])
    return resolved.path


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


def _collect_plans(directory: Path, scope_label: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not directory.is_dir():
        return items
    for path in sorted(directory.glob("*.md"), reverse=True):
        if path.name in _SKIP_LIST:
            continue
        entry: dict[str, Any] = {"file": path.name, "scope": scope_label}
        try:
            raw = path.read_text(encoding="utf-8")
            meta, _ = _split_front_matter(raw)
        except Exception:
            entry["parse_error"] = True
            items.append(entry)
            continue
        entry.update(
            {
                "slug": meta.get("slug"),
                "title": meta.get("title"),
                "date": meta.get("date"),
                "status": meta.get("status"),
                "owner": meta.get("owner"),
                "project_type": meta.get("project_type"),
                "accepted_at": meta.get("accepted_at"),
                "published_at": meta.get("published_at"),
            }
        )
        items.append(entry)
    items.extend(collect_folder_plan_entries(directory, scope_label))
    items.sort(key=lambda e: (str(e.get("date") or ""), str(e.get("file") or "")), reverse=True)
    return items


def _call_plan_list(arguments: dict[str, Any]) -> dict[str, Any]:
    repo = _resolve_repo_root(arguments.get("project_root"))
    scope = arguments.get("scope") or "published"
    if scope not in _LIST_SCOPES:
        raise ValueError(f"scope must be one of: {', '.join(sorted(_LIST_SCOPES))}")
    plans_dir = _plans_dir(repo)
    drafts_dir = _drafts_dir(repo)
    items: list[dict[str, Any]] = []
    if scope in ("drafts", "both"):
        items.extend(_collect_plans(drafts_dir, "draft"))
    if scope in ("published", "both"):
        items.extend(_collect_plans(plans_dir, "published"))
    return {
        "status": "ok",
        "scope": scope,
        "plans": items,
        "plans_dir": str(plans_dir),
        "drafts_dir": str(drafts_dir),
    }


def _call_plan_read(arguments: dict[str, Any]) -> dict[str, Any]:
    repo = _resolve_repo_root(arguments.get("project_root"))
    plans_dir = _plans_dir(repo)
    drafts_dir = _drafts_dir(repo)
    filename = arguments.get("filename")
    slug = arguments.get("slug")
    fn = filename if isinstance(filename, str) and filename.strip() else None
    sl = slug if isinstance(slug, str) and slug.strip() else None
    path = _find_plan_path(plans_dir, fn, sl, extra_dirs=[drafts_dir])
    if is_folder_plan(path):
        resolved = resolve_plan_path(plans_dir, fn, sl, extra_dirs=[drafts_dir])
        files = read_uiplan_files(resolved)
        combined = (
            "--- spec.md ---\n"
            + files.get("spec.md", "")
            + "\n\n--- plan.md ---\n"
            + files.get("plan.md", "")
            + "\n\n--- tasks.md ---\n"
            + files.get("tasks.md", "")
        )
        return {
            "status": "ok",
            "path": str(path),
            "relative": str(_rel_to(path, repo)),
            "kind": "uiplan",
            "content": combined,
            "uiplan_files": files,
        }
    return {
        "status": "ok",
        "path": str(path),
        "relative": str(_rel_to(path, repo)),
        "content": path.read_text(encoding="utf-8"),
    }


def _rel_to(path: Path, repo: Path) -> str:
    try:
        return str(path.relative_to(repo))
    except ValueError:
        return str(path)


def _call_plan_status_set(arguments: dict[str, Any]) -> dict[str, Any]:
    repo = _resolve_repo_root(arguments.get("project_root"))
    plans_dir = _plans_dir(repo)
    drafts_dir = _drafts_dir(repo)
    new_status = arguments.get("new_status")
    if not isinstance(new_status, str) or new_status not in _PLAN_STATUSES:
        raise ValueError(f"new_status must be one of: {', '.join(sorted(_PLAN_STATUSES))}")

    filename = arguments.get("filename")
    slug = arguments.get("slug")
    fn = filename if isinstance(filename, str) and filename.strip() else None
    sl = slug if isinstance(slug, str) and slug.strip() else None
    path = _find_plan_path(plans_dir, fn, sl, extra_dirs=[drafts_dir])

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

    if is_folder_plan(path):
        meta = load_folder_meta(path)
        meta["status"] = new_status
        save_folder_meta(path, meta)
        idx: dict[str, Any] | None = None
        if _is_in(path, plans_dir):
            idx = _regen_plan_index(repo)
        return {
            "status": "ok",
            "path": str(path),
            "new_status": new_status,
            "index_regen": idx,
        }

    raw = path.read_text(encoding="utf-8")
    meta, body = _split_front_matter(raw)
    meta["status"] = new_status
    path.write_text(_compose_plan(meta, body.lstrip("\n")), encoding="utf-8")
    idx: dict[str, Any] | None = None
    if _is_in(path, plans_dir):
        idx = _regen_plan_index(repo)
    return {
        "status": "ok",
        "path": str(path),
        "new_status": new_status,
        "index_regen": idx,
    }


def _is_in(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False


def _call_plan_render_mermaid(arguments: dict[str, Any]) -> dict[str, Any]:
    repo = _resolve_repo_root(arguments.get("project_root"))
    plans_dir = _plans_dir(repo)
    drafts_dir = _drafts_dir(repo)
    filename = arguments.get("filename")
    slug = arguments.get("slug")
    fn = filename if isinstance(filename, str) and filename.strip() else None
    sl = slug if isinstance(slug, str) and slug.strip() else None
    scope = arguments.get("scope") or "both"
    if scope not in _LIST_SCOPES:
        raise ValueError(f"scope must be one of: {', '.join(sorted(_LIST_SCOPES))}")
    extra: list[Path] = []
    if scope == "drafts":
        primary = drafts_dir
    elif scope == "published":
        primary = plans_dir
    else:
        primary = drafts_dir
        extra = [plans_dir]
    path = _find_plan_path(primary, fn, sl, extra_dirs=extra)
    if is_folder_plan(path):
        resolved = resolve_plan_path(primary, fn, sl, extra_dirs=extra)
        files = read_uiplan_files(resolved)
        blocks: list[str] = []
        for part in files.values():
            blocks.extend(m.group(1).strip() for m in _MERMAID_BLOCK.finditer(part))
        return {
            "status": "ok",
            "path": str(path),
            "blocks": blocks,
            "count": len(blocks),
        }
    raw = path.read_text(encoding="utf-8")
    _, body = _split_front_matter(raw)
    blocks = [m.group(1).strip() for m in _MERMAID_BLOCK.finditer(body)]
    return {
        "status": "ok",
        "path": str(path),
        "blocks": blocks,
        "count": len(blocks),
    }


_DRAFT_SKELETON = """# {title}

**Goal:** {intent}

**Architecture:** _Two or three sentences on approach and boundaries._

## Architecture diagram

```mermaid
flowchart TD
  Start([Start]):::start --> Step[Implement]:::process
  Step --> EndOk(((Done))):::endOk

  classDef start   fill:#ECFDF5,stroke:#10B981,color:#065F46,stroke-width:2px
  classDef process fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:1.25px
  classDef endOk   fill:#ECFDF5,stroke:#10B981,color:#065F46,stroke-width:2px

  linkStyle default stroke:#94A3B8,stroke-width:1.5px
```

## Context

_Populated by `uipath_plan_brainstorm` (library / skills / PDD hints)._

## File plan

| Path | Responsibility |
|------|------------------|
| `path/to/file.py` | ... |

## Bite-sized tasks

- [ ] Write or adjust failing test
- [ ] Minimal implementation
- [ ] Run test suite
- [ ] Update docs if behavior changed
- [ ] Commit with clear message

## Verification

```bash
pytest tests/ -q
```

## Rollback

Revert the commit / delete the branch; note any data migrations separately.
"""


def _call_plan_new(arguments: dict[str, Any]) -> dict[str, Any]:
    repo = _resolve_repo_root(arguments.get("project_root"))
    title = arguments.get("title", "")
    intent = arguments.get("intent", "")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("'title' must be a non-empty string")
    if not isinstance(intent, str) or not intent.strip():
        raise ValueError("'intent' must be a non-empty string")
    slug_in = arguments.get("slug")
    slug = slug_in if isinstance(slug_in, str) and slug_in.strip() else _derive_slug(title)
    if not _SLUG_RE.match(slug):
        raise ValueError("slug must be lowercase [a-z0-9-], start alphanumeric, length 2-121")
    owner = arguments.get("owner") or _default_actor()
    project_type = arguments.get("project_type") or "mixed"
    if project_type not in _PROJECT_TYPES:
        raise ValueError(f"project_type must be one of: {', '.join(sorted(_PROJECT_TYPES))}")
    date = _today_iso()
    meta = {
        "slug": slug,
        "title": title.strip(),
        "date": date,
        "status": "draft",
        "owner": str(owner),
        "project_type": project_type,
        "linked_pdd": "",
        "supersedes": None,
        "accepted_at": None,
        "accepted_by": None,
        "rejection_reason": None,
        "published_at": None,
    }
    body = _DRAFT_SKELETON.format(title=title.strip(), intent=intent.strip())
    drafts_dir = _drafts_dir(repo)
    drafts_dir.mkdir(parents=True, exist_ok=True)
    basename = f"{date}-{slug}.md"
    path = _safe_plan_path(drafts_dir, basename)
    if path.exists():
        raise FileExistsError(f"draft already exists: {path}")
    path.write_text(_compose_plan(meta, body), encoding="utf-8")
    return {
        "status": "ok",
        "path": str(path),
        "relative": _rel_to(path, repo),
        "slug": slug,
        "filename": basename,
    }


def _scan_pdd_candidates(repo: Path, limit: int = 10) -> list[dict[str, str]]:
    docs = repo / "docs"
    if not docs.is_dir():
        return []
    hits: list[dict[str, str]] = []
    patterns = ("PDD", "SDD", "ADD")
    for md in docs.rglob("*.md"):
        name_upper = md.name.upper()
        for tag in patterns:
            if tag in name_upper:
                hits.append(
                    {
                        "path": _rel_to(md, repo),
                        "kind": tag,
                        "name": md.name,
                    }
                )
                break
        if len(hits) >= limit:
            break
    return hits


def _call_plan_brainstorm(arguments: dict[str, Any]) -> dict[str, Any]:
    repo = _resolve_repo_root(arguments.get("project_root"))
    drafts_dir = _drafts_dir(repo)
    plans_dir = _plans_dir(repo)
    prompt = arguments.get("prompt")
    filename = arguments.get("filename")
    slug = arguments.get("slug")

    hint_prompt = ""
    draft_path: Path | None = None
    if (filename or slug) and not (isinstance(prompt, str) and prompt.strip()):
        fn = filename if isinstance(filename, str) and filename.strip() else None
        sl = slug if isinstance(slug, str) and slug.strip() else None
        try:
            draft_path = _find_plan_path(drafts_dir, fn, sl, extra_dirs=[plans_dir])
            raw = draft_path.read_text(encoding="utf-8")
            meta, body = _split_front_matter(raw)
            hint_prompt = f"{meta.get('title', '')}. "
            goal_match = re.search(r"\*\*Goal:\*\*\s*(.+)", body)
            if goal_match:
                hint_prompt += goal_match.group(1).strip()
        except Exception:
            pass
    if isinstance(prompt, str) and prompt.strip():
        hint_prompt = prompt.strip()
    if not hint_prompt:
        raise ValueError("provide 'prompt' or a valid draft slug/filename")

    terms = [
        w.lower()
        for w in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", hint_prompt)
    ]
    seen: set[str] = set()
    queries: list[str] = []
    for t in terms:
        if t in seen:
            continue
        seen.add(t)
        queries.append(t)
        if len(queries) >= 6:
            break

    pdd_candidates = _scan_pdd_candidates(repo)

    web_requested = os.environ.get("UIPATH_PLAN_WEB", "0") == "1"
    web_note = None
    if web_requested:
        web_note = (
            "UIPATH_PLAN_WEB=1 set; no web tool is registered inside the MCP "
            "server - use the host agent's web search skill separately."
        )

    clarifying = [
        "What is the single-sentence success criterion for this plan?",
        "Which UiPath paradigm applies (RPA / coded agent / solution / coded app / mixed)?",
        "Are there existing PDD/SDD/ADD docs this plan should link to?",
    ]

    return {
        "status": "ok",
        "prompt": hint_prompt,
        "draft_path": str(draft_path) if draft_path else None,
        "library_queries": queries,
        "suggested_tools": [
            {"tool": "uipath_library_search", "args": {"query": q}} for q in queries[:3]
        ]
        + [
            {"tool": "uipath_skill_match", "args": {"request": hint_prompt}},
        ],
        "pdd_candidates": pdd_candidates,
        "clarifying_questions": clarifying,
        "web_research": {"requested": web_requested, "note": web_note},
    }


def _snapshot_draft(path: Path) -> Path | None:
    try:
        repo_drafts = path.parent
        snaps = repo_drafts / ".snapshots"
        snaps.mkdir(parents=True, exist_ok=True)
        ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        snap_path = snaps / f"{path.stem}.{ts}.md"
        shutil.copy2(path, snap_path)
        return snap_path
    except Exception:
        return None


def _apply_operations(body: str, operations: list[dict[str, Any]]) -> tuple[str, dict[str, Any] | None]:
    """Return (new_body, title_override_or_none)."""
    title_override: dict[str, Any] | None = None
    for raw_op in operations:
        if not isinstance(raw_op, dict):
            raise ValueError("each operation must be an object")
        op = raw_op.get("op")
        if op == "set_title":
            val = raw_op.get("value", "")
            if not isinstance(val, str) or not val.strip():
                raise ValueError("set_title requires 'value'")
            title_override = {"title": val.strip()}
            body = re.sub(
                r"^# .+\n",
                f"# {val.strip()}\n",
                body,
                count=1,
                flags=re.MULTILINE,
            )
        elif op == "set_goal":
            val = raw_op.get("value", "")
            if not isinstance(val, str) or not val.strip():
                raise ValueError("set_goal requires 'value'")
            if re.search(r"\*\*Goal:\*\*", body):
                body = re.sub(
                    r"\*\*Goal:\*\*.*",
                    f"**Goal:** {val.strip()}",
                    body,
                    count=1,
                )
            else:
                body = f"**Goal:** {val.strip()}\n\n" + body
        elif op == "append_task":
            val = raw_op.get("value", "")
            if not isinstance(val, str) or not val.strip():
                raise ValueError("append_task requires 'value'")
            task_line = f"- [ ] {val.strip()}\n"
            if "## Bite-sized tasks" in body:
                body = re.sub(
                    r"(## Bite-sized tasks\n(?:.*\n)*?)(\n## |\Z)",
                    lambda m: m.group(1).rstrip() + "\n" + task_line + "\n" + (m.group(2) or ""),
                    body,
                    count=1,
                )
            else:
                body += f"\n## Bite-sized tasks\n\n{task_line}"
        elif op == "replace_body_section":
            heading = raw_op.get("section_heading", "")
            new_body = raw_op.get("new_body", "")
            if not isinstance(heading, str) or not heading.strip():
                raise ValueError("replace_body_section requires 'section_heading'")
            if not isinstance(new_body, str):
                raise ValueError("replace_body_section requires 'new_body' string")
            pattern = re.compile(
                rf"({re.escape(heading.strip())}\n)(.*?)(\n## |\Z)",
                re.DOTALL,
            )
            if not pattern.search(body):
                body += f"\n{heading.strip()}\n\n{new_body}\n"
            else:
                body = pattern.sub(lambda m: m.group(1) + "\n" + new_body.rstrip() + "\n" + (m.group(3) or ""), body, count=1)
        elif op == "add_mermaid":
            val = raw_op.get("value", "")
            if not isinstance(val, str) or not val.strip():
                raise ValueError("add_mermaid requires 'value'")
            block = f"\n```mermaid\n{val.strip()}\n```\n"
            if "## Architecture diagram" in body:
                body = re.sub(
                    r"(## Architecture diagram\n)",
                    lambda m: m.group(1) + block,
                    body,
                    count=1,
                )
            else:
                body += f"\n## Architecture diagram\n{block}"
        else:
            raise ValueError(f"unknown op: {op!r}")
    return body, title_override


def _call_plan_refine(arguments: dict[str, Any]) -> dict[str, Any]:
    repo = _resolve_repo_root(arguments.get("project_root"))
    drafts_dir = _drafts_dir(repo)
    plans_dir = _plans_dir(repo)
    operations = arguments.get("operations")
    if not isinstance(operations, list) or not operations:
        raise ValueError("'operations' must be a non-empty list")
    filename = arguments.get("filename")
    slug = arguments.get("slug")
    fn = filename if isinstance(filename, str) and filename.strip() else None
    sl = slug if isinstance(slug, str) and slug.strip() else None
    path = _find_plan_path(drafts_dir, fn, sl, extra_dirs=[plans_dir])
    if is_folder_plan(path):
        raise ValueError(
            "uipath_plan_refine applies to legacy single-file drafts only; "
            "edit UiPlan spec.md/plan.md/tasks.md directly or re-run uipath_plan_spec_new."
        )
    raw = path.read_text(encoding="utf-8")
    meta, body = _split_front_matter(raw)
    _snapshot_draft(path)
    new_body, title_override = _apply_operations(body, operations)
    if title_override:
        meta.update(title_override)
    if meta.get("status") == "draft":
        meta["status"] = "refining"
    _ensure_mermaid(new_body)
    path.write_text(_compose_plan(meta, new_body.lstrip("\n")), encoding="utf-8")
    return {
        "status": "ok",
        "path": str(path),
        "ops_applied": len(operations),
        "new_status": meta.get("status"),
    }


def _call_plan_diff(arguments: dict[str, Any]) -> dict[str, Any]:
    repo = _resolve_repo_root(arguments.get("project_root"))
    drafts_dir = _drafts_dir(repo)
    plans_dir = _plans_dir(repo)
    filename = arguments.get("filename")
    slug = arguments.get("slug")
    fn = filename if isinstance(filename, str) and filename.strip() else None
    sl = slug if isinstance(slug, str) and slug.strip() else None
    mode = arguments.get("mode") or "vs-published"
    if mode not in ("vs-published", "self"):
        raise ValueError("mode must be 'vs-published' or 'self'")
    draft_path = _find_plan_path(drafts_dir, fn, sl)
    if is_folder_plan(draft_path):
        return {
            "status": "blocked",
            "reason": "uiplan_folder",
            "message": (
                "uipath_plan_diff does not support UiPlan folders; compare "
                "spec.md/plan.md/tasks.md under .cursor/plans/ manually or with git."
            ),
            "draft": _rel_to(draft_path, repo),
            "diff": "",
        }
    draft_text = draft_path.read_text(encoding="utf-8")

    if mode == "vs-published":
        published = plans_dir / draft_path.name
        other_text = published.read_text(encoding="utf-8") if published.is_file() else ""
        other_label = _rel_to(published, repo) if published.is_file() else "<no published twin>"
    else:
        snaps = _snapshots_dir(repo)
        other_text = ""
        other_label = "<no snapshot>"
        if snaps.is_dir():
            candidates = sorted(snaps.glob(f"{draft_path.stem}.*.md"), reverse=True)
            if candidates:
                other_text = candidates[0].read_text(encoding="utf-8")
                other_label = _rel_to(candidates[0], repo)

    diff_lines = list(
        difflib.unified_diff(
            other_text.splitlines(keepends=True),
            draft_text.splitlines(keepends=True),
            fromfile=other_label,
            tofile=_rel_to(draft_path, repo),
            n=3,
        )
    )
    return {
        "status": "ok",
        "mode": mode,
        "diff": "".join(diff_lines),
        "draft": _rel_to(draft_path, repo),
        "other": other_label,
    }


def _call_plan_accept(arguments: dict[str, Any]) -> dict[str, Any]:
    repo = _resolve_repo_root(arguments.get("project_root"))
    drafts_dir = _drafts_dir(repo)
    plans_dir = _plans_dir(repo)
    filename = arguments.get("filename")
    slug = arguments.get("slug")
    fn = filename if isinstance(filename, str) and filename.strip() else None
    sl = slug if isinstance(slug, str) and slug.strip() else None
    actor = arguments.get("actor") or _default_actor()
    note = arguments.get("note")
    path = _find_plan_path(drafts_dir, fn, sl, extra_dirs=[plans_dir])
    if is_folder_plan(path):
        meta = load_folder_meta(path)
        meta["status"] = "accepted"
        meta["accepted_at"] = _utc_iso()
        meta["accepted_by"] = str(actor)
        if isinstance(note, str) and note.strip():
            meta["acceptance_note"] = note.strip()
        meta["rejection_reason"] = None
        save_folder_meta(path, meta)
        return {
            "status": "ok",
            "path": str(path),
            "accepted_at": meta["accepted_at"],
            "accepted_by": meta["accepted_by"],
        }
    raw = path.read_text(encoding="utf-8")
    meta, body = _split_front_matter(raw)
    meta["status"] = "accepted"
    meta["accepted_at"] = _utc_iso()
    meta["accepted_by"] = str(actor)
    if isinstance(note, str) and note.strip():
        meta["acceptance_note"] = note.strip()
    meta["rejection_reason"] = None
    path.write_text(_compose_plan(meta, body.lstrip("\n")), encoding="utf-8")
    return {
        "status": "ok",
        "path": str(path),
        "accepted_at": meta["accepted_at"],
        "accepted_by": meta["accepted_by"],
    }


def _call_plan_reject(arguments: dict[str, Any]) -> dict[str, Any]:
    repo = _resolve_repo_root(arguments.get("project_root"))
    drafts_dir = _drafts_dir(repo)
    plans_dir = _plans_dir(repo)
    filename = arguments.get("filename")
    slug = arguments.get("slug")
    fn = filename if isinstance(filename, str) and filename.strip() else None
    sl = slug if isinstance(slug, str) and slug.strip() else None
    reason = arguments.get("rejection_reason")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("'rejection_reason' must be a non-empty string")
    actor = arguments.get("actor") or _default_actor()
    path = _find_plan_path(drafts_dir, fn, sl, extra_dirs=[plans_dir])
    if is_folder_plan(path):
        meta = load_folder_meta(path)
        meta["status"] = "rejected"
        meta["rejection_reason"] = reason.strip()
        meta["rejected_at"] = _utc_iso()
        meta["rejected_by"] = str(actor)
        save_folder_meta(path, meta)
        return {
            "status": "ok",
            "path": str(path),
            "rejection_reason": reason.strip(),
            "rejected_by": str(actor),
        }
    raw = path.read_text(encoding="utf-8")
    meta, body = _split_front_matter(raw)
    meta["status"] = "rejected"
    meta["rejection_reason"] = reason.strip()
    meta["rejected_at"] = _utc_iso()
    meta["rejected_by"] = str(actor)
    path.write_text(_compose_plan(meta, body.lstrip("\n")), encoding="utf-8")
    return {
        "status": "ok",
        "path": str(path),
        "rejection_reason": reason.strip(),
        "rejected_by": str(actor),
    }


def _call_plan_publish(arguments: dict[str, Any]) -> dict[str, Any]:
    repo = _resolve_repo_root(arguments.get("project_root"))
    drafts_dir = _drafts_dir(repo)
    plans_dir = _plans_dir(repo)
    filename = arguments.get("filename")
    slug = arguments.get("slug")
    force = bool(arguments.get("force", False))
    fn = filename if isinstance(filename, str) and filename.strip() else None
    sl = slug if isinstance(slug, str) and slug.strip() else None
    draft_path = _find_plan_path(drafts_dir, fn, sl)
    if is_folder_plan(draft_path):
        return uiplan_publish_folder(
            repo,
            draft_path,
            force=force,
            utc_iso_fn=_utc_iso,
            regen_plan_index=_regen_plan_index,
        )
    raw = draft_path.read_text(encoding="utf-8")
    meta, body = _split_front_matter(raw)
    if meta.get("status") != "accepted":
        return {
            "status": "blocked",
            "reason": "not_accepted",
            "message": (
                f"Plan status is {meta.get('status')!r}; accept it via "
                "uipath_plan_accept before publishing."
            ),
        }
    plans_dir.mkdir(parents=True, exist_ok=True)
    target = _safe_plan_path(plans_dir, draft_path.name)
    if target.exists() and not force:
        return {
            "status": "blocked",
            "reason": "target_exists",
            "message": f"{target} exists; pass force=true to overwrite.",
        }
    meta["published_at"] = _utc_iso()
    draft_path.write_text(_compose_plan(meta, body.lstrip("\n")), encoding="utf-8")
    target.write_text(_compose_plan(meta, body.lstrip("\n")), encoding="utf-8")
    idx = _regen_plan_index(repo)
    return {
        "status": "ok",
        "published": str(target),
        "draft": str(draft_path),
        "published_at": meta["published_at"],
        "index_regen": idx,
    }


def require_accepted_plan(project_dir: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Return ``{allowed, reason, plan}`` for the optional ``UIPATH_PLAN_GATE``.

    - Gate is off unless ``UIPATH_PLAN_GATE=1``; when off, always returns allowed.
    - When on, searches ``.cursor/plans/`` then ``docs/plans/`` under
      ``project_dir`` (or cwd) for any plan whose status is ``accepted``.
    """
    enabled = os.environ.get("UIPATH_PLAN_GATE", "0") == "1"
    if not enabled:
        return {"allowed": True, "enforced": False, "reason": "gate_disabled"}
    repo = _resolve_repo_root(str(project_dir) if project_dir else None)
    for directory in (_drafts_dir(repo), _plans_dir(repo)):
        if not directory.is_dir():
            continue
        for p in directory.glob("*.md"):
            if p.name in _SKIP_LIST:
                continue
            try:
                raw = p.read_text(encoding="utf-8")
                meta, _ = _split_front_matter(raw)
            except Exception:
                continue
            if str(meta.get("status")) == "accepted":
                return {
                    "allowed": True,
                    "enforced": True,
                    "plan": str(p),
                    "slug": meta.get("slug"),
                }
        for sub in directory.iterdir():
            if not sub.is_dir() or sub.name.startswith("."):
                continue
            if not is_folder_plan(sub):
                continue
            try:
                meta = load_folder_meta(sub)
            except Exception:
                continue
            if str(meta.get("status")) == "accepted":
                return {
                    "allowed": True,
                    "enforced": True,
                    "plan": str(sub),
                    "slug": meta.get("slug"),
                }
    return {
        "allowed": False,
        "enforced": True,
        "reason": "no_accepted_plan",
        "message": (
            "UIPATH_PLAN_GATE=1 and no accepted plan exists under .cursor/plans/ "
            "or docs/plans/. Accept one via uipath_plan_accept."
        ),
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
    if name == "uipath_plan_new":
        return _call_plan_new(arguments)
    if name == "uipath_plan_brainstorm":
        return _call_plan_brainstorm(arguments)
    if name == "uipath_plan_refine":
        return _call_plan_refine(arguments)
    if name == "uipath_plan_diff":
        return _call_plan_diff(arguments)
    if name == "uipath_plan_accept":
        return _call_plan_accept(arguments)
    if name == "uipath_plan_reject":
        return _call_plan_reject(arguments)
    if name == "uipath_plan_publish":
        return _call_plan_publish(arguments)
    if name == "uipath_plan_ground":
        return call_uiplan_ground(arguments)
    if name == "uipath_plan_spec_new":
        return call_uiplan_spec_new(arguments)
    if name == "uipath_plan_plan_new":
        return call_uiplan_plan_new(arguments)
    if name == "uipath_plan_tasks_new":
        return call_uiplan_tasks_new(arguments)
    if name == "uipath_plan_review":
        return call_uiplan_review(arguments)
    if name == "uipath_plan_uiplan_new":
        return call_uiplan_new(arguments)
    raise ValueError(f"Unknown plan tool: {name}")
