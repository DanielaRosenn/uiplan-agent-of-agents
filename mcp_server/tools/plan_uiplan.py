"""UiPlan MCP actions: ground, spec/plan/tasks generation, review, orchestrator."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from mcp_server.tools.plan_constitution import load_constitution
from mcp_server.tools.plan_folder import (
    is_folder_plan,
    load_folder_meta,
    resolve_plan_path,
    save_folder_meta,
    read_uiplan_files,
)
from mcp_server.tools.plan_grounding import build_grounding_pack
from mcp_server.tools.plan_uiplan_review import run_uiplan_review


def _template_dir(repo: Path) -> Path:
    return repo / "docs" / "plans" / "_uiplan"


def _fill(tpl: str, mapping: dict[str, str]) -> str:
    out = tpl
    for k, v in mapping.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def _load_tpl(repo: Path, name: str) -> str:
    p = _template_dir(repo) / name
    if not p.is_file():
        raise FileNotFoundError(f"UiPlan template missing: {p}")
    return p.read_text(encoding="utf-8")


def _gate_ids(repo: Path) -> list[str]:
    const = load_constitution(repo)
    return [str(g.get("id", "")) for g in const.get("gates", []) if g.get("id")]


def call_uiplan_ground(arguments: dict[str, Any]) -> dict[str, Any]:
    from mcp_server.tools.plan_tools import _resolve_repo_root  # noqa: PLC0415

    repo = _resolve_repo_root(arguments.get("project_root"))
    topic = arguments.get("topic") or arguments.get("intent") or ""
    if not isinstance(topic, str) or not topic.strip():
        raise ValueError("'topic' must be a non-empty string")
    return build_grounding_pack(repo, topic.strip())


def _ensure_slug(arguments: dict[str, Any], title: str) -> str:
    from mcp_server.tools.plan_tools import _SLUG_RE, _derive_slug  # noqa: PLC0415

    slug_in = arguments.get("slug")
    slug = slug_in if isinstance(slug_in, str) and slug_in.strip() else _derive_slug(title)
    if not _SLUG_RE.match(slug):
        raise ValueError("slug must be lowercase [a-z0-9-], start alphanumeric, length 2-121")
    return slug


def call_uiplan_spec_new(arguments: dict[str, Any]) -> dict[str, Any]:
    from mcp_server.tools.plan_tools import (  # noqa: PLC0415
        _PROJECT_TYPES,
        _default_actor,
        _drafts_dir,
        _resolve_repo_root,
        _today_iso,
    )

    repo = _resolve_repo_root(arguments.get("project_root"))
    title = str(arguments.get("title", "")).strip()
    intent = str(arguments.get("intent", arguments.get("topic", title))).strip()
    if not title:
        raise ValueError("'title' must be a non-empty string")
    if not intent:
        raise ValueError("'intent' or 'topic' must be a non-empty string")
    slug = _ensure_slug(arguments, title)
    owner = arguments.get("owner") or _default_actor()
    project_type = arguments.get("project_type") or "mixed"
    if project_type not in _PROJECT_TYPES:
        raise ValueError(f"project_type must be one of: {', '.join(sorted(_PROJECT_TYPES))}")

    pack_in = arguments.get("grounding_pack")
    if isinstance(pack_in, dict) and pack_in.get("status") == "ok":
        pack = pack_in
    else:
        pack = build_grounding_pack(repo, intent)

    date = _today_iso()
    folder_name = f"{date}-{slug}"
    drafts = _drafts_dir(repo)
    folder = drafts / folder_name
    if folder.exists():
        raise FileExistsError(f"UiPlan folder already exists: {folder}")

    cites = " ".join(pack.get("suggested_citations") or [])

    tpl = _load_tpl(repo, "_spec-template.md")
    mapping = {
        "TITLE": title,
        "DATE": date,
        "INTENT": intent,
        "GROUNDING_CITATIONS": cites or "[skill:uipath-planner]",
        "US1_TITLE": "MVP slice",
        "US1_BODY": f"Deliver the core outcome for: {intent}",
        "US1_PRIORITY": "Highest user value first.",
        "US1_TEST": "Describe how to verify independently (command + fixture).",
        "US1_GIVEN_1": "initial state",
        "US1_WHEN_1": "action",
        "US1_THEN_1": "expected outcome",
        "US2_TITLE": "Secondary slice",
        "US2_BODY": "Follow-on behavior after MVP.",
        "US2_PRIORITY": "Lower volume or dependency on MVP.",
        "US2_TEST": "Independent verification steps.",
        "US2_GIVEN_1": "initial state",
        "US2_WHEN_1": "action",
        "US2_THEN_1": "expected outcome",
        "EDGE_1": "Describe primary edge case.",
        "FR_001": f"support the outcome described in intent ({intent[:120]})",
        "FR_002": "log decisions for auditability",
        "FR_003": "operate within tenant security constraints",
        "ENTITY_1": "PrimaryEntity",
        "ENTITY_1_DESC": "Core business object for this feature.",
        "SC_001": "Measurable outcome tied to intent (latency, accuracy, volume).",
        "ASSUMPTION_1": "List environment assumptions (Orchestrator folder, assets, etc.).",
    }
    spec_body = _fill(tpl, mapping)

    folder.mkdir(parents=True)
    meta = {
        "slug": slug,
        "title": title,
        "date": date,
        "status": "draft",
        "owner": str(owner),
        "project_type": project_type,
        "plan_kind": "uiplan",
        "linked_pdd": "",
        "accepted_at": None,
        "accepted_by": None,
        "rejection_reason": None,
        "published_at": None,
        "supersedes": None,
    }
    save_folder_meta(folder, meta)
    (folder / "spec.md").write_text(spec_body, encoding="utf-8")
    return {
        "status": "ok",
        "path": str(folder),
        "relative": str(folder.relative_to(repo)),
        "slug": slug,
        "folder_name": folder_name,
        "grounding_pack": pack,
    }


def call_uiplan_plan_new(arguments: dict[str, Any]) -> dict[str, Any]:
    from mcp_server.tools.plan_tools import _drafts_dir, _plans_dir, _resolve_repo_root, _today_iso  # noqa: PLC0415

    repo = _resolve_repo_root(arguments.get("project_root"))
    slug = _ensure_slug(arguments, arguments.get("title") or "plan")
    drafts = _drafts_dir(repo)
    plans = _plans_dir(repo)
    resolved = resolve_plan_path(drafts, None, slug, extra_dirs=[plans])
    if resolved.kind != "folder" or not is_folder_plan(resolved.path):
        raise ValueError("uipath_plan_plan_new requires an existing UiPlan folder draft (run uipath_plan_spec_new first)")
    folder = resolved.path
    files = read_uiplan_files(resolved)
    spec = files.get("spec.md", "")
    if not spec.strip():
        raise ValueError("spec.md is empty")

    pack = arguments.get("grounding_pack")
    if not isinstance(pack, dict) or pack.get("status") != "ok":
        pack = build_grounding_pack(repo, spec[:500])

    meta = load_folder_meta(folder)
    title = str(meta.get("title", slug))
    date = str(meta.get("date", _today_iso()))
    folder_name = folder.name
    cites = " ".join(pack.get("suggested_citations") or [])

    gate_lines = []
    for g in pack.get("constitution", {}).get("gates", []):
        gid = str(g.get("id", ""))
        txt = str(g.get("text", ""))
        gate_lines.append(f"- [ ] **{gid}**: {txt}")
    constitution_checklist = "\n".join(gate_lines) if gate_lines else "- [ ] **gates**: review CLAUDE.md"

    tpl = _load_tpl(repo, "_plan-template.md")
    tmpl_hint = str(pack.get("candidate_project_template", "templates/long-running/"))
    mapping = {
        "TITLE": title,
        "DATE": date,
        "GROUNDING_CITATIONS": cites,
        "SUMMARY": f"Implementation approach derived from spec for {title}.",
        "LANG_VERSION": "C# 12 / .NET 8 (Modern) or Python 3.11+ for coded agents — adjust per project-context.",
        "DEPS": "UiPath.* activities / SDK per project-context.",
        "STORAGE": "Orchestrator queues, assets, or Data Fabric — specify in Structure Decision.",
        "TESTING": "uipcli test run / pytest per paradigm.",
        "TARGET_PLATFORM": "Automation Cloud / Windows robots — confirm in project-context.",
        "PROJECT_TYPE": str(meta.get("project_type", "mixed")),
        "PERF": "State domain targets (e.g. P95 latency).",
        "CONSTRAINTS": "PII, residency, change windows.",
        "SCALE": "Volumes, concurrency, retention.",
        "CONSTITUTION_CHECKLIST": constitution_checklist,
        "FOLDER_NAME": folder_name,
        "SOURCE_TREE": f"{tmpl_hint}\n  (mirror template tree under your process project directory)",
        "STRUCTURE_DECISION": f"Start from {tmpl_hint} and adjust paths to match repo layout.",
        "COMPLEXITY_TABLE": "_None — add rows only if a constitution gate is violated._",
    }
    plan_body = _fill(tpl, mapping)
    (folder / "plan.md").write_text(plan_body, encoding="utf-8")
    return {"status": "ok", "path": str(folder / "plan.md"), "slug": slug}


def call_uiplan_tasks_new(arguments: dict[str, Any]) -> dict[str, Any]:
    from mcp_server.tools.plan_tools import _drafts_dir, _plans_dir, _resolve_repo_root  # noqa: PLC0415

    repo = _resolve_repo_root(arguments.get("project_root"))
    slug = _ensure_slug(arguments, arguments.get("title") or "plan")
    drafts = _drafts_dir(repo)
    plans = _plans_dir(repo)
    resolved = resolve_plan_path(drafts, None, slug, extra_dirs=[plans])
    if resolved.kind != "folder" or not is_folder_plan(resolved.path):
        raise ValueError("uipath_plan_tasks_new requires a UiPlan folder with spec.md and plan.md")
    folder = resolved.path
    files = read_uiplan_files(resolved)
    spec = files.get("spec.md", "")
    plan = files.get("plan.md", "")
    if not plan.strip():
        raise ValueError("plan.md is empty — run uipath_plan_plan_new first")

    pack = arguments.get("grounding_pack")
    if not isinstance(pack, dict) or pack.get("status") != "ok":
        pack = build_grounding_pack(repo, spec[:500])

    meta = load_folder_meta(folder)
    title = str(meta.get("title", slug))
    cites = " ".join(pack.get("suggested_citations") or [])
    tpl = _load_tpl(repo, "_tasks-template.md")
    mapping = {
        "TITLE": title,
        "GROUNDING_CITATIONS": cites,
        "T001": "Scaffold project directories per plan.md Project Structure (list concrete mkdir paths).",
        "T002": "Restore/analyze pipeline green for the touched projects.",
        "US1_TITLE": "MVP slice",
        "US1_GOAL": "Deliver first usable increment from spec User Story 1.",
        "US1_IND_TEST": "Run the Independent Test from spec for US1.",
        "T010_TEST": "Write failing automated test covering US1 happy path (exact test file path from plan).",
        "T011_IMPL": "Minimal implementation to satisfy US1 (exact source paths from plan).",
        "T020": "Documentation + README updates for operators.",
        "DEPENDENCIES_TEXT": "Phase 1 -> Phase 2 -> US1 -> Polish. Tests before implementation within each story.",
    }
    tasks_body = _fill(tpl, mapping)
    (folder / "tasks.md").write_text(tasks_body, encoding="utf-8")
    return {"status": "ok", "path": str(folder / "tasks.md"), "slug": slug}


def call_uiplan_review(arguments: dict[str, Any]) -> dict[str, Any]:
    from mcp_server.tools.plan_tools import _drafts_dir, _plans_dir, _resolve_repo_root  # noqa: PLC0415

    repo = _resolve_repo_root(arguments.get("project_root"))
    slug = str(arguments.get("slug", "")).strip()
    if not slug:
        raise ValueError("'slug' is required")
    stage = arguments.get("stage") or "all"
    if stage not in ("spec", "plan", "tasks", "all"):
        raise ValueError("stage must be spec | plan | tasks | all")
    drafts = _drafts_dir(repo)
    plans = _plans_dir(repo)
    resolved = resolve_plan_path(drafts, None, slug, extra_dirs=[plans])
    if resolved.kind != "folder":
        raise ValueError("uipath_plan_review for UiPlan requires a folder-shaped draft")
    files = read_uiplan_files(resolved)
    gate_ids = _gate_ids(repo)
    return run_uiplan_review(
        spec=files.get("spec.md", ""),
        plan=files.get("plan.md", ""),
        tasks=files.get("tasks.md", ""),
        stage=stage,  # type: ignore[arg-type]
        gate_ids=gate_ids,
        repo=repo,
        slug=slug,
    )


def call_uiplan_new(arguments: dict[str, Any]) -> dict[str, Any]:
    title = str(arguments.get("title", "")).strip()
    intent = str(arguments.get("intent", arguments.get("topic", title))).strip()
    if not title or not intent:
        raise ValueError("'title' is required; provide intent/topic or reuse title as intent")
    merged = {**arguments, "title": title, "intent": intent}
    out_spec = call_uiplan_spec_new(merged)
    slug = out_spec["slug"]
    pack = out_spec.get("grounding_pack") or {}
    merged2 = {**arguments, "slug": slug, "grounding_pack": pack}
    out_plan = call_uiplan_plan_new(merged2)
    out_tasks = call_uiplan_tasks_new(merged2)
    review = call_uiplan_review({**arguments, "slug": slug, "stage": "all"})
    return {
        "status": "ok",
        "slug": slug,
        "folder": out_spec.get("path"),
        "spec_new": out_spec,
        "plan_new": out_plan,
        "tasks_new": out_tasks,
        "review": review,
    }


def uiplan_publish_folder(
    repo: Path,
    draft_folder: Path,
    *,
    force: bool,
    utc_iso_fn,
    regen_plan_index,
) -> dict[str, Any]:
    """Copy a UiPlan draft folder to docs/plans/."""
    from mcp_server.tools.plan_tools import _plans_dir  # noqa: PLC0415

    if not is_folder_plan(draft_folder):
        raise ValueError("not a UiPlan folder")
    meta = load_folder_meta(draft_folder)
    if str(meta.get("status")) != "accepted":
        return {
            "status": "blocked",
            "reason": "not_accepted",
            "message": "UiPlan folder must be accepted via uipath_plan_accept before publish.",
        }
    plans_dir = _plans_dir(repo)
    target = plans_dir / draft_folder.name
    if target.exists() and not force:
        return {
            "status": "blocked",
            "reason": "target_exists",
            "message": f"{target} exists; pass force=true to overwrite.",
        }
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(draft_folder, target)
    meta["published_at"] = utc_iso_fn()
    save_folder_meta(target, meta)
    save_folder_meta(draft_folder, meta)
    idx = regen_plan_index(repo)
    return {
        "status": "ok",
        "published": str(target),
        "draft": str(draft_folder),
        "published_at": meta["published_at"],
        "index_regen": idx,
    }


__all__ = [
    "call_uiplan_ground",
    "call_uiplan_spec_new",
    "call_uiplan_plan_new",
    "call_uiplan_tasks_new",
    "call_uiplan_review",
    "call_uiplan_new",
    "uiplan_publish_folder",
]
