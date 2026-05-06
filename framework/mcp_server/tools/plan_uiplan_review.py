"""UiPlan structured review (spec-kit + superpowers-style checks)."""
from __future__ import annotations

import re
import importlib.util
from collections import defaultdict
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
    r"\b(TBD|TODO|implement later|fill in|FIXME)\b",
    re.IGNORECASE,
)
_ACTIVITY_TAG_RE = re.compile(r"\[activity:([A-Za-z0-9_.]+):([A-Za-z][A-Za-z0-9_]*)\]")
_PATH_TOKEN_RE = re.compile(r"`[^`]+\.(?:xaml|cs|py|json|md|yml|yaml|ts|tsx)`")
_WORKFLOW_PATH_TOKEN_RE = re.compile(r"`([^`]+\.(?:xaml|flow|py|dmn))`", re.IGNORECASE)
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


_NEEDS_CLARIFICATION_RE = re.compile(
    r"\[NEEDS\s+CLARIFICATION:\s*([^\]]+)\]",
    re.IGNORECASE,
)
_SME_REVIEW_RE = re.compile(r"\[SME\s+REVIEW(?::\s*([^\]]+))?\]", re.IGNORECASE)

_CLARIFICATION_GROUP_ORDER: tuple[tuple[str, str], ...] = (
    ("mailboxes_routing", "Mailboxes and routing"),
    ("execution_triggers", "Execution triggers"),
    ("zip_integration", "Zip integration"),
    ("vendor_data", "Vendor data"),
    ("human_review", "Human review"),
    ("audit_retention", "Audit and retention"),
    ("security_links", "Security and links"),
    ("sla_escalation", "SLA and escalation"),
    ("sme_review", "SME review"),
    ("other", "Other open items"),
)


def _categorize_clarification_label(label: str) -> tuple[str, str]:
    """Map a NEEDS CLARIFICATION label slug to (group_id, group_title)."""
    low = label.lower().strip()
    rules: list[tuple[tuple[str, ...], tuple[str, str]]] = [
        (
            ("mailbox", "mailboxes", "il entity", "payable", "routing", "regional"),
            ("mailboxes_routing", "Mailboxes and routing"),
        ),
        (
            ("trigger", "schedule", "queue", "dispatcher", "analyzer", "review", "sweep"),
            ("execution_triggers", "Execution triggers"),
        ),
        (("zip", "invoice.ziphq", "forward", "api"), ("zip_integration", "Zip integration")),
        (("vendor", "supplier", "lookup key", "missing-vendor"), ("vendor_data", "Vendor data")),
        (("human", "action center", "notification", "channel"), ("human_review", "Human review")),
        (("audit", "retention", "body", "attachment", "sink", "siem", "blob"), ("audit_retention", "Audit and retention")),
        (("domain", "link", "document", "allow-list", "allowlist"), ("security_links", "Security and links")),
        (("sla", "escalation", "recipient"), ("sla_escalation", "SLA and escalation")),
    ]
    for keywords, pair in rules:
        if any(k in low for k in keywords):
            return pair
    return "other", "Other open items"


def _question_from_needs_line(line: str, marker_inner: str) -> str:
    """Turn a bullet line with [NEEDS CLARIFICATION: x] into a readable question."""
    m = _NEEDS_CLARIFICATION_RE.search(line)
    if not m:
        return f"Please confirm: {marker_inner.strip()}"
    tail = line[m.end() :].strip()
    for prefix in ("\u2014", "-", ":", "—"):
        if tail.startswith(prefix):
            tail = tail[len(prefix) :].strip()
    if tail and len(tail) > 3:
        if tail[0].islower():
            tail = tail[0].upper() + tail[1:]
        if not tail.endswith("?"):
            tail = tail.rstrip(".") + "?"
        return tail
    return f"Please confirm: {marker_inner.strip()}?"


def _parse_clarification_items(text: str, source: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line in text.splitlines():
        if "[NEEDS CLARIFICATION" in line.upper():
            m = _NEEDS_CLARIFICATION_RE.search(line)
            if not m:
                continue
            label = m.group(1).strip()
            gid, title = _categorize_clarification_label(label)
            marker = f"[NEEDS CLARIFICATION: {label}]"
            q = _question_from_needs_line(line, label)
            items.append(
                {
                    "kind": "needs_clarification",
                    "marker": marker,
                    "label": label,
                    "question": q,
                    "source": source,
                    "group_id": gid,
                    "group_title": title,
                    "blocking_for": "implementation",
                }
            )
            continue
        if "[SME REVIEW" in line.upper():
            for sm in _SME_REVIEW_RE.finditer(line):
                detail = (sm.group(1) or "").strip()
                tail = line[sm.end() :].strip()
                for prefix in ("\u2014", "-", ":", "—"):
                    if tail.startswith(prefix):
                        tail = tail[len(prefix) :].strip()
                q = tail if tail else f"Please complete SME review{f' ({detail})' if detail else ''}."
                if not q.endswith("?"):
                    q = q.rstrip(".") + "?"
                items.append(
                    {
                        "kind": "sme_review",
                        "marker": sm.group(0),
                        "label": detail or "sme_review",
                        "question": q,
                        "source": source,
                        "group_id": "sme_review",
                        "group_title": "SME review",
                        "blocking_for": "production_readiness",
                    }
                )
    return items


def build_clarifications_bundle(
    *,
    spec: str,
    plan: str,
    tasks: str,
) -> dict[str, Any]:
    """Structured, grouped clarification questions from bundle markdown."""
    raw: list[dict[str, Any]] = []
    raw.extend(_parse_clarification_items(spec, "spec.md"))
    raw.extend(_parse_clarification_items(plan, "plan.md"))
    raw.extend(_parse_clarification_items(tasks, "tasks.md"))

    by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    title_for: dict[str, str] = {}
    for it in raw:
        gid = str(it["group_id"])
        by_group[gid].append(it)
        title_for[gid] = str(it["group_title"])

    groups_out: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for gid, default_title in _CLARIFICATION_GROUP_ORDER:
        if gid in by_group and by_group[gid]:
            groups_out.append(
                {
                    "id": gid,
                    "title": title_for.get(gid, default_title),
                    "items": by_group[gid],
                }
            )
            seen_ids.add(gid)
    for gid, lst in by_group.items():
        if gid not in seen_ids and lst:
            groups_out.append(
                {
                    "id": gid,
                    "title": title_for.get(gid, gid),
                    "items": lst,
                }
            )

    lines: list[str] = ["Clarifications"]
    for i, grp in enumerate(groups_out, start=1):
        lines.append(f"{i}. {grp['title']}")
        for it in grp["items"]:
            lines.append(f"   - {it['marker']} {it['question']}")
    text_block = "\n".join(lines) if len(raw) else ""

    return {
        "open_count": len(raw),
        "items": raw,
        "groups": groups_out,
        "clarifications_text": text_block,
    }


def review_spec_text(spec: str, repo: Path | None = None) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if "## 360 Build Visibility Contract" not in spec:
        findings.append(
            _finding(
                "error",
                "spec",
                "RULE_SPEC_NO_360",
                "spec.md must include `## 360 Build Visibility Contract` with visibility inventories.",
                "spec.md",
            )
        )
    if "[NEEDS CLARIFICATION" in spec or "[needs clarification" in spec.lower():
        findings.append(
            _finding(
                "warn",
                "spec",
                "sme_open_items",
                "Spec lists NEEDS CLARIFICATION markers — resolve before Production; "
                "acceptable while drafting.",
                "spec.md",
            )
        )
    if "[SME REVIEW]" in spec or "[sme review]" in spec.lower():
        findings.append(
            _finding(
                "warn",
                "spec",
                "sme_open_items",
                "Spec lists [SME REVIEW] items — confirm facts before Production.",
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
    spec_body = spec.split("## Development Handoff", 1)[0] if "## Development Handoff" in spec else spec
    spec_body_main = spec_body
    if "## Audience and Scope" in spec_body_main:
        spec_body_main = spec_body_main.split("## Audience and Scope", 1)[0] + (
            spec_body_main.split("## Audience and Scope", 1)[1].split("\n## ", 1)[1]
            if "\n## " in spec_body_main.split("## Audience and Scope", 1)[1]
            else ""
        )
    has_360_contract = "## 360 Build Visibility Contract" in spec
    if (not has_360_contract) and re.search(
        r"`[^`]+\.(xaml|cs)`|\buipcli\b|\buipath\s+pack\b|\[skill:",
        spec_body_main,
        re.IGNORECASE,
    ):
        findings.append(
            _finding(
                "warn",
                "spec",
                "persona_leakage",
                "spec.md contains implementation-level tokens (.xaml/.cs paths, CLI verbs, [skill:]). "
                "spec.md is the BA <-> Developer contract; move those to plan.md / tasks.md.",
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
    if "## LLM / Executor Readiness Contract" not in spec:
        findings.append(
            _finding(
                "error",
                "spec",
                "readiness_contract",
                "spec.md must include `## LLM / Executor Readiness Contract`.",
                "spec.md",
            )
        )
    else:
        for heading, rule in (
            ("### Role and scope", "readiness_role_scope"),
            ("### Environment and conventions", "readiness_environment"),
            ("### Skill routing matrix", "readiness_skill_matrix"),
            ("### Decision logic inventory", "readiness_decision_inventory"),
            ("### Build readiness checklist", "readiness_build_checklist"),
        ):
            if heading not in spec:
                findings.append(
                    _finding(
                        "error",
                        "spec",
                        rule,
                        f"Readiness contract is missing `{heading}`.",
                        "spec.md",
                    )
                )
    if "## 360 Build Visibility Contract" in spec:
        spec_workflow_paths = _spec_workflow_artifacts(spec)
        if spec_workflow_paths:
            missing_visual = _missing_spec_visual_catalog_paths(spec, spec_workflow_paths)
            if missing_visual:
                findings.append(
                    _finding(
                        "error",
                        "spec",
                        "RULE_SPEC_NO_WORKFLOW_VISUAL",
                        "spec.md must include `### Workflow surface visual catalog (required)` with one "
                        "dedicated `#### `<artifact>` section and Mermaid diagram per in-scope workflow "
                        "artifact. Missing visual coverage for: "
                        + ", ".join(missing_visual),
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
    if "connector" not in plan.lower() and "connection" not in plan.lower():
        findings.append(
            _finding(
                "error",
                "plan",
                "RULE_PLAN_NO_CONNECTOR_INV",
                "plan.md must include connector/connection inventory rows for in-scope integrations.",
                "plan.md",
            )
        )
    has_boundary = "invocation boundary" in plan.lower() or (
        "Invoked by" in plan and "Invokes" in plan
    )
    if not has_boundary:
        findings.append(
            _finding(
                "error",
                "plan",
                "RULE_PLAN_NO_SURFACE_BOUNDARY",
                "plan.md must define invocation boundaries (host/invoked surfaces).",
                "plan.md",
            )
        )
    has_log_contract = "correlation" in plan.lower() and (
        "phase" in plan.lower() or "log assertion" in plan.lower()
    )
    if not has_log_contract:
        findings.append(
            _finding(
                "error",
                "plan",
                "RULE_PLAN_NO_LOG_CONTRACT",
                "plan.md must include logging phases, correlation id propagation, and log assertions.",
                "plan.md",
            )
        )
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
    if "## Spec artifact chain map" not in plan:
        findings.append(
            _finding(
                "warn",
                "plan",
                "plan_spec_artifact_chain_map",
                "plan.md should include `## Spec artifact chain map` for spec->plan->tasks traceability.",
                "plan.md",
            )
        )
    if "## Project Graph" not in plan:
        findings.append(
            _finding(
                "error",
                "plan",
                "RULE_PLAN_NO_PROJECT_GRAPH",
                "plan.md must include `## Project Graph` so visual planning, tasks, context, "
                "generation stages, and package mapping share one canonical graph handoff.",
                "plan.md",
            )
        )
    if "## LLM execution navigation" not in plan:
        findings.append(
            _finding(
                "warn",
                "plan",
                "plan_llm_navigation_map",
                "plan.md should include `## LLM execution navigation` for explicit skill/tool/subagent routing.",
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
    _xaml_paradigms = {
        "modern-rpa",
        "coded-automation",
        "solution",
        "library",
        "tests",
    }
    if paradigm in _xaml_paradigms:
        if not re.search(
            r"\b(Sequence|Flowchart|State\s*Machine|Long\s*Running|Long\s+Running)\b",
            plan,
            re.IGNORECASE,
        ):
            findings.append(
                _finding(
                    "warn",
                    "plan",
                    "plan_workflow_types",
                    "plan.md should name XAML workflow types (Sequence, Flowchart, State Machine, "
                    "or Long Running Workflow) with rationale for each process.",
                    "plan.md",
                )
            )
        if not re.search(r"\bXAML|\.xaml\b", plan, re.IGNORECASE):
            findings.append(
                _finding(
                    "warn",
                    "plan",
                    "plan_xaml_first",
                    "plan.md should explicitly anchor XAML / Studio workflows when paradigm is "
                    "RPA or Solution (state coded-agent scope only where justified).",
                    "plan.md",
                )
            )
        vb_hit = re.search(r"\bVB\.NET\b", plan, re.IGNORECASE) or re.search(
            r"\bVisualBasic\b", plan, re.IGNORECASE
        )
        if vb_hit and not re.search(r"\blegacy\b", plan[:4000], re.IGNORECASE):
            findings.append(
                _finding(
                    "warn",
                    "plan",
                    "plan_vbnet_modern",
                    "plan.md mentions VB.NET / VisualBasic without an explicit legacy carve-out — "
                    "modern repo default is C# expressions for XAML.",
                    "plan.md",
                )
            )
    if re.search(r"\bWindows-Legacy\b|\bClassic\b|\buipath-rpa-legacy\b", plan, re.IGNORECASE):
        findings.append(
            _finding(
                "warn",
                "plan",
                "stack_policy_legacy",
                "plan.md mentions Windows-Legacy / Classic / uipath-rpa-legacy. The repo policy "
                "is modern Studio + .NET 8 + C#. Justify or remove the legacy reference.",
                "plan.md",
            )
        )
    if "## Stack Policy" not in plan and paradigm in _xaml_paradigms:
        findings.append(
            _finding(
                "warn",
                "plan",
                "stack_policy_section",
                "plan.md should include a `## Stack Policy` section declaring modern Studio + "
                "activity-first preference (and a `## Coded Surface Justification` table when any "
                "coded `.cs` workflow is in scope).",
                "plan.md",
            )
        )
    if re.search(r"\bWorkflows/[^\s`]+\.cs\b|`[^`]+\.cs\`", plan) and paradigm in _xaml_paradigms:
        if "## Coded Surface Justification" not in plan or "_empty by default" in plan:
            findings.append(
                _finding(
                    "warn",
                    "plan",
                    "coded_surface_justification",
                    "plan.md references a `.cs` workflow but `## Coded Surface Justification` is empty. "
                    "Modern stack prefers UiPath activities; justify each coded surface with the "
                    "library/activity-doc lookup that proved activities cannot cover the case.",
                    "plan.md",
                )
            )
    if paradigm == "solution":
        if "solution.uipx" not in plan or "bindings" not in plan.lower():
            findings.append(
                _finding(
                    "warn",
                    "plan",
                    "plan_solution_descriptors",
                    "Solution paradigm plans should name `solution.uipx` and `bindings/` "
                    "so project boundaries stay explicit.",
                    "plan.md",
                )
            )
    return findings


_TASK_LINE = re.compile(
    r"^\s*-\s*\[\s*\]\s*(T\d+)(?:\s+\[P\])?\s+\[US(\d+)\]",
    re.MULTILINE,
)

_WORKFLOW_HINT_RE = re.compile(
    r"`[^`]+\.(?:xaml|cs|py|flow|bpmn|json|md|ts|tsx)`|projects/|Main\.xaml|Workflows/|Activities/|"
    r"langgraph\.json|agent_framework\.json|caseplan\.json|api-workflow\.json|project\.json|tests/|Tests/|"
    r"\bSequence\b|\bFlowchart\b|Long\s+Running|State\s+Machine",
    re.IGNORECASE,
)
_TEST_COMMAND_RE = re.compile(
    r"pytest|uipcli\s+test\s+run|unittest|uipath\s+run|\buip\s+codedapp\s+test|\buip\s+case\b",
    re.IGNORECASE,
)
_PHASE5_EVIDENCE_RE = re.compile(
    r"junit|\.trx|pytest|\bnupkg\b|analyzer|resultPath|robot\s+log|job\s+log|execution\s+log|testresults",
    re.IGNORECASE,
)
_FAILURE_DIAGNOSIS_RE = re.compile(
    r"(diagnos|parse|parsed).*?(analyzer|resultPath|CLI|error|rule).*?"
    r"(uipath_library_search|uipath_library_lookup|query_uipath_docs|--help|Studio\s+IPC).*?"
    r"(inspect|source|schema|descriptor|project\.json|solution\.uipx).*?"
    r"(fix|local).*?(rerun|re-run)",
    re.IGNORECASE | re.DOTALL,
)
_ANALYZER_POLICY_TRIGGER_RE = re.compile(
    r"ST-USG-034|Automation\s+Hub|tenant\s+policy|validates\s+except",
    re.IGNORECASE,
)
_ANALYZER_POLICY_DIAGNOSIS_RE = re.compile(
    r"(analyzer|resultPath|JSON).*?"
    r"(uipath_library_search|uipath_library_lookup|query_uipath_docs|docs?).*?"
    r"(project\.json|Studio|project-setting|project\s+metadata|Automation\s+Hub).*?"
    r"(fix|local).*?(rerun|re-run)",
    re.IGNORECASE | re.DOTALL,
)
_SOLUTION_DESCRIPTOR_DIAGNOSIS_RE = re.compile(
    r"solution\.uipx.*?"
    r"(descriptor|schema|definition|ResourceBuilder).*?"
    r"(generated|provenance|placeholder|manual|Studio|Automation\s+Cloud).*?"
    r"(project-level|restore|analyze).*?"
    r"(rerun|re-run)",
    re.IGNORECASE | re.DOTALL,
)
_STUDIO_TEMPLATE_CONTRACT_RE = re.compile(
    r"(template\s+decision\s+matrix|starter\s+template|scaffold\s+source).*?"
    r"(uip\s+rpa\s+create-project|project\.uiproj|project\.json|Studio).*?"
    r"(workflow\s+type|Dispatcher|Performer|queue[-\s]?worker|Long\s+Running|HITL|Sequence|Flowchart|State\s+Machine)",
    re.IGNORECASE | re.DOTALL,
)
_GENERIC_XAML_SCAFFOLD_RE = re.compile(
    r"(generic|manual|hand[-\s]?written).*?Main\.xaml|LogMessage[-\s]?only|scaffold[-\s]?only",
    re.IGNORECASE | re.DOTALL,
)
_TEMPLATE_REMEDIATION_RE = re.compile(
    r"(template\s+remediation|replace.*?generic.*?template|starter\s+template|uip\s+rpa\s+create-project|"
    r"Dispatcher\s+template|Performer|queue[-\s]?worker|Long\s+Running|HITL)",
    re.IGNORECASE | re.DOTALL,
)
_UIPATH_PKG_MENTION = re.compile(r"\bUiPath\.[A-Za-z0-9_.]+\b")
_RPA_BROAD_ACTIVITY_RE = re.compile(
    r"(Microsoft\s+Graph\s*\+\s*[^;]*activities|Graph\s*\+\s*[^;]*activities|"
    r"Slack\s+HITL\s*\+\s*queue\s+updates|host\s+loop\s*\+\s*[^;]*agent\s+invoke\s*\+\s*queue\s+updates)",
    re.IGNORECASE,
)
_STUDIO_HANDOFF_RE = re.compile(r"\[HANDOFF:Studio\]", re.IGNORECASE)
_AGENT_TASK_RE = re.compile(r"\b(agent|Invoke Agent|LangGraph|LlamaIndex)\b", re.IGNORECASE)
_AGENT_TASK_EVIDENCE_RE = re.compile(
    r"langgraph\.json|llama_index\.json|agent_framework\.json|uipath\s+run|uv\s+run\s+pytest|"
    r"request/response|response\s+schema|graph_entry\.py|graph\s+nodes",
    re.IGNORECASE,
)
_EXECUTOR_CONTEXT_RE = re.compile(r"###\s*Executor context", re.IGNORECASE)
_TASK_CARD_TABLE_RE = re.compile(r"\|\s*Field\s*\|\s*Content\s*\|", re.IGNORECASE)
_MINI_TOPOLOGY_RE = re.compile(
    r"###\s*(Mini-topology|Workflow map|Workflow interaction):",
    re.IGNORECASE,
)
_PER_WORKFLOW_ACTIVITY_CHECKLIST_HEADING_RE = re.compile(
    r"##\s*Per-workflow activity checklist",
    re.IGNORECASE,
)
_SPEC_360_HEADING_RE = re.compile(r"##\s*360\s+Build\s+Visibility\s+Contract", re.IGNORECASE)
_SPEC_WORKFLOW_VISUAL_CATALOG_HEADING_RE = re.compile(
    r"###\s*Workflow\s+surface\s+visual\s+catalog",
    re.IGNORECASE,
)
_PLAN_SPEC_ARTIFACT_CHAIN_HEADING_RE = re.compile(r"##\s*Spec\s+artifact\s+chain\s+map", re.IGNORECASE)
_PLAN_WORKFLOW_CONFORMANCE_HEADING_RE = re.compile(
    r"##\s*Workflow\s+diagram\s*\+\s*activity\s+conformance\s+matrix",
    re.IGNORECASE,
)
_SPEC_ARTIFACT_TOKEN_RE = re.compile(
    r"[A-Za-z0-9_./-]+\.(?:xaml|flow|py|dmn|json|uipx|uiproj)",
    re.IGNORECASE,
)
_STUB_TASK_RE = re.compile(
    r"(placeholder|would invoke|contract only|logmessage-only|stub-)",
    re.IGNORECASE,
)


def _task_id_number(line: str) -> int | None:
    # Match T010 / T011 but not a prefix of T011A — `(T\d+)` alone treats T011A as T011.
    m = re.match(r"^\s*-\s*\[\s*\]\s*T(\d+)([A-Z])?(?=\s)", line)
    if not m:
        return None
    return int(m.group(1), 10)


def _extract_section(text: str, heading_pattern: re.Pattern[str]) -> str:
    """Return markdown section body from heading match to next ## heading."""
    m = heading_pattern.search(text)
    if not m:
        return ""
    start = m.end()
    rest = text[start:]
    next_heading = re.search(r"\n##\s+", rest)
    if not next_heading:
        return rest
    return rest[: next_heading.start()]


def _spec_workflow_artifacts(spec: str) -> set[str]:
    """Return workflow artifacts declared in spec 360 section."""
    contract = _extract_section(spec, _SPEC_360_HEADING_RE)
    if not contract.strip():
        return set()
    return {
        p.strip()
        for p in _WORKFLOW_PATH_TOKEN_RE.findall(contract)
        if any(ext in p.lower() for ext in (".xaml", ".flow", ".py", ".dmn"))
    }


def _missing_spec_visual_catalog_paths(spec: str, paths: set[str]) -> list[str]:
    """Return spec workflow artifacts that do not have a dedicated visual section + mermaid."""
    catalog = _extract_section(spec, _SPEC_WORKFLOW_VISUAL_CATALOG_HEADING_RE)
    if not catalog.strip():
        return sorted(paths)
    missing: list[str] = []
    for path in sorted(paths):
        pattern = re.compile(
            rf"####\s*`{re.escape(path)}`.*?```mermaid",
            re.IGNORECASE | re.DOTALL,
        )
        if not pattern.search(catalog):
            missing.append(path)
    return missing


def _review_task_section_contracts(tasks: str, paradigm: str | None) -> list[dict[str, Any]]:
    """Tests / Implementation / Paradigm-specific task lines must meet detail contracts."""
    findings: list[dict[str, Any]] = []
    mode = "none"  # none | tests | impl | phase5
    wf_paradigms = {
        "modern-rpa",
        "coded-automation",
        "solution",
        "library",
        "tests",
        "api-workflow",
        "coded-app",
        "maestro-flow",
        "case-management",
        "coded-agent",
    }

    for line in tasks.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            if re.search(r"phase\s*5", stripped, re.IGNORECASE):
                mode = "phase5"
            else:
                mode = "none"
            continue
        if stripped.startswith("### Tests"):
            mode = "tests"
            continue
        if stripped.startswith("### Implementation") or stripped.startswith("### Paradigm-specific tasks"):
            mode = "impl"
            continue

        tid = _task_id_number(line)
        if tid is None:
            continue
        is_parallel = "[P]" in line

        if mode == "tests":
            if not _TEST_COMMAND_RE.search(line):
                findings.append(
                    _finding(
                        "error",
                        "tasks",
                        "task_test_detail",
                        f"Task T{tid} must cite an exact test command (pytest, uipcli test run, "
                        f"unittest, uipath run, or uip ...): {stripped[:160]}",
                        "tasks.md",
                    )
                )
        elif mode == "impl" and not is_parallel:
            if _STUDIO_HANDOFF_RE.search(line):
                findings.append(
                    _finding(
                        "error",
                        "tasks",
                        "task_studio_handoff_skip",
                        "[HANDOFF:Studio] is not a valid substitute for building Studio/RPA source artifacts.",
                        "tasks.md",
                    )
                )
            if _RPA_BROAD_ACTIVITY_RE.search(line):
                findings.append(
                    _finding(
                        "error",
                        "tasks",
                        "task_rpa_too_broad",
                        "RPA/Studio task is too broad; split into package/activity/property mapped subtasks "
                        f"with Studio/default-activity evidence: {stripped[:180]}",
                        "tasks.md",
                    )
                )
            if _AGENT_TASK_RE.search(line) and not _AGENT_TASK_EVIDENCE_RE.search(line):
                findings.append(
                    _finding(
                        "error",
                        "tasks",
                        "task_agent_contract_detail",
                        "Agent-backed task must name graph descriptor/entry point, local run/test command, "
                        f"or request/response schema: {stripped[:180]}",
                        "tasks.md",
                    )
                )
            if not _PER_LINE_IMPL_GROUND.search(line):
                findings.append(
                    _finding(
                        "error",
                        "tasks",
                        "task_implementation_grounding",
                        f"Task T{tid} must cite grounding ([skill:/[library:/[askai:/[agent: or "
                        f"uipath_library_search / uipath_library_lookup / query_uipath_docs / uipath_doc_*).",
                        "tasks.md",
                    )
                )
            wf_ok = False
            if paradigm in (
                "solution",
                "modern-rpa",
                "coded-automation",
                "library",
                "tests",
                "api-workflow",
            ):
                wf_ok = bool(
                    re.search(
                        r"`[^`]+\.xaml`|projects/|Main\.xaml|Workflows/|Activities/|\bSequence\b|"
                        r"\bFlowchart\b|Long\s+Running|State\s+Machine",
                        line,
                        re.IGNORECASE,
                    )
                )
            elif paradigm == "coded-agent":
                wf_ok = bool(
                    re.search(
                        r"`[^`]+\.py`|langgraph\.json|agent_framework\.json|tests/|Tests/",
                        line,
                        re.IGNORECASE,
                    )
                )
            elif paradigm in wf_paradigms:
                wf_ok = bool(_WORKFLOW_HINT_RE.search(line))
            if paradigm in wf_paradigms and tid >= 11 and not wf_ok:
                findings.append(
                    _finding(
                        "error",
                        "tasks",
                        "task_workflow_detail",
                        f"Task T{tid} must name a workflow entry (.xaml/.cs/.py), projects/, graph, "
                        f"or workflow type keyword: {stripped[:160]}",
                        "tasks.md",
                    )
                )
            if tid >= 11 and not _PATH_TOKEN_RE.search(line):
                findings.append(
                    _finding(
                        "error",
                        "tasks",
                        "task_project_detail",
                        f"Task T{tid} must include a concrete artifact path in backticks.",
                        "tasks.md",
                    )
                )
            if _UIPATH_PKG_MENTION.search(line):
                low = line.lower()
                if "uipath_doc_get_activity" not in low and "[activity:" not in line:
                    findings.append(
                        _finding(
                            "error",
                            "tasks",
                            "task_activity_detail",
                            f"Task T{tid} names a UiPath package token — add `uipath_doc_get_activity` or "
                            f"`[activity:Package:Activity]`: {stripped[:160]}",
                            "tasks.md",
                        )
                    )
            if _RESOURCE_TOKEN_RE.search(line) and not _LIBRARY_TOOL_RE.search(line):
                findings.append(
                    _finding(
                        "error",
                        "tasks",
                        "task_knowledge_grounding",
                        f"Task T{tid} mentions queues/assets/bindings/folders — include "
                        f"`uipath_library_search` or `uipath_library_lookup` (or query_uipath_docs fallback): "
                        f"{stripped[:160]}",
                        "tasks.md",
                    )
                )

    m5 = re.search(r"(?i)##\s*Phase\s*5\s*:", tasks)
    if m5:
        tail = tasks[m5.start() :]
        if not _PHASE5_EVIDENCE_RE.search(tail):
            findings.append(
                _finding(
                    "error",
                    "tasks",
                    "task_evidence_detail",
                    "Phase 5 must name verification evidence (JUnit/pytest report, analyzer resultPath JSON, "
                    ".nupkg path, robot/job logs).",
                    "tasks.md",
                )
            )
        if not _FAILURE_DIAGNOSIS_RE.search(tail):
            findings.append(
                _finding(
                    "error",
                    "tasks",
                    "task_failure_diagnosis_loop",
                    "Phase 5 must require parsing failed verification output, consulting docs/tooling, "
                    "inspecting affected source/schema, attempting a safe local fix, and rerunning before "
                    "declaring analyzer/solution/tooling failures blocked.",
                    "tasks.md",
                )
            )
        if re.search(r"stop\s+on\s+analyzer\s+errors|blocked\s+by\s+tenant\s+policy", tail, re.IGNORECASE) and not _FAILURE_DIAGNOSIS_RE.search(tail):
            findings.append(
                _finding(
                    "error",
                    "tasks",
                    "task_premature_blocker_wording",
                    "Phase 5 cannot allow premature blocker wording for analyzer errors or tenant policy "
                    "without the diagnosis/fix/rerun loop.",
                    "tasks.md",
                )
            )

    return findings


def review_tasks_text(tasks: str, spec: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    paradigm = _declared_paradigm(spec)
    _xaml_paradigms = {
        "modern-rpa",
        "coded-automation",
        "solution",
        "library",
        "tests",
    }
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
    if not _EXECUTOR_CONTEXT_RE.search(tasks):
        findings.append(
            _finding(
                "error",
                "tasks",
                "executor_context_required",
                "tasks.md must include `### Executor context ...` blocks for phases/stories.",
                "tasks.md",
            )
        )
    if not _TASK_CARD_TABLE_RE.search(tasks):
        findings.append(
            _finding(
                "error",
                "tasks",
                "task_card_required",
                "tasks.md must include task-card tables (`| Field | Content |`) for implementation tasks.",
                "tasks.md",
            )
        )
    if not re.search(r"##\s*FR\s+traceability", tasks, re.IGNORECASE):
        findings.append(
            _finding(
                "warn",
                "tasks",
                "tasks_fr_traceability_matrix",
                "tasks.md should include `## FR traceability matrix (required)`.",
                "tasks.md",
            )
        )
    if "## Clarification resolution ledger" not in tasks:
        findings.append(
            _finding(
                "warn",
                "tasks",
                "tasks_clarification_resolution_ledger",
                "tasks.md should include `## Clarification resolution ledger (required)`.",
                "tasks.md",
            )
        )
    if "## Log assertion checklist" not in tasks:
        findings.append(
            _finding(
                "warn",
                "tasks",
                "tasks_log_assertion_checklist",
                "tasks.md should include `## Log assertion checklist (required)`.",
                "tasks.md",
            )
        )
    if "## LLM execution navigation guide" not in tasks:
        findings.append(
            _finding(
                "warn",
                "tasks",
                "tasks_llm_navigation_guide",
                "tasks.md should include `## LLM execution navigation guide`.",
                "tasks.md",
            )
        )
    findings.extend(_review_task_section_contracts(tasks, paradigm))
    workflow_paths = {
        p.strip()
        for p in _WORKFLOW_PATH_TOKEN_RE.findall(tasks)
        if any(ext in p.lower() for ext in (".xaml", ".flow", ".py", ".dmn"))
    }
    stub_xaml_line = any(".xaml" in ln.lower() and _STUB_TASK_RE.search(ln) for ln in tasks.splitlines())
    if stub_xaml_line:
        findings.append(
            _finding(
                "error",
                "tasks",
                "RULE_TASKS_STUB_XAML",
                "XAML tasks contain stub-only wording (placeholder/contract-only/would invoke).",
                "tasks.md",
            )
        )
    if workflow_paths:
        has_rule_tasks_no_diagram = False
        if not _MINI_TOPOLOGY_RE.search(tasks):
            findings.append(
                _finding(
                    "error",
                    "tasks",
                    "workflow_diagram_sections",
                    "tasks.md references workflow artifacts but lacks explicit per-workflow diagram sections.",
                    "tasks.md",
                )
            )
            has_rule_tasks_no_diagram = True
            findings.append(
                _finding(
                    "error",
                    "tasks",
                    "RULE_TASKS_NO_DIAGRAM",
                    "Each in-scope workflow artifact must have a dedicated internal-step diagram section.",
                    "tasks.md",
                )
            )
        checklist_section = _extract_section(tasks, _PER_WORKFLOW_ACTIVITY_CHECKLIST_HEADING_RE)
        if not checklist_section:
            findings.append(
                _finding(
                    "error",
                    "tasks",
                    "RULE_TASKS_NO_ACTIVITY_CHECKLIST",
                    "tasks.md must include `## Per-workflow activity checklist (required)` "
                    "when workflow artifacts are in scope.",
                    "tasks.md",
                )
            )
        else:
            unresolved_checklist: list[str] = []
            for path in sorted(workflow_paths):
                if path not in checklist_section:
                    unresolved_checklist.append(path)
            if unresolved_checklist:
                findings.append(
                    _finding(
                        "error",
                        "tasks",
                        "RULE_TASKS_NO_ACTIVITY_CHECKLIST",
                        "Per-workflow activity checklist coverage is incomplete for one or more "
                        "workflow artifacts: "
                        + ", ".join(unresolved_checklist),
                        "tasks.md",
                    )
                )
        unresolved: list[str] = []
        for path in sorted(workflow_paths):
            if tasks.count(f"`{path}`") < 2:
                unresolved.append(path)
        if unresolved:
            findings.append(
                _finding(
                    "error",
                    "tasks",
                    "workflow_diagrams_complete",
                    "Each workflow artifact should have an actual internal-step diagram section. "
                    f"Add per-workflow diagrams for: {', '.join(unresolved)}",
                    "tasks.md",
                )
            )
            if not has_rule_tasks_no_diagram:
                findings.append(
                    _finding(
                        "error",
                        "tasks",
                        "RULE_TASKS_NO_DIAGRAM",
                        "Per-workflow diagram coverage is incomplete for one or more referenced artifacts.",
                        "tasks.md",
                    )
                )
    if _ANALYZER_POLICY_TRIGGER_RE.search(tasks) and not _ANALYZER_POLICY_DIAGNOSIS_RE.search(tasks):
        findings.append(
            _finding(
                "error",
                "tasks",
                "task_analyzer_rule_diagnosis",
                "Tasks mention ST-USG-034, Automation Hub, tenant policy, or 'validates except' without "
                "requiring analyzer JSON parsing, docs lookup, project/Studio metadata inspection, "
                "safe local fix attempt, and rerun evidence.",
                "tasks.md",
            )
        )
    if "solution.uipx" in tasks and not _SOLUTION_DESCRIPTOR_DIAGNOSIS_RE.search(tasks):
        findings.append(
            _finding(
                "error",
                "tasks",
                "task_solution_descriptor_diagnosis",
                "Tasks mention `solution.uipx` without requiring descriptor/schema validation, generated "
                "versus placeholder/manual provenance, project-level restore/analyze separation, and rerun evidence.",
                "tasks.md",
            )
        )
    if paradigm in _xaml_paradigms:
        if not _STUDIO_TEMPLATE_CONTRACT_RE.search(tasks):
            findings.append(
                _finding(
                    "error",
                    "tasks",
                    "tasks_studio_template_contract",
                    "RPA/Studio tasks must include a template decision matrix: project path, selected "
                    "starter template or scaffold source, workflow type, why it matches the use case, "
                    "generated structure to preserve, and `uip rpa create-project` / Studio evidence. "
                    "If unknown, add a discovery/question task before implementation.",
                    "tasks.md",
                )
            )
        if _GENERIC_XAML_SCAFFOLD_RE.search(tasks) and not _TEMPLATE_REMEDIATION_RE.search(tasks):
            findings.append(
                _finding(
                    "error",
                    "tasks",
                    "tasks_generic_xaml_without_template_remediation",
                    "Generic or LogMessage-only XAML scaffolding must have explicit template remediation "
                    "tasks when Dispatcher, Performer/queue worker, Long Running/HITL, Flowchart, or "
                    "State Machine structure is required.",
                    "tasks.md",
                )
            )
        if not re.search(r"LogMessage|log message", tasks, re.IGNORECASE):
            findings.append(
                _finding(
                    "warn",
                    "tasks",
                    "tasks_logging_contract",
                    "tasks.md should require LogMessage (or equivalent) with structured phases.",
                    "tasks.md",
                )
            )
        if not re.search(r"correlation", tasks, re.IGNORECASE):
            findings.append(
                _finding(
                    "warn",
                    "tasks",
                    "tasks_correlation_id",
                    "tasks.md should require a correlation id propagated across workflows/queue items.",
                    "tasks.md",
                )
            )
        if not re.search(
            r"\b(smoke|job\s+run|run-file|robot\s+log|execution\s+log)\b",
            tasks,
            re.IGNORECASE,
        ):
            findings.append(
                _finding(
                    "warn",
                    "tasks",
                    "tasks_smoke_run",
                    "tasks.md should include a smoke run or job/run-file step after pack.",
                    "tasks.md",
                )
            )
        if not re.search(
            r"(log\s+assert|assert.*log|expected.*log|robot\s+log|job\s+log)",
            tasks,
            re.IGNORECASE,
        ):
            findings.append(
                _finding(
                    "warn",
                    "tasks",
                    "tasks_log_validation",
                    "tasks.md should capture expected log substrings or assertions after smoke run.",
                    "tasks.md",
                )
            )
    
    # RULE_TASKS_NO_ACTIVITY_DOC_EVIDENCE: check for activity evidence
    if paradigm in _xaml_paradigms:
        activity_doc_pattern = re.compile(
            r"(uipath_doc_get_activity|uipath_doc_list_packages|\[activity:[A-Za-z0-9_.]+:[A-Za-z][A-Za-z0-9_]*\]|"
            r"default\s+xaml|studio\s+scaffold|package.*version|required\s+scope|required\s+props)",
            re.IGNORECASE
        )
        if not activity_doc_pattern.search(tasks):
            findings.append(
                _finding(
                    "error",
                    "tasks",
                    "RULE_TASKS_NO_ACTIVITY_DOC_EVIDENCE",
                    "tasks.md must include activity doc lookups (uipath_doc_get_activity) and evidence "
                    "(package, version, required scope, inputs/outputs, default XAML) for non-trivial activities. "
                    "See docs/uiplan/ACTIVITY_AND_RUNTIME_EVIDENCE.md §Activity selection grounding.",
                    "tasks.md",
                )
            )
    
    # RULE_TASKS_NO_RESOURCE_PROVISIONING_EVIDENCE: check for resource provisioning evidence
    has_orchestrator_resources = bool(re.search(r"\b(queue|asset|folder|connection|binding)\b", tasks, re.IGNORECASE))
    if has_orchestrator_resources:
        resource_provisioning_pattern = re.compile(
            r"(uip\s+or\s+queues\s+create|uip\s+or\s+assets\s+create|uip\s+or\s+folders\s+create|"
            r"provisioning\s+command|verification\s+command|evidence\s+path|out/queue-|out/asset-|"
            r"\[HANDOFF:Secrets\]|\[skill:uipath-platform\])",
            re.IGNORECASE
        )
        if not resource_provisioning_pattern.search(tasks):
            findings.append(
                _finding(
                    "error",
                    "tasks",
                    "RULE_TASKS_NO_RESOURCE_PROVISIONING_EVIDENCE",
                    "tasks.md references queues/assets/folders/connections but lacks provisioning commands, "
                    "verification commands, evidence paths, and [skill:uipath-platform] routing. "
                    "See docs/uiplan/ACTIVITY_AND_RUNTIME_EVIDENCE.md §Orchestrator resource lifecycle.",
                    "tasks.md",
                )
            )
    
    # RULE_TASKS_NO_TENANT_RUNTIME_EVIDENCE: check for tenant runtime evidence or structured blocker
    has_deploy_language = bool(re.search(r"\b(deploy|publish|activate|job\s+run|job\s+start|smoke)\b", tasks, re.IGNORECASE))
    if has_deploy_language:
        tenant_evidence_pattern = re.compile(
            r"(target\s+folder|package.*version|job\s+id|final\s+state|job\s+logs|uip\s+or\s+jobs\s+logs|"
            r"queue.*item.*proof|asset.*proof|tenant-blocker\.json|local-ready|"
            r"uip\s+or\s+jobs\s+start|uipcli\s+package\s+deploy)",
            re.IGNORECASE
        )
        if not tenant_evidence_pattern.search(tasks):
            findings.append(
                _finding(
                    "error",
                    "tasks",
                    "RULE_TASKS_NO_TENANT_RUNTIME_EVIDENCE",
                    "tasks.md includes deploy/smoke language but lacks tenant runtime evidence "
                    "(target folder, package version, job ID, final state, logs, queue/asset proof) "
                    "or a structured blocker (tenant-blocker.json) explaining why tenant evidence is unavailable. "
                    "See docs/uiplan/ACTIVITY_AND_RUNTIME_EVIDENCE.md §Tenant evidence.",
                    "tasks.md",
                )
            )
    
    # RULE_TASKS_NO_UAT_TEST_EVIDENCE: check for UAT/test evidence
    has_production_stories = bool(re.search(r"\b(user\s+story|production|acceptance\s+criteria)\b", tasks, re.IGNORECASE))
    if has_production_stories or has_deploy_language:
        uat_evidence_pattern = re.compile(
            r"(uipcli\s+test\s+run|pytest|uipath\s+eval|test\s+artifact|test\s+execution\s+command|"
            r"test\s+results|Tests/.*\.xaml|tests/test_.*\.py|out/test-results|"
            r"UAT|manual\s+uat|AC\s+mapping|acceptance\s+criteria\s+mapping|"
            r"\[skill:uipath-test\]|UiPath\.Testing\.Activities)",
            re.IGNORECASE
        )
        if not uat_evidence_pattern.search(tasks):
            findings.append(
                _finding(
                    "error",
                    "tasks",
                    "RULE_TASKS_NO_UAT_TEST_EVIDENCE",
                    "tasks.md appears to include production-bound stories but lacks UAT/test evidence "
                    "(test artifacts, execution commands, results, AC mapping, or [skill:uipath-test] routing). "
                    "See docs/uiplan/ACTIVITY_AND_RUNTIME_EVIDENCE.md §UAT/test evidence.",
                    "tasks.md",
                )
            )
    
    flow_hitl_override = (
        "flow" in spec.lower()
        and "hitl" in spec.lower()
        and (
            "flow as the process owner" in spec.lower()
            or "flow as hitl canvas" in spec.lower()
            or "uipath flow" in spec.lower()
        )
    )
    if flow_hitl_override and "[skill:uipath-custom-hitl]" in tasks and "[skill:uipath-maestro-flow]" not in tasks:
        findings.append(
            _finding(
                "error",
                "tasks",
                "hitl_override_mismatch",
                "Spec requires Flow-owned HITL, but tasks route only through custom HITL. "
                "Add Flow HITL override and `[skill:uipath-maestro-flow]` routing.",
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
    spec_workflow_paths = _spec_workflow_artifacts(spec)
    if "## 360 Build Visibility Contract" in spec:
        spec_artifacts = {m.group(0) for m in _SPEC_ARTIFACT_TOKEN_RE.finditer(spec)}
        missing = [a for a in sorted(spec_artifacts) if a not in plan and a not in tasks]
        if missing:
            findings.append(
                _finding(
                    "error",
                    "cross",
                    "RULE_SPEC_ARTIFACT_MISSING",
                    "Artifacts declared in spec 360 contract are missing from plan/tasks: "
                    + ", ".join(missing[:8]),
                    "cross",
                )
            )
    if spec_workflow_paths:
        plan_chain = _extract_section(plan, _PLAN_SPEC_ARTIFACT_CHAIN_HEADING_RE)
        plan_conformance = _extract_section(plan, _PLAN_WORKFLOW_CONFORMANCE_HEADING_RE)
        tasks_checklist = _extract_section(tasks, _PER_WORKFLOW_ACTIVITY_CHECKLIST_HEADING_RE)
        missing_chain = [p for p in sorted(spec_workflow_paths) if p not in plan_chain]
        if missing_chain:
            findings.append(
                _finding(
                    "error",
                    "cross",
                    "RULE_SPEC_VISUAL_CHAIN_MISSING",
                    "Spec workflow artifacts must appear in `plan.md` `## Spec artifact chain map`. "
                    "Missing: " + ", ".join(missing_chain),
                    "cross",
                )
            )
        missing_plan_conformance = [p for p in sorted(spec_workflow_paths) if p not in plan_conformance]
        if missing_plan_conformance:
            findings.append(
                _finding(
                    "error",
                    "cross",
                    "RULE_SPEC_VISUAL_CHAIN_MISSING",
                    "Spec workflow artifacts must appear in `plan.md` "
                    "`## Workflow diagram + activity conformance matrix (required)`. Missing: "
                    + ", ".join(missing_plan_conformance),
                    "cross",
                )
            )
        missing_tasks_checklist = [p for p in sorted(spec_workflow_paths) if p not in tasks_checklist]
        if missing_tasks_checklist:
            findings.append(
                _finding(
                    "error",
                    "cross",
                    "RULE_SPEC_VISUAL_CHAIN_MISSING",
                    "Spec workflow artifacts must appear in `tasks.md` "
                    "`## Per-workflow activity checklist (required)`. Missing: "
                    + ", ".join(missing_tasks_checklist),
                    "cross",
                )
            )
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
    if "{{" in spec or "{{" in plan or "{{" in tasks:
        findings.append(
            _finding(
                "error",
                "cross",
                "RULE_ANY_TEMPLATE_RESIDUE",
                "Template tokens (`{{...}}`) remain in spec/plan/tasks.",
                "cross",
            )
        )
    errors = [f for f in findings if f.get("severity") == "error"]
    ok = len(errors) == 0
    clarifications = build_clarifications_bundle(spec=spec, plan=plan, tasks=tasks)
    open_n = int(clarifications.get("open_count") or 0)
    if not ok:
        next_action = "Address error-severity findings and re-run uipath_plan_review."
    elif open_n > 0:
        next_action = (
            f"Review passed with {open_n} open clarification(s). "
            "Use the grouped `clarifications` object (or `clarifications_text`) and update "
            "`spec.md` / `plan.md` / `tasks.md` before Production-bound implementation."
        )
    else:
        next_action = "Optional: resolve warnings; then uipath_plan_accept when ready."
    return {
        "ok": ok,
        "stage": stage,
        "findings": findings,
        "next_action": next_action,
        "clarifications": clarifications,
    }
