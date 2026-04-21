"""UiPlan structured review (spec-kit + superpowers-style checks)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

Stage = Literal["spec", "plan", "tasks", "all"]

_SKILL_CITE = re.compile(r"\[skill:([a-z0-9-]+)\]", re.IGNORECASE)
_TEMPLATE_CITE = re.compile(r"\[template:([^\]]+)\]")


def _finding(
    severity: str,
    stage: str,
    rule: str,
    message: str,
    where: str = "",
) -> dict[str, Any]:
    return {
        "severity": severity,
        "stage": stage,
        "rule": rule,
        "message": message,
        "where": where,
    }


_PLACEHOLDER_BAN = re.compile(
    r"\b(TBD|TODO|implement later|fill in|FIXME|NEEDS CLARIFICATION)\b",
    re.IGNORECASE,
)


def review_spec_text(spec: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if "[NEEDS CLARIFICATION" in spec or "[needs clarification" in spec.lower():
        findings.append(
            _finding(
                "error",
                "spec",
                "no_needs_clarification",
                "Unresolved NEEDS CLARIFICATION markers remain in spec.md.",
                "spec.md",
            )
        )
    if "Priority: P1" not in spec:
        findings.append(
            _finding(
                "warn",
                "spec",
                "p1_story",
                "No User Story marked Priority: P1 (MVP).",
                "spec.md",
            )
        )
    if "**Given**" not in spec or "**When**" not in spec or "**Then**" not in spec:
        findings.append(
            _finding(
                "warn",
                "spec",
                "acceptance_format",
                "Add Given/When/Then acceptance scenarios for MVP story.",
                "spec.md",
            )
        )
    frs = re.findall(r"\*\*FR-\d+\*\*:\s*(.+)", spec)
    for fr in frs:
        t = fr.strip()
        if not (t.startswith("System MUST") or t.startswith("Users MUST")):
            findings.append(
                _finding(
                    "warn",
                    "spec",
                    "fr_format",
                    f"Functional requirement should start with System MUST or Users MUST: {t[:80]}...",
                    "spec.md",
                )
            )
            break
    if "**SC-001**" not in spec:
        findings.append(
            _finding(
                "warn",
                "spec",
                "success_criteria",
                "Add measurable SC-001 under Success Criteria.",
                "spec.md",
            )
        )
    return findings


def review_plan_text(plan: str, gate_ids: list[str]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if "NEEDS CLARIFICATION" in plan:
        findings.append(
            _finding(
                "error",
                "plan",
                "tech_context_clear",
                "plan.md Technical Context still contains NEEDS CLARIFICATION.",
                "plan.md",
            )
        )
    if "**Structure Decision**" in plan:
        sd = plan.split("**Structure Decision**", 1)[1]
        if len(sd.strip()) < 20:
            findings.append(
                _finding(
                    "warn",
                    "plan",
                    "structure_decision",
                    "Expand Structure Decision with concrete paths.",
                    "plan.md",
                )
            )
    for gid in gate_ids:
        if gid and gid not in plan:
            findings.append(
                _finding(
                    "warn",
                    "plan",
                    "constitution_gate",
                    f"Constitution gate id '{gid}' not referenced in plan.md checklist.",
                    "plan.md",
                )
            )
    return findings


_TASK_LINE = re.compile(
    r"^\s*-\s*\[\s*\]\s*(T\d+)(?:\s+\[P\])?\s+\[US(\d+)\]",
    re.MULTILINE,
)


def review_tasks_text(tasks: str, spec: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for m in _PLACEHOLDER_BAN.finditer(tasks):
        findings.append(
            _finding(
                "error",
                "tasks",
                "no_placeholder",
                f"Banned placeholder phrase in tasks: {m.group(0)}",
                "tasks.md",
            )
        )
        break
    story_nums = set(re.findall(r"###\s*User Story\s+(\d+)\s*-", spec))
    task_lines = _TASK_LINE.findall(tasks)
    if not task_lines:
        findings.append(
            _finding(
                "warn",
                "tasks",
                "task_ids",
                "No tasks matching format '- [ ] Tnn [P?] [USn] ...' found.",
                "tasks.md",
            )
        )
    for tid, us in task_lines:
        if us not in story_nums and story_nums:
            findings.append(
                _finding(
                    "warn",
                    "tasks",
                    "us_trace",
                    f"Task {tid} references US{us} but spec may not define that story.",
                    "tasks.md",
                )
            )
    # TDD pairing heuristic: each "### Implementation" section should follow "### Tests"
    if "### Tests" not in tasks and "Tests for User Story" not in tasks:
        findings.append(
            _finding(
                "warn",
                "tasks",
                "tdd_sections",
                "Add explicit 'Tests for User Story' section before implementation tasks.",
                "tasks.md",
            )
        )
    return findings


def review_citations(combined: str, repo: Path) -> list[dict[str, Any]]:
    """Resolve ``[skill:name]`` and ``[template:path]`` citations when possible."""
    from uipath_claude.skills.registry import SkillRegistry

    findings: list[dict[str, Any]] = []
    reg = SkillRegistry(project_root=repo)
    reg.load_skills()
    known = {str(s.get("name")) for s in reg.skills if s.get("name")}
    for m in _SKILL_CITE.finditer(combined):
        name = m.group(1)
        if name not in known:
            findings.append(
                _finding(
                    "warn",
                    "cross",
                    "citation_skill",
                    f"[skill:{name}] not found in SkillRegistry.",
                    "citations",
                )
            )
    root = repo.resolve()
    for m in _TEMPLATE_CITE.finditer(combined):
        rel = m.group(1).strip().rstrip("/")
        p = (repo / rel).resolve()
        try:
            p.relative_to(root)
        except ValueError:
            findings.append(
                _finding(
                    "warn",
                    "cross",
                    "citation_template",
                    f"[template:{rel}] resolves outside repo root.",
                    "citations",
                )
            )
            continue
        if not p.exists():
            findings.append(
                _finding(
                    "info",
                    "cross",
                    "citation_template",
                    f"[template:{rel}] path not found on disk (may be conceptual).",
                    "citations",
                )
            )
    return findings


def review_duplicate_uiplan_slug(repo: Path, slug: str) -> list[dict[str, Any]]:
    """Warn when more than one draft UiPlan folder shares the same slug."""
    import yaml as _yaml

    drafts: list[str] = []
    base = repo / ".cursor" / "plans"
    if not base.is_dir():
        return []
    for sub in base.iterdir():
        if not sub.is_dir():
            continue
        mp = sub / ".meta.yaml"
        if not mp.is_file():
            continue
        try:
            meta = _yaml.safe_load(mp.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        if str(meta.get("plan_kind", "")) != "uiplan":
            continue
        if str(meta.get("slug", "")) != slug:
            continue
        drafts.append(sub.name)
    if len(drafts) > 1:
        return [
            _finding(
                "warn",
                "cross",
                "duplicate_uiplan",
                f"Multiple draft UiPlan folders for slug {slug!r}: {', '.join(sorted(drafts))}",
                "cross",
            )
        ]
    return []


def review_cross(spec: str, plan: str, tasks: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    fr_labels = re.findall(r"\*\*(FR-\d+)\*\*", spec)
    for fr in fr_labels:
        if fr not in tasks and fr.lower() not in tasks.lower():
            findings.append(
                _finding(
                    "warn",
                    "cross",
                    "fr_coverage",
                    f"{fr} from spec.md has no obvious trace in tasks.md.",
                    "cross",
                )
            )
    # Paths in tasks should appear in plan structure block
    paths = re.findall(r"`([^\s`]+\.(?:py|cs|xaml|md|json))`", tasks)
    for p in paths[:15]:
        if p and p not in plan:
            findings.append(
                _finding(
                    "info",
                    "cross",
                    "path_in_plan",
                    f"Task references `{p}` — confirm it appears in plan.md Project Structure.",
                    "cross",
                )
            )
    return findings


def run_uiplan_review(
    *,
    spec: str,
    plan: str,
    tasks: str,
    stage: Stage,
    gate_ids: list[str] | None = None,
    repo: Path | None = None,
    slug: str | None = None,
) -> dict[str, Any]:
    gate_ids = gate_ids or []
    findings: list[dict[str, Any]] = []
    if stage in ("spec", "all"):
        findings.extend(review_spec_text(spec))
    if stage in ("plan", "all"):
        findings.extend(review_plan_text(plan, gate_ids))
    if stage in ("tasks", "all"):
        findings.extend(review_tasks_text(tasks, spec))
    if stage in ("all",):
        findings.extend(review_cross(spec, plan, tasks))
        if repo is not None:
            findings.extend(review_citations("\n".join((spec, plan, tasks)), repo))
            if slug:
                findings.extend(review_duplicate_uiplan_slug(repo, slug))
    errors = [f for f in findings if f.get("severity") == "error"]
    ok = len(errors) == 0
    next_action = (
        "Address error-severity findings and re-run uipath_plan_review."
        if not ok
        else "Optional: resolve warnings; then uipath_plan_accept when ready."
    )
    return {
        "ok": ok,
        "stage": stage,
        "findings": findings,
        "next_action": next_action,
    }
