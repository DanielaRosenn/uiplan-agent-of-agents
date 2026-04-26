"""UiPlan structured review (spec-kit + superpowers-style checks)."""
from __future__ import annotations

import re
import importlib.util
from pathlib import Path
from typing import Any, Literal

try:
    from tools.uiplan.paradigms import KNOWN_PARADIGMS, cli_family
except ModuleNotFoundError:
    _PARADIGM_PATH = Path(__file__).resolve().parents[3] / "tools" / "uiplan" / "paradigms.py"
    _spec = importlib.util.spec_from_file_location("uiplan_paradigms", _PARADIGM_PATH)
    if _spec is None or _spec.loader is None:
        raise
    _module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_module)
    KNOWN_PARADIGMS = _module.KNOWN_PARADIGMS
    cli_family = _module.cli_family
from uipath_claude.skills.activity_docs import get_activity_doc

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
_ACTIVITY_TAG_RE = re.compile(r"\[activity:([A-Za-z0-9_.]+):([A-Za-z][A-Za-z0-9_]*)\]")
_PATH_TOKEN_RE = re.compile(r"`[^`]+\.(?:xaml|cs|py|json|md|yml|yaml|ts|tsx)`")
_GROUNDING_TOKEN_RE = re.compile(
    r"\[skill:|\[library:|\[askai:|\[agent:|uipath_library_lookup|uipath_library_search|"
    r"query_uipath_docs|uipath_doc_get_activity|uipath_doc_list_packages",
    re.IGNORECASE,
)
_LIBRARY_TOOL_RE = re.compile(r"uipath_library_(lookup|search)", re.IGNORECASE)
_PER_LINE_IMPL_GROUND = re.compile(
    r"\[skill:|\[library:|\[askai:|\[agent:|uipath_library_lookup|uipath_library_search|"
    r"query_uipath_docs|uipath_doc_get_activity|uipath_doc_list_packages",
    re.IGNORECASE,
)
_RESOURCE_TOKEN_RE = re.compile(r"\b(queue|asset|bucket|folder|orchestrator|binding)\b", re.IGNORECASE)
_CLI_TOKEN_RE = re.compile(r"\b(uipcli|uipath|uip)\b")

_KNOWN_PARADIGM_SET = {p for p in KNOWN_PARADIGMS if p != "unknown"}
_EXPECTED_DESCRIPTORS: dict[str, tuple[str, ...]] = {
    "modern-rpa": ("project.json", "Main.xaml"),
    "coded-automation": ("project.json", ".cs"),
    "coded-agent": ("pyproject.toml", "langgraph.json"),
    "solution": ("solution.uipx", "bindings"),
    "maestro-flow": (".bpmn", ".flow"),
    "coded-app": ("app.config.json", "action-schema.json"),
    "api-workflow": ("api-workflow.json",),
    "case-management": ("caseplan.json",),
    "library": ("project.json", "Activities/"),
    "tests": ("Tests/",),
}


def _declared_paradigm(spec: str) -> str | None:
    m = re.search(r"\*\*Implementation paradigm\*\*:\s*([^\n]+)", spec, flags=re.IGNORECASE)
    if not m:
        return None
    value = m.group(1).strip().strip("`").lower()
    if value in _KNOWN_PARADIGM_SET:
        return value
    return None


def review_spec_text(spec: str, repo: Path | None = None) -> list[dict[str, Any]]:
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
    if "## Development Handoff" not in spec:
        findings.append(
            _finding(
                "error",
                "spec",
                "development_handoff",
                "Add a Development Handoff section so accepted designs can become build-ready work.",
                "spec.md",
            )
        )
    if "tasks.md" not in spec or "uipath_plan_review" not in spec:
        findings.append(
            _finding(
                "error",
                "spec",
                "build_handoff_gate",
                "Development Handoff must name tasks.md and the review/acceptance gate before source changes.",
                "spec.md",
            )
        )
    paradigm = _declared_paradigm(spec)
    if paradigm is None:
        findings.append(
            _finding(
                "error",
                "spec",
                "paradigm_declared",
                "Development Handoff must declare a known implementation paradigm.",
                "spec.md",
            )
        )
    if "**CLI family**" not in spec:
        findings.append(
            _finding(
                "error",
                "spec",
                "cli_family_declared",
                "Development Handoff must declare CLI family (uipcli, uipath, or uip).",
                "spec.md",
            )
        )
    if not _LIBRARY_TOOL_RE.search(spec):
        findings.append(
            _finding(
                "warn",
                "spec",
                "feasibility_lookup",
                "Development Handoff should name `uipath_library_search` and/or "
                "`uipath_library_lookup` before locking APIs.",
                "spec.md",
            )
        )
    if "query_uipath_docs" not in spec and "[askai:" not in spec.lower():
        findings.append(
            _finding(
                "warn",
                "spec",
                "feasibility_lookup",
                "Development Handoff should include AskAI-style fallback (`query_uipath_docs` or `[askai:]`).",
                "spec.md",
            )
        )
    if "uipath_doc_get_activity" not in spec.lower():
        findings.append(
            _finding(
                "warn",
                "spec",
                "activity_doc_routing",
                "Development Handoff should cite `uipath_doc_get_activity` (or list packages) "
                "when activity-level detail may be needed.",
                "spec.md",
            )
        )
    if repo is not None:
        ctx = repo / ".claude" / "rules" / "project-context.md"
        if not ctx.is_file() and "uipath-project-discovery-agent" not in spec.lower():
            findings.append(
                _finding(
                    "warn",
                    "spec",
                    "discovery_precheck",
                    "project-context.md is missing; cite `[agent:uipath-project-discovery-agent]` "
                    "in the spec until discovery completes.",
                    "spec.md",
                )
            )
    return findings


def review_plan_text(
    plan: str,
    gate_ids: list[str],
    paradigm: str | None,
    repo: Path | None = None,
) -> list[dict[str, Any]]:
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
    if "## Development execution contract" not in plan:
        findings.append(
            _finding(
                "error",
                "plan",
                "development_execution_contract",
                "Add a Development execution contract that defines how accepted plans become implementation work.",
                "plan.md",
            )
        )
    if "### Source Code (repository root)" not in plan:
        findings.append(
            _finding(
                "error",
                "plan",
                "code_structure_present",
                "Plan must include a source code structure section.",
                "plan.md",
            )
        )
    if "### Paradigm build loop" not in plan:
        findings.append(
            _finding(
                "error",
                "plan",
                "build_loop_present",
                "Plan must include a paradigm-specific build loop section.",
                "plan.md",
            )
        )
    if "## Planner Route & Specialist Handoff" not in plan:
        findings.append(
            _finding(
                "error",
                "plan",
                "planner_route_heading",
                "plan.md must include `## Planner Route & Specialist Handoff` (contract routing).",
                "plan.md",
            )
        )
    if "uipath-project-discovery-agent" not in plan.lower() and "project-context.md" not in plan.lower():
        findings.append(
            _finding(
                "warn",
                "plan",
                "discovery_route",
                "plan.md should cite `[agent:uipath-project-discovery-agent]` or `.claude/rules/project-context.md`.",
                "plan.md",
            )
        )
    if not _LIBRARY_TOOL_RE.search(plan):
        findings.append(
            _finding(
                "warn",
                "plan",
                "library_route",
                "plan.md should explicitly name `uipath_library_search` and/or `uipath_library_lookup`.",
                "plan.md",
            )
        )
    if "uipath_doc_get_activity" not in plan.lower():
        findings.append(
            _finding(
                "warn",
                "plan",
                "activity_doc_route",
                "plan.md should mention `uipath_doc_get_activity` when workflows touch activities.",
                "plan.md",
            )
        )
    skill_cites = len(_SKILL_CITE.findall(plan))
    if skill_cites < 2:
        findings.append(
            _finding(
                "warn",
                "plan",
                "specialist_skills",
                "plan.md should cite at least two `[skill:...]` tokens (planner plus a specialist).",
                "plan.md",
            )
        )
    if paradigm:
        required = _EXPECTED_DESCRIPTORS.get(paradigm, ())
        missing = [item for item in required if item not in plan]
        if missing:
            findings.append(
                _finding(
                    "error",
                    "plan",
                    "code_structure_present",
                    f"Plan is missing descriptor hints for paradigm {paradigm}: {', '.join(missing)}.",
                    "plan.md",
                )
            )
        expected_cli = cli_family(paradigm).split()[0]
        if expected_cli in ("uipcli", "uipath", "uip") and expected_cli not in plan:
            findings.append(
                _finding(
                    "error",
                    "plan",
                    "build_loop_present",
                    f"Plan does not mention expected CLI family `{expected_cli}` for paradigm `{paradigm}`.",
                    "plan.md",
                )
            )
    return findings


_TASK_LINE = re.compile(
    r"^\s*-\s*\[\s*\]\s*(T\d+)(?:\s+\[P\])?\s+\[US(\d+)\]",
    re.MULTILINE,
)


def _review_implementation_task_routing(tasks: str) -> list[dict[str, Any]]:
    """Each non-[P] checklist line under ### Implementation should cite routing evidence."""
    findings: list[dict[str, Any]] = []
    in_impl = False
    for line in tasks.splitlines():
        stripped = line.strip()
        if stripped.startswith("### Implementation"):
            in_impl = True
            continue
        if stripped.startswith("### ") and in_impl and "Implementation" not in stripped:
            in_impl = False
        if not in_impl:
            continue
        m = re.match(r"^\s*-\s*\[\s*\]\s*(T\d+)", line)
        if not m:
            continue
        if "[P]" in line:
            continue
        if not _PER_LINE_IMPL_GROUND.search(line):
            findings.append(
                _finding(
                    "warn",
                    "tasks",
                    "task_implementation_grounding",
                    f"Task {m.group(1)} should cite grounding (skill/agent/library/AskAI tokens or "
                    f"uipath_library_search / uipath_library_lookup / query_uipath_docs / uipath_doc_*).",
                    "tasks.md",
                )
            )
    return findings


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
    if "## Phase 5: Build, Verify, and Handoff" not in tasks:
        findings.append(
            _finding(
                "error",
                "tasks",
                "build_verify_handoff_phase",
                "Add a final Build, Verify, and Handoff phase so implementation continues after planning.",
                "tasks.md",
            )
        )
    if not _PATH_TOKEN_RE.search(tasks):
        findings.append(
            _finding(
                "error",
                "tasks",
                "tasks_have_artifacts",
                "Tasks must include explicit artifact paths in backticks.",
                "tasks.md",
            )
        )
    if not _GROUNDING_TOKEN_RE.search(tasks):
        findings.append(
            _finding(
                "error",
                "tasks",
                "feasibility_grounding",
                "Tasks must cite feasibility grounding ([skill:], library, askai, or lookup tools).",
                "tasks.md",
            )
        )
    if not (_RESOURCE_TOKEN_RE.search(tasks) and _CLI_TOKEN_RE.search(tasks)):
        findings.append(
            _finding(
                "warn",
                "tasks",
                "tasks_have_artifacts",
                "Tasks should include UiPath resources (queues/assets/folders/bindings) and concrete CLI verbs.",
                "tasks.md",
            )
        )
    if "personal workspace" not in tasks.lower() or "production" not in tasks.lower():
        findings.append(
            _finding(
                "error",
                "tasks",
                "deploy_gate",
                "Tasks must state personal workspace default and Production approval gate.",
                "tasks.md",
            )
        )
    findings.extend(_review_implementation_task_routing(tasks))
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
    paradigm = _declared_paradigm(spec)
    if stage in ("spec", "all"):
        findings.extend(review_spec_text(spec, repo))
    if stage in ("plan", "all"):
        findings.extend(review_plan_text(plan, gate_ids, paradigm, repo))
    if stage in ("tasks", "all"):
        findings.extend(review_tasks_text(tasks, spec))
    if stage in ("all",):
        findings.extend(review_cross(spec, plan, tasks))
        for pkg, act in _ACTIVITY_TAG_RE.findall("\n".join((spec, plan, tasks))):
            if not get_activity_doc(pkg, act, None):
                findings.append(
                    _finding(
                        "warn",
                        "cross",
                        "no_invented_activities",
                        f"Activity tag [{pkg}:{act}] could not be resolved in activity docs.",
                        "cross",
                    )
                )
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
