"""UiPlan MCP actions: ground, spec/plan/tasks generation, review, orchestrator."""
from __future__ import annotations

import re
import shutil
import importlib.util
from pathlib import Path
from typing import Any

try:
    from tools.uiplan.paradigms import (
        build_loop_block,
        cli_family,
        code_structure_block,
        deploy_gate,
        infer_paradigm_from_files,
        normalize_paradigm,
        paradigm_task_blocks,
        stack_line,
    )
except ModuleNotFoundError:
    _PARADIGM_PATH = Path(__file__).resolve().parents[3] / "tools" / "uiplan" / "paradigms.py"
    _spec = importlib.util.spec_from_file_location("uiplan_paradigms", _PARADIGM_PATH)
    if _spec is None or _spec.loader is None:
        raise
    _module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_module)
    build_loop_block = _module.build_loop_block
    cli_family = _module.cli_family
    code_structure_block = _module.code_structure_block
    deploy_gate = _module.deploy_gate
    infer_paradigm_from_files = _module.infer_paradigm_from_files
    normalize_paradigm = _module.normalize_paradigm
    paradigm_task_blocks = _module.paradigm_task_blocks
    stack_line = _module.stack_line
from uipath_claude.context.path_contract import runtime_root
from uipath_claude.skills.activity_docs import get_activity_doc

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

_ACTIVITY_TAG_RE = re.compile(
    r"\[activity:([A-Za-z0-9_.]+):([A-Za-z][A-Za-z0-9_]*)\]"
)
ACTIVITY_REFS_CAP = 8


def collect_activity_refs(*texts: str, cap: int = ACTIVITY_REFS_CAP) -> list[tuple[str, str]]:
    """Parse plan/spec text for ``[activity:PackageId:ActivityName]`` tags; dedupe, order preserved."""
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str]] = []
    for text in texts:
        for m in _ACTIVITY_TAG_RE.finditer(text or ""):
            key = (m.group(1), m.group(2))
            if key in seen:
                continue
            seen.add(key)
            out.append(key)
            if len(out) >= cap:
                return out
    return out


def _resolved_activity_docs_markdown(spec: str, plan: str) -> str:
    """Markdown to append to tasks.md (includes heading)."""
    refs = collect_activity_refs(spec, plan)
    parts: list[str] = ["\n\n## Resolved activity docs\n\n"]
    if not refs:
        parts.append(
            "_No `[activity:PackageId:ActivityName]` tags in plan.md or spec.md yet — "
            "add tags in plan for auto-inlined docs. Until then, resolve activity semantics via "
            "`uipath_doc_get_activity` / `uipath_doc_list_packages` (MCP), not guesswork._\n"
        )
    else:
        for pkg, act in refs:
            doc = get_activity_doc(pkg, act, None)
            parts.append(f"### `{pkg}` / `{act}`\n\n")
            if doc:
                body = doc.strip()
                if len(body) > 1500:
                    body = body[:1500] + "\n\n_(truncated)_\n"
                parts.append(body + "\n\n---\n\n")
            else:
                parts.append("_No documentation found._\n\n---\n\n")
    return "".join(parts)


def _tdd_excerpt_lines(lines: list[str]) -> str:
    """First content through the line before the second top-level ``## `` heading, else first 40 lines."""
    if not lines:
        return ""
    major = [
        i
        for i, ln in enumerate(lines)
        if ln.startswith("## ") and not ln.startswith("###")
    ]
    if len(major) >= 2:
        excerpt_lines = lines[: major[1]]
    else:
        excerpt_lines = lines[:40]
    return "\n".join(excerpt_lines).rstrip() + "\n"


def _tdd_reference_append(repo: Path) -> str:
    try:
        rt = runtime_root(repo)
    except FileNotFoundError:
        import uipath_claude  # noqa: PLC0415

        rt = Path(uipath_claude.__file__).resolve().parent.parent
    tdd = rt / "uipath_claude" / "templates" / "tdd.md"
    if not tdd.is_file():
        return ""
    excerpt = _tdd_excerpt_lines(tdd.read_text(encoding="utf-8").splitlines())
    if not excerpt.strip():
        return ""
    return "\n\n## TDD reference (excerpt)\n\n" + excerpt + "\n"


def _template_dir(repo: Path) -> Path:
    """Return the kit directory, preferring *repo* then the checkout that owns ``uipath_claude``."""
    direct = repo / "templates" / "uiplan"
    if (direct / "_spec-template.md").is_file():
        return direct
    import uipath_claude  # noqa: PLC0415 — runtime import to infer checkout root

    inferred_root = Path(uipath_claude.__file__).resolve().parents[2]
    fallback = inferred_root / "templates" / "uiplan"
    if (fallback / "_spec-template.md").is_file():
        return fallback
    msg = f"UiPlan template kit missing: tried {direct} and {fallback}"
    raise FileNotFoundError(msg)


def _fill(tpl: str, mapping: dict[str, str]) -> str:
    out = tpl
    for k, v in mapping.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def _clip_one_line(text: str, limit: int = 220) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 14].rstrip() + " ... (truncated)"


def _needs_clarification(topic: str) -> str:
    return f"[NEEDS CLARIFICATION: {topic}]"


def _format_decision_logic_inventory(paradigm: str, pack: dict[str, Any]) -> dict[str, str]:
    if paradigm == "solution":
        return {
            "DECISION_1": "RouteAndExecutionDecision",
            "DECISION_1_OWNER": "Flow + DMN + agent boundary",
            "DECISION_1_WHY": "separate deterministic policy from semantic reasoning",
            "DECISION_1_INPUTS": "normalized request + confidence + policy fields",
            "DECISION_1_OUTPUTS": "route target + review flag + execution mode",
            "DECISION_1_REVIEW_TRIGGER": "policy requires review or low confidence",
        }
    if paradigm in ("modern-rpa", "coded-automation"):
        return {
            "DECISION_1": "WorkflowBranchDecision",
            "DECISION_1_OWNER": "Main workflow",
            "DECISION_1_WHY": "route deterministic branches with auditability",
            "DECISION_1_INPUTS": "workflow inputs + queue/asset context",
            "DECISION_1_OUTPUTS": "selected branch + status update",
            "DECISION_1_REVIEW_TRIGGER": "business-rule exception",
        }
    if paradigm == "coded-agent":
        return {
            "DECISION_1": "AgentRouteDecision",
            "DECISION_1_OWNER": "LangGraph entrypoint",
            "DECISION_1_WHY": "classify intent and choose executable path",
            "DECISION_1_INPUTS": "request payload + retrieval/tool outputs",
            "DECISION_1_OUTPUTS": "typed response schema + route metadata",
            "DECISION_1_REVIEW_TRIGGER": "unsafe response or low confidence",
        }
    if paradigm == "maestro-flow":
        return {
            "DECISION_1": "FlowRoutingDecision",
            "DECISION_1_OWNER": "Flow route node",
            "DECISION_1_WHY": "control orchestration paths across systems",
            "DECISION_1_INPUTS": "trigger payload + branch conditions",
            "DECISION_1_OUTPUTS": "selected branch + downstream task",
            "DECISION_1_REVIEW_TRIGGER": "human approval branch selected",
        }
    return {
        "DECISION_1": _needs_clarification("primary decision name"),
        "DECISION_1_OWNER": _needs_clarification("owner surface"),
        "DECISION_1_WHY": _needs_clarification("decision rationale"),
        "DECISION_1_INPUTS": _needs_clarification("decision inputs"),
        "DECISION_1_OUTPUTS": _needs_clarification("decision outputs"),
        "DECISION_1_REVIEW_TRIGGER": _needs_clarification("human review trigger"),
    }


def _format_visibility_defaults(paradigm: str) -> dict[str, str]:
    build_family = cli_family(paradigm)
    return {
        "ALLOWED_SURFACES": {
            "solution": ".xaml, .flow, .dmn, coded-agent modules, bindings/resources",
            "modern-rpa": ".xaml workflows, queues/assets, project descriptors",
            "coded-automation": ".cs workflows, project descriptors, tests",
            "coded-agent": "langgraph/agent code, descriptors, tests, bindings",
            "maestro-flow": ".flow/.bpmn, bindings, invoked surfaces",
        }.get(paradigm, _needs_clarification("allowed build surfaces")),
        "EXPLICIT_EXCLUSIONS": "Legacy/VB/Classic/Production deploy from assistant session",
        "EVIDENCE_PATHS": "store gate evidence under `out/` per surface",
        "NAMING_CONVENTIONS": "align project/workflow names with descriptors and bindings",
        "ARTIFACT_1_PATH": _needs_clarification("primary artifact path"),
        "ARTIFACT_1_TYPE": _needs_clarification("artifact type/surface"),
        "ARTIFACT_1_STORY": "US1",
        "ARTIFACT_1_ENTRYPOINT": _needs_clarification("artifact entrypoint"),
        "ARTIFACT_1_ANTISTUB": "placeholder-only scaffold (no real activity/node wiring)",
        "ARTIFACT_1_EVIDENCE": "analyze/test/smoke evidence file in `out/`",
        "DEP_1_PACKAGE": _needs_clarification("package or tool name"),
        "DEP_1_ACTIVITY_CONNECTOR": _needs_clarification("activity/connector id"),
        "DEP_1_ARTIFACT": _needs_clarification("artifact path using dependency"),
        "DEP_1_REASON": "required for in-scope behavior",
        "DEP_1_VERSION_SOURCE": "descriptor or library resolution",
        "DEP_1_EVIDENCE": "validation/test output path",
        "SURFACE_1_NAME": _needs_clarification("surface/resource name"),
        "SURFACE_1_DESCRIPTOR": _needs_clarification("descriptor file"),
        "SURFACE_1_BOUNDARY": _needs_clarification("invocation boundary"),
        "SURFACE_1_IO": _needs_clarification("typed inputs/outputs"),
        "SURFACE_1_OWNER": _needs_clarification("owner skill/project"),
        "SURFACE_1_EVIDENCE": "runtime or test evidence path",
        "LOG_1_SURFACE": _needs_clarification("workflow surface for logging"),
        "LOG_1_PHASES": "start, input summary, decision, status transition, exception, terminal",
        "LOG_1_CORRELATION": "propagate one correlation id across invoked boundaries",
        "LOG_1_ASSERTIONS": "assert correlation id and phase markers in logs",
        "LOG_1_EVIDENCE": "log capture path in `out/`",
        "SCAFFOLD_1_ARTIFACT": _needs_clarification("artifact path"),
        "SCAFFOLD_1_SOURCE": _needs_clarification("starter template/scaffold source"),
        "SCAFFOLD_1_PRESERVE": "descriptor files and generated structure required by template",
        "SCAFFOLD_1_REQUIRED": "real workflow/node implementation for scoped story",
        "SCAFFOLD_1_REJECT_SIGNAL": "stub marker text (placeholder/contract-only/would invoke)",
        "VERIFY_1_SURFACE": _needs_clarification("surface being verified"),
        "VERIFY_1_FAMILY": build_family,
        "VERIFY_1_COMMAND": _needs_clarification("concrete verification command"),
        "VERIFY_1_DONE_WHEN": "command succeeds and expected assertions pass",
        "VERIFY_1_EVIDENCE": "command output path under `out/`",
        "WF_1_PATH": _needs_clarification("workflow artifact path"),
        "WF_1_DIAGRAM_SECTION": "`spec.md` `### Workflow surface visual catalog (required)`",
        "WF_1_MANDATORY_ACTIVITIES": _needs_clarification("mandatory activities/nodes"),
        "WF_1_SKILL_TOOL_ROUTE": "[skill:uipath-rpa] + uipath_doc_get_activity (or matching specialist)",
        "WF_1_EVIDENCE": "analyze/validate/test evidence path under `out/`",
    }


def _source_documents_markdown(pack: dict[str, Any]) -> str:
    """Append source paths only; source text is context, not generated document body."""
    docs = pack.get("source_documents") or []
    if not isinstance(docs, list) or not docs:
        return ""
    lines = [
        "## Source traceability",
        "",
        "_The sections above (user stories, requirements) are the build-ready specification. "
        "Below are the source paths used as context; source content is intentionally not copied._",
        "",
    ]
    for doc in docs[:5]:
        if not isinstance(doc, dict):
            continue
        name = str(doc.get("name") or doc.get("path") or "source document")
        path = str(doc.get("path") or "")
        kind = str(doc.get("kind") or "markdown")
        lines.append(f"### {name}")
        if path:
            lines.append(f"- **Path**: `{path}`")
        lines.append(f"- **Kind**: {kind}")
        if doc.get("error"):
            lines.append(f"- **Read error**: {doc['error']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n\n"


def _insert_source_documents(spec_body: str, pack: dict[str, Any]) -> str:
    section = _source_documents_markdown(pack)
    if not section:
        return spec_body
    # Appended at end so "User Scenarios" and "Requirements" remain the first work areas (not a wall of PDD).
    return spec_body.rstrip() + "\n\n" + section


def _source_doc_summary(pack: dict[str, Any]) -> tuple[str | None, str | None]:
    docs = pack.get("source_documents") or []
    if not isinstance(docs, list) or not docs:
        return None, None
    first = docs[0] if isinstance(docs[0], dict) else {}
    name = str(first.get("name") or "source document")
    return name, None


def _format_source_routing_snippet(repo: Path, pack: dict[str, Any]) -> str:
    """Explicit MCP / discovery / subagent routing for spec.md and plan.md."""
    ctx_path = repo / ".claude" / "rules" / "project-context.md"
    present = pack.get("project_context_present")
    if not isinstance(present, bool):
        present = ctx_path.is_file()
    lines: list[str] = []
    if present:
        lines.append(
            "- **Project discovery**: `.claude/rules/project-context.md` exists; refresh via "
            "`[agent:uipath-project-discovery-agent]` when markers drift."
        )
    else:
        lines.append(
            "- **Project discovery (blocking precondition)**: `.claude/rules/project-context.md` is "
            "**missing**. Run `[agent:uipath-project-discovery-agent]` and capture project-context "
            "before locking scope or production edits."
        )
    lines.extend(
        [
            "- **Library MCP**: `uipath_library_search` (ranked search) and `uipath_library_lookup` "
            "(book/section precision).",
            "- **AskAI-style fallback**: `query_uipath_docs` (and `[askai:topic]` notes in tasks) when "
            "library evidence is insufficient.",
            "- **Activity docs MCP**: `uipath_doc_get_activity` / `uipath_doc_list_packages` before naming "
            "activities or pinning package versions.",
            "- **Specialists / subagents**: cite `[skill:...]` for build personas; split heavy work via "
            "subagents or `Task` for isolated discovery or implementation.",
        ]
    )
    return "\n".join(lines)


def _format_grounding_context(pack: dict[str, Any]) -> str:
    """Render grounding inputs into plan.md so later task generation sees them."""
    lines: list[str] = []

    planner = pack.get("planning_skill")
    if isinstance(planner, dict) and planner.get("name"):
        lines.append(f"- Planning route: `[skill:{planner['name']}]`")
        excerpt = planner.get("excerpt")
        if excerpt:
            lines.append(f"  - Excerpt: {_clip_one_line(str(excerpt), 300)}")

    matched = pack.get("matched_skills") or []
    if isinstance(matched, list) and matched:
        lines.append("- Matched specialist skills:")
        for skill in matched[:5]:
            if not isinstance(skill, dict):
                continue
            name = str(skill.get("name") or "unknown")
            desc = _clip_one_line(str(skill.get("description") or ""), 180)
            lines.append(f"  - `[skill:{name}]` - {desc}")
            excerpt = skill.get("excerpt")
            if excerpt:
                lines.append(f"    - Excerpt: {_clip_one_line(str(excerpt), 260)}")

    source_docs = pack.get("source_documents") or []
    if isinstance(source_docs, list) and source_docs:
        lines.append("- Source documents used as context (content intentionally not copied):")
        for doc in source_docs[:5]:
            if not isinstance(doc, dict):
                continue
            name = str(doc.get("name") or doc.get("path") or "source document")
            path = str(doc.get("path") or "")
            lines.append(f"  - `{name}`: `{path}`")
            if doc.get("error"):
                lines.append(f"    - Read error: {_clip_one_line(str(doc['error']), 180)}")

    lookups = pack.get("knowledge_lookups") or []
    if isinstance(lookups, list) and lookups:
        lines.append("- Library / AskAI-style knowledge lookups:")
        for hit in lookups[:3]:
            if not isinstance(hit, dict):
                continue
            query = str(hit.get("query") or "").strip()
            source = str(hit.get("source") or "").strip()
            prefix = f"  - `{query}`" if query else "  - lookup"
            if source:
                prefix += f" ({source})"
            lines.append(prefix)
            excerpt = hit.get("excerpt") or hit.get("error")
            if excerpt:
                lines.append(f"    - Excerpt: {_clip_one_line(str(excerpt), 300)}")

    library_hits = pack.get("library_hits") or []
    if isinstance(library_hits, list) and library_hits:
        lines.append("- Library search hits:")
        for hit in library_hits[:3]:
            if not isinstance(hit, dict):
                continue
            query = str(hit.get("query") or "").strip()
            excerpt = hit.get("excerpt") or hit.get("error")
            lines.append(f"  - `{query}`: {_clip_one_line(str(excerpt or ''), 260)}")

    discovery = pack.get("project_discovery_agent")
    if isinstance(discovery, dict) and discovery.get("name"):
        lines.append(f"- Project discovery persona: `[agent:{discovery['name']}]`")
        excerpt = discovery.get("excerpt")
        if excerpt:
            lines.append(f"  - Excerpt: {_clip_one_line(str(excerpt), 300)}")

    unanswered = pack.get("unanswered") or []
    if isinstance(unanswered, list) and unanswered:
        lines.append("- Open grounding questions:")
        lines.extend(f"  - {item}" for item in unanswered[:5])

    return "\n".join(lines) if lines else "_No grounding context available._"


def _format_workflow_shape_block(paradigm: str) -> str:
    """XAML-first workflow typing table for plan.md (replace row labels per feature)."""
    intro = (
        "**XAML-first default:** Prefer `.xaml` workflows for Orchestrator-driven orchestration; "
        "add a coded-agent sub-project only when semantic LLM / tooling clearly requires it "
        "(state that justification in the Structure Decision).\n"
    )
    table_header = (
        "\n| Process / project (rename to match repo) | Workflow type | One-line rationale |\n"
        "| --- | --- | --- |\n"
    )
    if paradigm == "solution":
        rows = (
            "| Dispatcher / intake RPA | Sequence or Flowchart | linear dequeue + routing |\n"
            "| Analyzer host / queue consumer | Sequence or Flowchart | transactional steps |\n"
            "| Human wait / suspend-resume | Long Running Workflow | waits on Action Center / human |\n"
            "| Analyzer agent (Python) | N/A (coded agent) | semantic reasoning / tools only |\n"
        )
    elif paradigm in ("modern-rpa", "library", "tests"):
        rows = (
            "| Main automation | Sequence or Flowchart | (fill from SDD) |\n"
            "| Human or external wait | Long Running Workflow | only if suspend/resume is required |\n"
        )
    elif paradigm == "coded-automation":
        rows = "| Coded workflow entry | C# workflow (see project) | (fill) |\n"
    else:
        rows = (
            "| If this paradigm still ships XAML sub-processes | Sequence / Flowchart / LRW | "
            "document each file |\n"
        )
    footer = (
        "\nPick **one** of Sequence, Flowchart, State Machine, or Long Running Workflow per "
        "top-level `.xaml` file; use **Long Running** only when the design truly waits across "
        "human or external events."
    )
    return intro + table_header + rows + footer


def _format_logging_verification_block(paradigm: str) -> str:
    """Shared logging + smoke + log-assertion contract for plan.md."""
    cli_bits = (
        "`uipcli solution restore` -> `uipcli solution analyze` -> `uipcli solution pack`"
        if paradigm == "solution"
        else "`uipcli package restore` -> `uipcli package analyze` -> `uipcli test run` -> "
        "`uipcli package pack`"
    )
    return "\n".join(
        [
            "**Logging contract** (orchestration workflows):",
            "- `LogMessage` (Info/Warn/Error) at: run start, non-PII input summary, branch decisions, "
            "status transitions, exceptions, final summary.",
            "- Propagate a **correlation id** (queue item id, transaction id, or GUID) across "
            "`Invoke Workflow File` boundaries where applicable.",
            "",
            "**Verification contract:**",
            f"- Build gates: {cli_bits}; stop on analyzer errors.",
            "- **Smoke run:** after pack, run a safe local/unattended job, `uipcli job run`, or "
            "`uip rpa run-file` (document exact command in tasks) — never Production.",
            "- **Log assertions:** capture robot/job logs; assert expected substrings (correlation id, "
            "phase markers, terminal status) for happy path and at least one failure path.",
            "",
            "**Expression language:** C# (`CSharp`) for new modern XAML; VisualBasic only when "
            "the plan explicitly records a legacy VisualBasic project.",
        ]
    )


def _format_planner_handoff(pack: dict[str, Any]) -> str:
    route = pack.get("planner_route") or []
    lines = [
        "- Start with `[skill:uipath-planner]` to confirm project type, implementation paradigm, and execution sequence.",
        "- Ensure `.claude/rules/project-context.md` exists; if missing, run `[agent:uipath-project-discovery-agent]` before locking scope or tasks.",
        "- For RPA or Solution scopes, name **workflow types** (Sequence / Flowchart / State Machine / Long Running) per `.xaml` process before implementation.",
    ]
    if isinstance(route, list) and route:
        lines.append("- Planned capability route:")
        for index, step in enumerate(route, start=1):
            lines.append(f"  {index}. {step}")

    matched = pack.get("matched_skills") or []
    if isinstance(matched, list) and matched:
        lines.append("- Specialist build personas:")
        for skill in matched[:5]:
            if not isinstance(skill, dict) or not skill.get("name"):
                continue
            name = str(skill["name"])
            desc = _clip_one_line(str(skill.get("description") or ""), 180)
            lines.append(f"  - `[skill:{name}]`: {desc}")

    lines.extend(
        [
            "- Use `uipath_library_search` / `uipath_library_lookup` and `query_uipath_docs` before adding "
            "packages, CLI flags, activities, SDK calls, or platform resources; use `uipath_doc_get_activity` "
            "when activity semantics matter.",
            "- Use subagents when work can be split across discovery, implementation, testing, documentation, or review.",
            "- `/uiplan-implement` must run review first, read `.meta.yaml` for `status: accepted`, ask before "
            "source edits, then execute `tasks.md` with these personas and gates.",
        ]
    )
    return "\n".join(lines)


def _format_task_planner_handoff(pack: dict[str, Any]) -> str:
    matched = pack.get("matched_skills") or []
    skill_names = [
        str(skill.get("name"))
        for skill in matched
        if isinstance(skill, dict) and skill.get("name")
    ]
    specialist_text = ", ".join(f"`[skill:{name}]`" for name in skill_names[:5])
    if not specialist_text:
        specialist_text = "the specialist skill(s) selected in `plan.md`"
    return (
        "Run the planner handoff from `plan.md`: confirm `[skill:uipath-planner]`, "
        "`[agent:uipath-project-discovery-agent]`, "
        f"{specialist_text}, `uipath_library_search` / `uipath_library_lookup`, `query_uipath_docs`, "
        "`uipath_doc_get_activity` when needed, and any useful subagents "
        "are available before source edits."
    )


def _dependency_hint(pack: dict[str, Any]) -> str:
    matched = pack.get("matched_skills") or []
    names = [
        str(skill.get("name"))
        for skill in matched
        if isinstance(skill, dict) and skill.get("name")
    ]
    if not names:
        return "UiPath.* activities / SDK per project-context."
    return "Project dependencies should follow " + ", ".join(f"[skill:{name}]" for name in names[:5])


def _detect_paradigm(repo: Path, meta: dict[str, Any], arguments: dict[str, Any]) -> str:
    requested = normalize_paradigm(str(arguments.get("paradigm", "")).strip())
    if requested != "unknown":
        return requested
    from_meta = normalize_paradigm(str(meta.get("project_type", "")).strip())
    if from_meta != "unknown":
        return from_meta
    has_project_json = (repo / "project.json").is_file()
    has_xaml = any(repo.rglob("*.xaml"))
    has_pyproject = (repo / "pyproject.toml").is_file()
    has_agent_marker = any((repo / name).is_file() for name in ("langgraph.json", "agent_framework.json", "llama_index.json"))
    return infer_paradigm_from_files(
        has_project_json=has_project_json,
        has_xaml=has_xaml,
        has_pyproject=has_pyproject,
        has_agent_marker=has_agent_marker,
        has_solution=(repo / "solution.uipx").is_file(),
        has_coded_app=(repo / "app.config.json").is_file() and (repo / "action-schema.json").is_file(),
        has_case_plan=(repo / "caseplan.json").is_file(),
        has_api_workflow=(repo / "api-workflow.json").is_file(),
        has_maestro_file=any(repo.rglob("*.bpmn")) or any(repo.rglob("*.flow")),
    )


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


_DATED_FOLDER_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9_-]+$")


def _argument_plan_ref(arguments: dict[str, Any]) -> str:
    for key in ("path", "folder", "filename", "slug"):
        value = arguments.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise ValueError("provide a UiPlan slug, folder name, or folder path")


def _repo_from_uiplan_path(path: Path) -> Path | None:
    folder = path if path.is_dir() else path.parent
    for parent in (folder, *folder.parents):
        if parent.name == "plans" and parent.parent.name == ".cursor":
            return parent.parent.parent.resolve()
        if parent.name == "plans" and parent.parent.name == "docs":
            return parent.parent.parent.resolve()
    return None


def _checkout_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _candidate_repo_roots(arguments: dict[str, Any], ref: str) -> list[Path]:
    import os  # noqa: PLC0415

    candidates: list[Path] = []

    def add(path: Path | str | None) -> None:
        if path is None:
            return
        try:
            resolved = Path(path).expanduser().resolve()
        except OSError:
            return
        if resolved not in candidates:
            candidates.append(resolved)

    explicit_root = arguments.get("project_root")
    if isinstance(explicit_root, str) and explicit_root.strip():
        add(explicit_root)

    ref_path = Path(ref).expanduser()
    if ref_path.is_absolute() or "/" in ref or "\\" in ref:
        direct = ref_path.resolve()
        if direct.exists():
            repo = _repo_from_uiplan_path(direct)
            if repo is not None:
                add(repo)

    add(os.environ.get("WORKSPACE_ROOT"))
    add(Path.cwd())
    add(_checkout_repo_root())
    return candidates


def _is_folder_or_file_ref(ref: str) -> bool:
    name = Path(ref).name
    return (
        "/" in ref
        or "\\" in ref
        or name.endswith(".md")
        or bool(_DATED_FOLDER_RE.match(name))
    )


def _resolve_existing_uiplan(arguments: dict[str, Any]) -> tuple[Path, Any, str]:
    from mcp_server.tools.plan_tools import _drafts_dir, _plans_dir  # noqa: PLC0415

    ref = _argument_plan_ref(arguments)
    filename = Path(ref).name if _is_folder_or_file_ref(ref) else None
    slug = None if filename else ref
    errors: list[str] = []

    for repo in _candidate_repo_roots(arguments, ref):
        drafts = _drafts_dir(repo)
        plans = _plans_dir(repo)
        try:
            resolved = resolve_plan_path(drafts, filename, slug, extra_dirs=[plans])
            if resolved.kind != "folder" or not is_folder_plan(resolved.path):
                raise ValueError("resolved plan is not a folder-shaped UiPlan draft")
            meta = load_folder_meta(resolved.path)
            resolved_slug = str(meta.get("slug") or slug or resolved.path.name)
            return repo, resolved, resolved_slug
        except Exception as exc:  # noqa: BLE001 - aggregate context for tool callers
            errors.append(f"{repo}: {exc}")

    joined = "; ".join(errors[-3:]) if errors else "no candidate repo roots"
    raise FileNotFoundError(
        f"Could not resolve UiPlan {ref!r}. Pass a metadata slug, dated folder name, "
        f"or full folder path. Tried: {joined}"
    )


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

    paradigm = normalize_paradigm(str(arguments.get("paradigm", project_type)))

    date = _today_iso()
    folder_name = f"{date}-{slug}"
    drafts = _drafts_dir(repo)
    folder = drafts / folder_name
    if folder.exists():
        raise FileExistsError(f"UiPlan folder already exists: {folder}")

    cites = " ".join(pack.get("suggested_citations") or [])
    source_name, _source_summary = _source_doc_summary(pack)
    if source_name:
        us1_body = (
            f"Translate `{source_name}` into a build-ready UiPath specification using the "
            "document as context, without copying its prose into the generated bundle."
        )
        fr_001 = f"implement the process requirements captured in `{source_name}`"
        entity_1 = "SourceProcess"
        entity_1_desc = f"Business process described by `{source_name}`."
        sc_001 = f"Spec, plan, and tasks trace back to `{source_name}` without generic placeholders."
        assumption_1 = f"`{source_name}` is the authoritative input until the human edits this spec."
    else:
        us1_body = f"Deliver the core outcome for: {intent}"
        fr_001 = f"support the outcome described in intent ({intent[:120]})"
        entity_1 = "PrimaryEntity"
        entity_1_desc = "Core business object for this feature."
        sc_001 = "Measurable outcome tied to intent (latency, accuracy, volume)."
        assumption_1 = "List environment assumptions (Orchestrator folder, assets, etc.)."

    tpl = _load_tpl(repo, "_spec-template.md")
    mapping = {
        "TITLE": title,
        "DATE": date,
        "INTENT": intent,
        "GROUNDING_CITATIONS": cites or "[skill:uipath-planner]",
        "US1_TITLE": "MVP slice",
        "US1_BODY": us1_body,
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
        "FR_001": fr_001,
        "FR_002": "log decisions for auditability",
        "FR_003": "operate within tenant security constraints",
        "ENTITY_1": entity_1,
        "ENTITY_1_DESC": entity_1_desc,
        "SC_001": sc_001,
        "ASSUMPTION_1": assumption_1,
        "BUILD_ENTRYPOINT": "`tasks.md` after review passes and the bundle is accepted.",
        "IMPLEMENTATION_SCOPE": "Only files, projects, assets, queues, and docs named in plan.md/tasks.md.",
        "BUILD_COMMAND": (
            f"`/uiplan-implement {slug}` after `uipath_plan_review` passes and "
            "`uipath_plan_accept` records human approval. Use `scaffold-code` "
            "only for optional local runtime/adaptor checks."
        ),
        "QUALITY_GATES": (
            "restore -> analyze -> test -> pack; add smoke run + robot log assertions (correlation id, "
            "phases, terminal status); deploy only with explicit approval."
        ),
        "PARADIGM": paradigm,
        "TARGET_STACK": stack_line(paradigm),
        "CLI_FAMILY": cli_family(paradigm),
        "DEPLOY_GATE": deploy_gate(paradigm),
        "SOURCE_ROUTING_SNIPPET": _format_source_routing_snippet(repo, pack),
        "PROJECT_TYPE": project_type,
        "LANG_VERSION": stack_line(paradigm),
        "TARGET_PLATFORM": "Automation Cloud / Windows robots (confirm folder and permissions).",
        "DEPS": _dependency_hint(pack),
    }
    mapping.update(_format_decision_logic_inventory(paradigm, pack))
    mapping.update(_format_visibility_defaults(paradigm))
    spec_body = _insert_source_documents(_fill(tpl, mapping), pack)

    folder.mkdir(parents=True)
    meta = {
        "slug": slug,
        "title": title,
        "date": date,
        "status": "draft",
        "owner": str(owner),
        "project_type": project_type,
        "plan_kind": "uiplan",
        "linked_pdd": (
            str((pack.get("source_documents") or [{}])[0].get("path", ""))
            if pack.get("source_documents")
            else ""
        ),
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
    from mcp_server.tools.plan_tools import _today_iso  # noqa: PLC0415

    repo, resolved, slug = _resolve_existing_uiplan(arguments)
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
        "SUMMARY": (
            f"Implementation approach derived from spec for {title}. "
            "The plan is grounded in the planning skill, matched specialist "
            "skills, library/AskAI-style lookups, project context, and constitution gates."
        ),
        "GROUNDING_CONTEXT": _format_grounding_context(pack),
        "SOURCE_ROUTING_SNIPPET": _format_source_routing_snippet(repo, pack),
        "PLANNER_HANDOFF": _format_planner_handoff(pack),
        "LANG_VERSION": "C# 12 / .NET 8 (Modern) or Python 3.11+ for coded agents — adjust per project-context.",
        "DEPS": _dependency_hint(pack),
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
    paradigm = _detect_paradigm(repo, meta, arguments)
    mapping["WORKFLOW_SHAPE_BLOCK"] = _format_workflow_shape_block(paradigm)
    mapping["LOGGING_VERIFICATION_BLOCK"] = _format_logging_verification_block(paradigm)
    mapping.update(
        {
            "PARADIGM": paradigm,
            "CLI_FAMILY": cli_family(paradigm),
            "CODE_STRUCTURE_BLOCK": code_structure_block(paradigm),
            "BUILD_LOOP_BLOCK": build_loop_block(paradigm),
            "LANG_VERSION": stack_line(paradigm),
        }
    )
    plan_body = _fill(tpl, mapping)
    (folder / "plan.md").write_text(plan_body, encoding="utf-8")
    return {
        "status": "ok",
        "path": str(folder / "plan.md"),
        "slug": slug,
        "folder_name": folder.name,
    }


def call_uiplan_tasks_new(arguments: dict[str, Any]) -> dict[str, Any]:
    repo, resolved, slug = _resolve_existing_uiplan(arguments)
    folder = resolved.path
    files = read_uiplan_files(resolved)
    spec = files.get("spec.md", "")
    plan = files.get("plan.md", "")
    if not plan.strip():
        raise ValueError("plan.md is empty — run uipath_plan_plan_new first")
    if "## Development Handoff" not in spec:
        raise ValueError("spec.md is missing Development Handoff — run uipath_plan_spec_new first")
    required_plan_sections = (
        "## Project Structure",
        "### Paradigm build loop",
        "## Per-project workflow and platform inventory",
        "## Planner Route & Specialist Handoff",
        "## Project Inventory",
        "## Project Graph",
        "## Workflow Catalog",
        "## Activity Inventory",
        "## Bindings and Environment",
        "## Skill and Subagent Routing",
        "## Stack Policy",
    )
    missing_sections = [section for section in required_plan_sections if section not in plan]
    if missing_sections:
        joined = ", ".join(missing_sections)
        raise ValueError(
            "plan.md is missing required task-generation preconditions "
            f"({joined}) — rerun uipath_plan_plan_new after discovery/grounding."
        )

    pack = arguments.get("grounding_pack")
    if not isinstance(pack, dict) or pack.get("status") != "ok":
        pack = build_grounding_pack(repo, spec[:500])

    meta = load_folder_meta(folder)
    title = str(meta.get("title", slug))
    cites = " ".join(pack.get("suggested_citations") or [])
    matched = pack.get("matched_skills") or []
    first_skill = ""
    for skill in matched:
        if isinstance(skill, dict) and skill.get("name"):
            first_skill = str(skill["name"])
            break
    skill_tag = f"[skill:{first_skill}]" if first_skill else "[skill:uipath-planner]"
    tpl = _load_tpl(repo, "_tasks-template.md")
    mapping = {
        "TITLE": title,
        "GROUNDING_CITATIONS": cites,
        "T001": (
            "Create the contract baseline from `plan.md`: test fixture paths, queue/asset/binding "
            "schemas, and workflow ownership notes for each build surface; verify baseline files exist "
            "before implementation starts."
        ),
        "T002": (
            "Implement shared foundational artifacts required by all stories (schemas, reusable helpers, "
            "common validation utilities) and prove they pass the first targeted test/analyze gate."
        ),
        "PLANNER_TASKS": _format_task_planner_handoff(pack),
        "US1_TITLE": "MVP slice",
        "US1_GOAL": "Deliver first usable increment from spec User Story 1.",
        "US1_IND_TEST": "Run the Independent Test from spec for US1.",
        "T010_TEST": (
            "Write failing automated test at the exact path from `plan.md` (e.g. `tests/test_us1_mvp.py`); "
            "run `uv run pytest tests/test_us1_mvp.py -q` or `uipcli test run -a <projectKey> .`; "
            "ground APIs with `uipath_library_search` / `uipath_library_lookup`; **Runtime evidence**: "
            "pytest JUnit or `TestResults/` output path."
        ),
        "T011_IMPL": (
            f"Complete US1 using **separate** checklist lines from `### Paradigm-specific tasks` "
            f"(e.g. `T011A`, `T011B`, …) when present — one bullet = one done gate; no merged half-tasks. "
            f"Use {skill_tag}; `uipath_library_search` / `uipath_library_lookup` / `uipath_doc_get_activity` "
            "before activities/SDKs on any line that adds `.xaml` / RPA activities (when RPA is in scope, "
            "build those workflows in-repo — do not treat them as optional). **Verification/evidence**: "
            "per sub-task; personal workspace default; Production requires explicit approval."
        ),
        "T020": "Documentation + README updates for operators.",
        "DEPENDENCIES_TEXT": "Phase 1 -> Phase 2 -> US1 -> Polish. Tests before implementation within each story.",
    }
    paradigm = _detect_paradigm(repo, meta, arguments)
    mapping.update(
        {
            "PARADIGM": paradigm,
            "CLI_FAMILY": cli_family(paradigm),
            "DEPLOY_GATE": deploy_gate(paradigm),
            "PARADIGM_TASK_BLOCKS": paradigm_task_blocks(paradigm),
        }
    )
    tasks_body = _fill(tpl, mapping)
    tasks_body += _resolved_activity_docs_markdown(spec, plan)
    tasks_body += _tdd_reference_append(repo)
    (folder / "tasks.md").write_text(tasks_body, encoding="utf-8")
    return {
        "status": "ok",
        "path": str(folder / "tasks.md"),
        "slug": slug,
        "folder_name": folder.name,
    }


def call_uiplan_review(arguments: dict[str, Any]) -> dict[str, Any]:
    repo, resolved, slug = _resolve_existing_uiplan(arguments)
    stage = arguments.get("stage") or "all"
    if stage not in ("spec", "plan", "tasks", "all"):
        raise ValueError("stage must be spec | plan | tasks | all")
    files = read_uiplan_files(resolved)
    gate_ids = _gate_ids(repo)
    meta = load_folder_meta(resolved.path)
    out = run_uiplan_review(
        spec=files.get("spec.md", ""),
        plan=files.get("plan.md", ""),
        tasks=files.get("tasks.md", ""),
        stage=stage,  # type: ignore[arg-type]
        gate_ids=gate_ids,
        repo=repo,
        slug=slug,
    )
    status = str(meta.get("status", "") or "").strip().lower()
    out["meta_status"] = str(meta.get("status", "") or "draft")
    out["acceptance_ready"] = status == "accepted"
    try:
        folder_rel = str(resolved.path.relative_to(repo))
    except ValueError:
        folder_rel = str(resolved.path)
    out["routing_metadata"] = {
        "slug": slug,
        "folder": folder_rel,
        "meta_status": out["meta_status"],
        "acceptance_ready": out["acceptance_ready"],
    }
    return out


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
        "spec": out_spec,
        "plan": out_plan,
        "tasks": out_tasks,
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
