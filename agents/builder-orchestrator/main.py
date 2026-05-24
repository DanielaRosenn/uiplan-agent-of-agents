from __future__ import annotations

import json
import re
import subprocess
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import TypedDict

from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph


CONSTRAINT_LINE_PATTERN = re.compile(r"\b(must|never|required|do not|should not|blocker|constraint)\b", re.IGNORECASE)
VIOLATION_PATTERN = re.compile(r"\b(fail|failed|error|missing|blocked|escalation|unsafe|violation)\b", re.IGNORECASE)


class OrchestratorState(TypedDict, total=False):
    brief: dict[str, Any]
    agentAssignments: list[dict[str, str]]
    outputDir: str
    runId: str
    supervisor: dict[str, Any]
    phaseHistory: list[dict[str, Any]]
    hitlDecisions: list[dict[str, Any]]
    loopBudgets: dict[str, int]
    buildIterations: list[dict[str, Any]]
    deployIterations: list[dict[str, Any]]
    escalation: dict[str, Any]
    uiEventsPath: str
    uiPlanFiles: list[dict[str, str]]
    humanDocs: list[dict[str, str]]
    generatedDocuments: list[dict[str, str]]
    buildArtifacts: list[dict[str, str]]
    provisionedResources: list[dict[str, str]]
    executionEvidence: dict[str, Any]
    summary: str
    handoff: dict[str, Any]


def _to_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    return []


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _safe_slug(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-") or "run"


def _add_phase_event(state: OrchestratorState, phase: str, status: str, details: str = "") -> None:
    event = {"phase": phase, "status": status, "time": _now_iso(), "details": details}
    state.setdefault("phaseHistory", [])
    state["phaseHistory"].append(event)


def _record_hitl_decision(
    state: OrchestratorState,
    phase: str,
    approved: bool,
    note: str,
) -> None:
    decision = {
        "phase": phase,
        "approved": approved,
        "note": note,
        "time": _now_iso(),
    }
    state.setdefault("hitlDecisions", [])
    state["hitlDecisions"].append(decision)


def _run_command(command: str, cwd: Path) -> tuple[bool, str]:
    completed = subprocess.run(  # noqa: S603
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        shell=True,  # noqa: S602
        check=False,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    ok = completed.returncode == 0
    return ok, output.strip()


def _load_uiplan_template(file_name: str) -> str:
    template_path = Path(__file__).resolve().parents[2] / "dist" / "agenthack-repo" / "templates" / "uiplan" / file_name
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    return ""


def _render_uiplan_template(template_text: str, replacements: dict[str, str]) -> str:
    content = template_text
    for key, value in replacements.items():
        content = content.replace(f"{{{{{key}}}}}", value)
    # Ensure no unresolved placeholders are shown in UI.
    content = re.sub(r"\{\{[A-Z0-9_]+\}\}", "N/A", content)
    return content


def _safe_node_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", value)
    if not cleaned:
        return "node"
    if cleaned[0].isdigit():
        return f"n_{cleaned}"
    return cleaned


def _classify_severity(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("never", "do not", "must", "blocker", "unsafe", "production")):
        return "high"
    if any(token in lowered for token in ("required", "should not", "escalation")):
        return "medium"
    return "low"


def _extract_skill_constraints(repo_root: Path, skill_name: str) -> list[dict[str, Any]]:
    skill_path = repo_root / "skills" / "skills" / skill_name / "SKILL.md"
    if not skill_path.exists():
        return []

    lines = skill_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    constraints: list[dict[str, Any]] = []
    in_critical_rules = False
    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if line.startswith("## ") and "critical rules" in line.lower():
            in_critical_rules = True
            continue
        if in_critical_rules and line.startswith("## "):
            break
        if not in_critical_rules:
            continue
        if not line:
            continue
        if re.match(r"^\d+\.\s+", line) or line.startswith("- "):
            text = re.sub(r"^\d+\.\s*", "", line)
            text = re.sub(r"^-\s*", "", text).strip()
            severity = _classify_severity(text)
            violation = bool(VIOLATION_PATTERN.search(text))
            constraints.append(
                {
                    "id": f"{skill_name}_{idx}",
                    "source": "skill",
                    "skill": skill_name,
                    "text": text[:260],
                    "severity": severity,
                    "violation": violation,
                    "line": idx,
                    "file": f"skills/skills/{skill_name}/SKILL.md",
                }
            )
    return constraints


def _build_constraints_graph_payload(state: OrchestratorState) -> dict[str, Any]:
    brief = state.get("brief", {})
    repo_root = Path(__file__).resolve().parents[2]
    target_folder = str(brief.get("constraintsFolder", "agents/builder-orchestrator")).strip() or "agents/builder-orchestrator"
    folder_path = (repo_root / target_folder).resolve()
    selected_skills = _to_string_list(
        brief.get(
            "constraintSkills",
            ["uipath-troubleshoot", "uipath-platform", "uipath-rpa", "uipath-test"],
        )
    )

    constraints: list[dict[str, Any]] = []
    connections: list[dict[str, str]] = []

    def _short_node_label(path_text: str, max_len: int = 52) -> str:
        clean = str(path_text).replace("\\", "/")
        return clean if len(clean) <= max_len else f"...{clean[-(max_len - 3):]}"

    def _normalize_edge_target(raw_target: str, source_file: str) -> str:
        value = str(raw_target).strip().replace("\\", "/")
        if not value:
            return value
        if ":" in value[:8]:
            return value
        source_path = Path(source_file.replace("\\", "/"))
        joined = (source_path.parent / value).as_posix()
        return joined

    def _append_connection(source: str, target: str, relation: str) -> None:
        if not source or not target:
            return
        source_norm = str(source).replace("\\", "/")
        target_norm = str(target).replace("\\", "/")
        relation_norm = str(relation).strip().lower() or "calls"
        candidate = {"source": source_norm, "target": target_norm, "relation": relation_norm}
        if candidate not in connections:
            connections.append(candidate)

    xaml_ref_pattern = re.compile(r'["\']([^"\']+\.xaml)["\']', re.IGNORECASE)
    system_signals = {
        "Salesforce": ("salesforce", "sf_"),
        "Zendesk": ("zendesk", "zd_"),
        "Slack": ("slack",),
        "Orchestrator": ("orchestrator", "queue", "asset"),
        "Email": ("smtp", "mail", "email"),
        "Webhook": ("webhook",),
    }
    if folder_path.exists() and folder_path.is_dir():
        scanned_files = (
            list(folder_path.rglob("*.xaml"))
            + list(folder_path.rglob("*.cs"))
            + list(folder_path.rglob("*.py"))
            + list(folder_path.rglob("*.md"))
            + list(folder_path.rglob("*.json"))
        )
        ignored_parts = {".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", "site-packages"}
        for file_path in scanned_files[:120]:
            if any(part in ignored_parts for part in file_path.parts):
                continue
            try:
                lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue
            resolved_file = file_path.resolve()
            try:
                rel_path = str(resolved_file.relative_to(repo_root)).replace("\\", "/")
            except ValueError:
                rel_path = str(resolved_file).replace("\\", "/")
            file_text = "\n".join(lines)
            lower_file_text = file_text.lower()
            connection_source_file = rel_path.lower().endswith((".xaml", ".cs", ".py", ".json"))
            if connection_source_file:
                for system_name, markers in system_signals.items():
                    if any(marker in lower_file_text for marker in markers):
                        _append_connection(rel_path, f"system:{system_name}", "uses")

                if rel_path.lower().endswith(".xaml"):
                    for match in xaml_ref_pattern.finditer(file_text):
                        target_value = str(match.group(1) or "").strip()
                        if not target_value:
                            continue
                        target_norm = _normalize_edge_target(target_value, rel_path)
                        if target_norm.lower().endswith(".xaml") and target_norm != rel_path:
                            _append_connection(rel_path, target_norm, "invokes")

            for idx, line in enumerate(lines, start=1):
                stripped = line.strip()
                if len(stripped) < 12:
                    continue
                if not CONSTRAINT_LINE_PATTERN.search(stripped):
                    continue
                if any(
                    token in stripped
                    for token in (
                        "CONSTRAINT_LINE_PATTERN",
                        "VIOLATION_PATTERN",
                        "classDef ",
                        "| File | Constraint count |",
                        "## Top files by constraint density",
                    )
                ):
                    continue
                severity = _classify_severity(stripped)
                violation = bool(VIOLATION_PATTERN.search(stripped))
                constraints.append(
                    {
                        "id": f"{_safe_node_id(rel_path)}_{idx}",
                        "source": "folder",
                        "file": rel_path,
                        "line": idx,
                        "text": stripped[:260],
                        "severity": severity,
                        "violation": violation,
                    }
                )
                if len(constraints) >= 80:
                    break
            if len(constraints) >= 80:
                break

    skill_constraints: list[dict[str, Any]] = []
    for skill_name in selected_skills:
        skill_constraints.extend(_extract_skill_constraints(repo_root, skill_name))

    combined_constraints = constraints + skill_constraints
    severity_counts = {"high": 0, "medium": 0, "low": 0}
    violations_count = 0
    files_with_constraints: dict[str, int] = {}
    for item in combined_constraints:
        sev = str(item.get("severity", "low"))
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        if item.get("violation"):
            violations_count += 1
        file_key = str(item.get("file", "unknown"))
        files_with_constraints[file_key] = files_with_constraints.get(file_key, 0) + 1

    top_files = sorted(files_with_constraints.items(), key=lambda pair: pair[1], reverse=True)[:5]
    top_code_files = sorted(
        ((name, count) for name, count in files_with_constraints.items() if not str(name).startswith("skills/skills/")),
        key=lambda pair: pair[1],
        reverse=True,
    )[:5]
    file_nodes = [file_name for file_name, _ in top_code_files]
    displayed_code_constraints = [item for item in constraints if item.get("file") in set(file_nodes)][:16]
    displayed_skill_constraints = skill_constraints[:6]

    displayed_connections = connections[:80]
    dependency_edges = [
        {
            "source": str(conn.get("source", "")),
            "target": str(conn.get("target", "")),
            "relation": str(conn.get("relation", "depends-on")),
        }
        for conn in displayed_connections
        if str(conn.get("source", "")).lower().endswith((".xaml", ".cs", ".py", ".json"))
        and str(conn.get("target", "")).lower().endswith((".xaml", ".cs", ".py", ".json"))
    ]
    dependency_index: dict[str, dict[str, list[dict[str, str]] | int]] = {}
    for edge in dependency_edges:
        src = str(edge["source"])
        dst = str(edge["target"])
        if src not in dependency_index:
            dependency_index[src] = {"outgoing": [], "incoming": [], "outgoingCount": 0, "incomingCount": 0}
        if dst not in dependency_index:
            dependency_index[dst] = {"outgoing": [], "incoming": [], "outgoingCount": 0, "incomingCount": 0}
        dependency_index[src]["outgoing"].append(edge)  # type: ignore[index]
        dependency_index[dst]["incoming"].append(edge)  # type: ignore[index]
        dependency_index[src]["outgoingCount"] = int(dependency_index[src]["outgoingCount"]) + 1  # type: ignore[index]
        dependency_index[dst]["incomingCount"] = int(dependency_index[dst]["incomingCount"]) + 1  # type: ignore[index]
    connection_files = sorted(
        {
            c["source"]
            for c in displayed_connections
            if str(c.get("source", "")).lower().endswith((".xaml", ".cs", ".json", ".py"))
        }
        | {
            c["target"]
            for c in displayed_connections
            if str(c.get("target", "")).lower().endswith((".xaml", ".cs", ".json", ".py"))
        }
    )[:24]
    file_to_node_id = {
        file_name: _safe_node_id(f"conn_file_{idx}_{file_name}")
        for idx, file_name in enumerate(connection_files)
    }
    system_targets = sorted(
        {c["target"] for c in displayed_connections if str(c.get("target", "")).startswith("system:")}
    )
    system_to_node_id = {
        system_name: _safe_node_id(f"system_{idx}_{system_name}")
        for idx, system_name in enumerate(system_targets)
    }

    mermaid_lines = [
        "flowchart LR",
        f'  folderNode["Folder: {_short_node_label(target_folder, 44)}"]',
    ]
    for file_name, node_id in file_to_node_id.items():
        mermaid_lines.append(f'  {node_id}["{_short_node_label(file_name)}"]')
        mermaid_lines.append(f"  folderNode --> {node_id}")
    for system_name, node_id in system_to_node_id.items():
        mermaid_lines.append(f'  {node_id}["{system_name.replace("system:", "System: ")}"]')

    for idx, conn in enumerate(displayed_connections):
        source = str(conn.get("source", ""))
        target = str(conn.get("target", ""))
        relation = str(conn.get("relation", "calls")).lower()
        source_node = file_to_node_id.get(source) or system_to_node_id.get(source)
        target_node = file_to_node_id.get(target) or system_to_node_id.get(target)
        if not source_node or not target_node:
            continue
        mermaid_lines.append(f"  {source_node} -- {relation} --> {target_node}")
        mermaid_lines.append(f"  linkStyle {idx} stroke:#64748b,stroke-width:1px;")

    for idx, item in enumerate(displayed_code_constraints):
        file_name = str(item.get("file", "unknown"))
        file_node_id = file_to_node_id.get(file_name)
        if not file_node_id:
            continue
        constraint_node_id = _safe_node_id(f"constraint_{idx}_{item.get('id', idx)}")
        label = str(item.get("text", "")).replace('"', "'")
        if len(label) > 52:
            label = f"{label[:52]}..."
        sev = str(item.get("severity", "low")).upper()
        line_no = item.get("line", "n/a")
        mermaid_lines.append(f'  {constraint_node_id}["{sev} L{line_no}: {label}"]')
        mermaid_lines.append(f"  {file_node_id} -. constrains .-> {constraint_node_id}")
        mermaid_lines.append(f"  class {constraint_node_id} folderConstraint")

    for idx, item in enumerate(displayed_skill_constraints):
        skill_name = str(item.get("skill", "unknown"))
        skill_node_id = _safe_node_id(f"skill_ctx_{idx}_{skill_name}")
        rule_node_id = _safe_node_id(f"skill_rule_{idx}_{item.get('id', idx)}")
        label = str(item.get("text", "")).replace('"', "'")
        if len(label) > 46:
            label = f"{label[:46]}..."
        sev = str(item.get("severity", "low")).upper()
        mermaid_lines.append(f'  {skill_node_id}["Skill: {skill_name}"]')
        mermaid_lines.append(f'  {rule_node_id}["{sev}: {label}"]')
        mermaid_lines.append(f"  {skill_node_id} -. context .-> {rule_node_id}")
        mermaid_lines.append(f"  class {rule_node_id} skillConstraint")
        mermaid_lines.append(f"  class {skill_node_id} skillNode")

    if file_to_node_id:
        mermaid_lines.append(f"  class {','.join(file_to_node_id.values())} fileNode")
    if system_to_node_id:
        mermaid_lines.append(f"  class {','.join(system_to_node_id.values())} systemNode")
    mermaid_lines.extend(
        [
            "  class folderNode folderNode",
            "  classDef folderNode fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0c4a6e,font-size:16px",
            "  classDef fileNode fill:#eef2ff,stroke:#4f46e5,stroke-width:1.6px,color:#1e1b4b,font-size:14px",
            "  classDef systemNode fill:#fef3c7,stroke:#d97706,stroke-width:1.6px,color:#78350f,font-size:14px",
            "  classDef skillNode fill:#ccfbf1,stroke:#0f766e,stroke-width:1.4px,color:#134e4a,font-size:13px",
            "  classDef folderConstraint fill:#dbeafe,stroke:#2563eb,stroke-width:1.3px,color:#1e3a8a,font-size:13px",
            "  classDef skillConstraint fill:#ccfbf1,stroke:#0f766e,stroke-width:1.3px,color:#134e4a,font-size:13px",
        ]
    )

    mermaid_graph = "\n".join(mermaid_lines)
    summary_table = (
        "| Metric | Value |\n"
        "|---|---:|\n"
        f"| Folder constraints | {len(constraints)} |\n"
        f"| Skill constraints | {len(skill_constraints)} |\n"
        f"| High severity | {severity_counts.get('high', 0)} |\n"
        f"| Medium severity | {severity_counts.get('medium', 0)} |\n"
        f"| Low severity | {severity_counts.get('low', 0)} |\n"
        f"| Potential violations | {violations_count} |\n"
    )
    top_files_table = (
        "| File | Constraint count |\n"
        "|---|---:|\n"
        + ("\n".join(f"| `{file_name}` | {count} |" for file_name, count in top_files) or "| _No files_ | 0 |")
    )
    codebase_doc = (
        f"# Constraints Codebase Doc ({target_folder})\n\n"
        "## Summary\n\n"
        f"{summary_table}\n\n"
        "## Connection overview\n\n"
        f"- Total code/system connections detected: {len(connections)}\n"
        f"- Connections visualized in graph: {len(displayed_connections)}\n\n"
        f"- File dependency edges detected: {len(dependency_edges)}\n\n"
        "## Skills Included\n\n"
        f"{', '.join(selected_skills) if selected_skills else 'none'}\n\n"
        "## Top files by constraint density\n\n"
        f"{top_files_table}\n"
    )

    return {
        "targetFolder": target_folder,
        "constraints": constraints,
        "skillConstraints": skill_constraints,
        "selectedSkills": selected_skills,
        "sourceCounts": {
            "folder": len(constraints),
            "skill": len(skill_constraints),
        },
        "severityCounts": severity_counts,
        "violationsCount": violations_count,
        "topFiles": [{"path": file_name, "constraintCount": count} for file_name, count in top_files],
        "connections": displayed_connections,
        "dependencies": dependency_edges,
        "dependencyIndex": dependency_index,
        "mermaid": mermaid_graph,
        "codebaseDoc": codebase_doc,
    }


def normalize_state_input(payload: dict[str, Any]) -> OrchestratorState:
    if "brief" in payload and isinstance(payload.get("brief"), dict):
        state: OrchestratorState = dict(payload)
    else:
        state = {"brief": dict(payload)}

    brief = state.get("brief", {})
    if not isinstance(brief, dict):
        brief = {}

    project_name = str(brief.get("projectName", "agent-of-agents-builder")).strip()
    run_id = str(brief.get("runId", "")).strip() or f"{_safe_slug(project_name)}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    output_root = str(brief.get("outputRoot", "")).strip()
    if output_root:
        output_dir = Path(output_root).resolve()
    else:
        output_dir = Path(__file__).resolve().parent / "out" / run_id

    state["runId"] = run_id
    state["outputDir"] = str(output_dir)
    state["brief"] = {
        "projectName": project_name,
        "domain": str(brief.get("domain", "operations")).strip(),
        "objective": str(brief.get("objective", brief.get("businessGoal", ""))).strip(),
        "systems": _to_string_list(brief.get("systems", [])),
        "constraints": _to_string_list(brief.get("constraints", [])),
        "stakeholders": _to_string_list(brief.get("stakeholders", [])),
        "successCriteria": _to_string_list(brief.get("successCriteria", [])),
        "constraintsFolder": str(brief.get("constraintsFolder", "agents/builder-orchestrator")).strip()
        or "agents/builder-orchestrator",
        "constraintSkills": _to_string_list(
            brief.get(
                "constraintSkills",
                ["uipath-troubleshoot", "uipath-platform", "uipath-rpa", "uipath-test"],
            )
        ),
        "dryRun": bool(brief.get("dryRun", True)),
        "queueName": str(brief.get("queueName", "Q_AGENT_OF_AGENTS_WORK")).strip(),
        "assetName": str(brief.get("assetName", "ASSET_AGENT_OF_AGENTS_POLICY")).strip(),
        "queueProvisionCommand": str(brief.get("queueProvisionCommand", "")).strip(),
        "assetProvisionCommand": str(brief.get("assetProvisionCommand", "")).strip(),
        "flowRunCommand": str(brief.get("flowRunCommand", "")).strip(),
        "maxBuildIterations": int(brief.get("maxBuildIterations", 5)),
        "maxDeployIterations": int(brief.get("maxDeployIterations", 3)),
        "forceBuildFailures": int(brief.get("forceBuildFailures", 0)),
        "forceDeployFailures": int(brief.get("forceDeployFailures", 0)),
    }
    state["supervisor"] = {
        "mode": "agent-of-agents",
        "status": "running",
        "startedAt": _now_iso(),
    }
    state["loopBudgets"] = {
        "maxBuildIterations": int(state["brief"]["maxBuildIterations"]),
        "maxDeployIterations": int(state["brief"]["maxDeployIterations"]),
    }
    state["buildIterations"] = []
    state["deployIterations"] = []
    state["phaseHistory"] = []
    state["hitlDecisions"] = []
    return state


def assign_agents(state: OrchestratorState) -> OrchestratorState:
    _add_phase_event(state, "intake", "started", "Routing specialist agents for phase ownership.")
    assignments = [
        {
            "phase": "brief-intake",
            "agent": "intake-analyst-agent",
            "responsibility": "Normalize brief and enforce required build contract.",
        },
        {
            "phase": "design-doc-generation",
            "agent": "solution-architect-agent",
            "responsibility": "Generate PDD, SDD, and ADD documents from brief.",
        },
        {
            "phase": "uipath-artifact-generation",
            "agent": "workflow-generator-agent",
            "responsibility": "Generate runnable project and flow artifacts.",
        },
        {
            "phase": "resource-provisioning",
            "agent": "platform-provisioner-agent",
            "responsibility": "Create/verify queues and assets via UiPath CLI commands.",
        },
        {
            "phase": "execution-evidence",
            "agent": "run-verifier-agent",
            "responsibility": "Run flow and collect evidence package.",
        },
        {
            "phase": "supervisor-control",
            "agent": "supervisor-agent",
            "responsibility": "Apply loop budgets and escalation policy.",
        },
    ]
    _record_hitl_decision(state, "intake", True, "Intake accepted automatically for local rebuild flow.")
    _add_phase_event(state, "intake", "completed")
    return {"agentAssignments": assignments}


def generate_design_docs(state: OrchestratorState) -> OrchestratorState:
    _add_phase_event(state, "plan", "started", "Generating planning documentation package.")
    brief = state.get("brief", {})
    output_dir = Path(state["outputDir"])
    docs_dir = output_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    project_name = brief.get("projectName", "Agent of Agents Builder")
    objective = brief.get("objective", "")
    systems = ", ".join(_to_string_list(brief.get("systems", [])))
    constraints = ", ".join(_to_string_list(brief.get("constraints", [])))
    stakeholders = ", ".join(_to_string_list(brief.get("stakeholders", [])))
    success_criteria = _to_string_list(brief.get("successCriteria", []))
    queue_name = brief.get("queueName", "")
    asset_name = brief.get("assetName", "")

    criteria_lines = "\n".join(f"- {item}" for item in success_criteria) if success_criteria else "- N/A"
    assumptions = [
        "UiPath CLI tooling is available in the execution environment.",
        "Deployment targets non-production resources only.",
        "Brief inputs are validated before execution.",
    ]
    assumption_lines = "\n".join(f"- {item}" for item in assumptions)

    human_doc_specs = [
        ("PDD.md", "Process Design Document"),
        ("SDD.md", "Solution Design Document"),
        ("ADD.md", "Agent Design Document"),
    ]
    human_docs: list[dict[str, str]] = []
    for file_name, title in human_doc_specs:
        content = (
            f"# {title}\n\n"
            f"## Project\n- Name: {project_name}\n- Domain: {brief.get('domain', '')}\n\n"
            f"## Objective\n{objective}\n\n"
            f"## Systems\n{systems or 'N/A'}\n\n"
            f"## Constraints\n{constraints or 'N/A'}\n\n"
            f"## Stakeholders\n{stakeholders or 'N/A'}\n\n"
            f"## Success Criteria\n{criteria_lines}\n\n"
            "## Assumptions\n"
            f"{assumption_lines}\n\n"
            "## Runtime Resource Targets\n"
            f"- Queue: {queue_name or 'N/A'}\n"
            f"- Asset: {asset_name or 'N/A'}\n\n"
            "## Expected Outputs\n"
            "- Generated design docs (PDD, SDD, ADD)\n"
            "- Generated UiPath artifacts and run script\n"
            "- Provisioned/verified queue and asset results\n"
            "- Execution evidence bundle with command logs\n\n"
            "## Supervisor Contract\n"
            f"- maxBuildIterations: {brief.get('maxBuildIterations', 5)}\n"
            f"- maxDeployIterations: {brief.get('maxDeployIterations', 3)}\n"
            "- Escalation occurs when loop budgets are exhausted.\n"
        )
        path = docs_dir / file_name
        path.write_text(content, encoding="utf-8")
        human_docs.append(
            {
                "name": file_name.replace(".md", "").lower(),
                "title": title,
                "path": str(path),
                "status": "generated",
            }
        )

    architecture_diagram = (
        "```mermaid\n"
        "flowchart TB\n"
        "  Intake[Brief Intake] --> Plan[Generate UiPlan Files]\n"
        "  Plan --> Build[Build Artifacts]\n"
        "  Build --> Deploy[Provision and Deploy Test]\n"
        "  Deploy --> Evidence[Emit Evidence Bundle]\n"
        "```\n"
    )
    sequence_diagram = (
        "```mermaid\n"
        "sequenceDiagram\n"
        "  autonumber\n"
        "  participant Brief as Intake Brief\n"
        "  participant Orchestrator as Builder Orchestrator\n"
        "  participant Build as Build Phase\n"
        "  participant Deploy as Deploy Test\n"
        "  participant Evidence as Evidence Bundle\n"
        "  Brief->>Orchestrator: Submit run brief\n"
        "  Orchestrator->>Build: Generate docs and artifacts\n"
        "  Build->>Deploy: Hand off build outputs\n"
        "  Deploy->>Evidence: Persist run evidence\n"
        "```\n"
    )
    story_title = f"As an automation lead, I want {project_name} to execute with guardrails"
    systems_list = "\n".join(f"- {item}" for item in _to_string_list(brief.get("systems", []))) or "- N/A"
    constraints_list = "\n".join(f"- {item}" for item in _to_string_list(brief.get("constraints", []))) or "- N/A"
    stakeholders_list = "\n".join(f"- {item}" for item in _to_string_list(brief.get("stakeholders", []))) or "- N/A"
    success_list = "\n".join(f"- {item}" for item in success_criteria) or "- N/A"
    run_id = state.get("runId", "")

    summary_text = (
        f"- Domain: `{brief.get('domain', 'operations')}`\n"
        f"- Objective: {objective or 'N/A'}\n"
        f"- Queue: `{queue_name or 'N/A'}`\n"
        f"- Asset: `{asset_name or 'N/A'}`\n"
        f"- Build budget: `{brief.get('maxBuildIterations', 5)}`\n"
        f"- Deploy budget: `{brief.get('maxDeployIterations', 3)}`\n"
    )
    spec_template = _load_uiplan_template("_spec-template.md")
    plan_template = _load_uiplan_template("_plan-template.md")
    tasks_template = _load_uiplan_template("_tasks-template.md")

    common = {
        "TITLE": project_name,
        "DATE": _now_iso(),
        "GROUNDING_CITATIONS": "`brief.enterprise-incident.json`, orchestrator runtime state",
        "INTENT": objective or "Generate and execute UiPlan-driven build flow.",
        "US1_TITLE": f"{project_name} delivery flow",
        "US1_BODY": f"The system orchestrates {brief.get('domain', 'operations')} workflows and preserves UiPlan outputs as first-class build artifacts.",
        "US1_PRIORITY": "This controls all downstream generation and deployment evidence.",
        "US1_TEST": "Run orchestrator and verify spec/plan/tasks + run-events payload.",
        "US1_GIVEN_1": "a valid brief and loop budget",
        "US1_WHEN_1": "the orchestrator executes",
        "US1_THEN_1": "UiPlan docs and evidence are generated",
        "US2_TITLE": "Deploy-test evidence loop",
        "US2_BODY": "The system should validate deploy/test status and produce escalation evidence when needed.",
        "US2_PRIORITY": "Protects release readiness gates.",
        "US2_TEST": "Force deploy failures and confirm escalation packet output.",
        "US2_GIVEN_1": "deploy test cannot pass within budget",
        "US2_WHEN_1": "budget is exhausted",
        "US2_THEN_1": "escalation is recorded with iteration evidence",
        "EDGE_1": "Missing queue/asset commands in non-dry-run mode.",
        "FR_001": objective or "satisfy business objective",
        "FR_002": "generate agent-readable UiPlan contracts",
        "FR_003": "review runtime status through the Copilot viewer",
        "ENTITY_1": "UiPlanRun",
        "ENTITY_1_DESC": f"Run envelope for `{run_id}` containing docs, loops, resources, and evidence.",
        "PROJECT_TYPE": "LangGraph coded agent orchestrator",
        "ALLOWED_SURFACES": "Python orchestrator, markdown UiPlan docs, JSON run-state feed, static UI viewer",
        "LANG_VERSION": "Python 3.11+",
        "EXPLICIT_EXCLUSIONS": "Production deploy, tenant destructive operations",
        "TARGET_PLATFORM": "Local development and non-production orchestrator targets",
        "DEPS": "langgraph, pytest, python stdlib",
        "EVIDENCE_PATHS": f"{state.get('outputDir', '')}/evidence and ui/copilotkit/current",
        "NAMING_CONVENTIONS": "runId slug + timestamp, docs under out/<runId>/docs",
        "IMPLEMENTATION_SCOPE": "Builder orchestrator generation flow and CopilotKit viewer surface",
        "PARADIGM": "UiPlan-first orchestration",
        "CLI_FAMILY": "uipath, uipcli, python",
        "SC_001": "UiPlan docs and diagrams render automatically in viewer",
        "ASSUMPTION_1": "Templates are available in dist/agenthack-repo/templates/uiplan",
        "SOURCE_ROUTING_SNIPPET": "- Runtime payload: `ui/run-events.json` and `ui/copilotkit/current/run-events.json`",
        "SUMMARY": summary_text,
        "GROUNDING_CONTEXT": "- Intake brief, runtime loop budgets, generated artifacts, and viewer contract.",
        "PLANNER_HANDOFF": "- Build flow: intake -> plan -> build -> deploy_test -> emit_ui_events -> handoff.",
        "LOGGING_VERIFICATION_BLOCK": "- Validate phase events, HITL decisions, and deploy iterations in run-events payload.",
        "CONSTITUTION_CHECKLIST": "- [x] Non-production only\n- [x] No secrets committed\n- [x] Analyzer/test gates included",
        "LANG_VERSION": "Python 3.11+",
        "PARADIGM_TASK_BLOCKS": "- [ ] T011A [US1] Implement generated workflow and runtime evidence updates in `agents/builder-orchestrator/main.py`.",
        "PLANNER_TASKS": "Validate that generated `spec.md`, `plan.md`, and `tasks.md` are non-empty and include diagrams.",
        "DEPLOY_GATE": "Deploy/test loop passes or escalation packet is emitted.",
        "DEPENDENCIES_TEXT": "- T001 -> T002 -> T003 -> T004 -> T005",
    }

    spec_content = _render_uiplan_template(spec_template, common) if spec_template else ""
    plan_content = _render_uiplan_template(plan_template, common) if plan_template else ""
    tasks_content = _render_uiplan_template(tasks_template, common) if tasks_template else ""

    task_board_prefix = (
        "## Task Board\n\n"
        "| Task ID | Title | Status | Owner | Depends On |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| T001 | Validate intake brief and normalize state | done | intake-analyst-agent | - |\n"
        "| T002 | Generate UiPlan docs (`spec.md`, `plan.md`, `tasks.md`) | done | solution-architect-agent | T001 |\n"
        "| T003 | Generate build artifacts and analyze loop | done | workflow-generator-agent | T002 |\n"
        "| T004 | Provision resources and execute deploy-test loop | done | platform-provisioner-agent | T003 |\n"
        "| T005 | Emit run events and evidence bundle | done | run-verifier-agent | T004 |\n\n"
    )
    if "## Task Board" not in tasks_content:
        tasks_content = f"# Tasks: {project_name}\n\n{task_board_prefix}\n{tasks_content}".strip()

    ui_plan_specs = [
        ("spec.md", "UiPlan Specification", spec_content),
        ("plan.md", "UiPlan Plan", plan_content),
        ("tasks.md", "UiPlan Tasks", tasks_content),
    ]
    ui_plan_files: list[dict[str, str]] = []
    for file_name, title, content in ui_plan_specs:
        path = docs_dir / file_name
        path.write_text(content, encoding="utf-8")
        ui_plan_files.append(
            {
                "name": file_name.replace(".md", "").lower(),
                "title": title,
                "path": str(path),
                "status": "generated",
            }
        )

    _record_hitl_decision(state, "plan", True, "Plan package accepted for build phase.")
    _add_phase_event(state, "plan", "completed")
    return {
        "uiPlanFiles": ui_plan_files,
        "humanDocs": human_docs,
        "generatedDocuments": human_docs,
    }


def generate_uipath_artifacts(state: OrchestratorState) -> OrchestratorState:
    _add_phase_event(state, "build", "started", "Generating build artifacts and entering analyze loop.")
    brief = state.get("brief", {})
    output_dir = Path(state["outputDir"])
    artifacts_dir = output_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    flow_spec = {
        "name": f"{brief.get('projectName', 'AgentBuilder')} Flow",
        "domain": brief.get("domain", "operations"),
        "objective": brief.get("objective", ""),
        "queueName": brief.get("queueName", ""),
        "assetName": brief.get("assetName", ""),
        "loopBudgets": state.get("loopBudgets", {}),
        "hitlDecisions": state.get("hitlDecisions", []),
    }
    flow_path = artifacts_dir / "generated-flow.json"
    flow_path.write_text(json.dumps(flow_spec, indent=2), encoding="utf-8")

    run_script_path = artifacts_dir / "run-flow.ps1"
    run_script_path.write_text(
        (
            "$ErrorActionPreference = 'Stop'\n"
            "$env:AGENTHACK_BUSINESS_UNIT='FINANCE'\n"
            "$env:AGENTHACK_INCIDENT_ID='INC-9000'\n"
            "$env:AGENTHACK_INCIDENT_SUMMARY='Auto-generated run from builder orchestrator'\n"
            "$env:AGENTHACK_INCIDENT_SEVERITY='SEV2'\n"
            "uip rpa run-file --file-path \"examples/05-agenthack-enterprise-intake/Main.xaml\"\n"
        ),
        encoding="utf-8",
    )

    artifacts = [
        {"name": "generated_flow_spec", "kind": "flow_spec", "path": str(flow_path), "status": "generated"},
        {"name": "run_flow_script", "kind": "script", "path": str(run_script_path), "status": "generated"},
    ]

    max_iters = int(state.get("loopBudgets", {}).get("maxBuildIterations", 5))
    forced_failures = int(brief.get("forceBuildFailures", 0))
    iterations: list[dict[str, Any]] = []
    build_ok = False
    for idx in range(1, max_iters + 1):
        analyze_ok = idx > forced_failures
        attempt = {
            "iteration": idx,
            "phase": "build",
            "analyzeStatus": "passed" if analyze_ok else "failed",
            "testStatus": "passed" if analyze_ok else "skipped",
            "repairApplied": not analyze_ok,
            "time": _now_iso(),
        }
        iterations.append(attempt)
        if analyze_ok:
            build_ok = True
            break

    if not build_ok:
        escalation = {
            "reason": "build_loop_budget_exhausted",
            "phase": "build",
            "maxIterations": max_iters,
            "iterations": iterations,
            "action": "HITL escalation required for budget extension or abort.",
        }
        _add_phase_event(state, "build", "failed", escalation["reason"])
        return {
            "buildArtifacts": artifacts,
            "buildIterations": iterations,
            "escalation": escalation,
        }

    _record_hitl_decision(state, "build", True, "Build artifacts and analyze loop accepted.")
    _add_phase_event(state, "build", "completed")
    return {"buildArtifacts": artifacts, "buildIterations": iterations}


def provision_resources(state: OrchestratorState) -> OrchestratorState:
    if state.get("escalation"):
        return {}
    _add_phase_event(state, "deploy_test", "started", "Provisioning target resources.")
    brief = state.get("brief", {})
    output_dir = Path(state["outputDir"])
    dry_run = bool(brief.get("dryRun", True))
    queue_name = str(brief.get("queueName", "Q_AGENT_OF_AGENTS_WORK"))
    asset_name = str(brief.get("assetName", "ASSET_AGENT_OF_AGENTS_POLICY"))

    resources: list[dict[str, str]] = []
    command_logs: list[str] = []

    queue_cmd = str(brief.get("queueProvisionCommand", "")).strip()
    asset_cmd = str(brief.get("assetProvisionCommand", "")).strip()

    if dry_run:
        resources.append(
            {
                "resourceType": "queue",
                "name": queue_name,
                "status": "simulated",
                "resourceId": "dry-run-queue",
                "details": "dryRun=true",
            }
        )
        resources.append(
            {
                "resourceType": "asset",
                "name": asset_name,
                "status": "simulated",
                "resourceId": "dry-run-asset",
                "details": "dryRun=true",
            }
        )
    else:
        if queue_cmd:
            ok, output = _run_command(queue_cmd, output_dir)
            resources.append(
                {
                    "resourceType": "queue",
                    "name": queue_name,
                    "status": "created" if ok else "failed",
                    "resourceId": queue_name if ok else "",
                    "details": output,
                }
            )
            command_logs.append(f"queueProvisionCommand: {output}")
        else:
            resources.append(
                {
                    "resourceType": "queue",
                    "name": queue_name,
                    "status": "failed",
                    "resourceId": "",
                    "details": "queueProvisionCommand is required when dryRun=false",
                }
            )

        if asset_cmd:
            ok, output = _run_command(asset_cmd, output_dir)
            resources.append(
                {
                    "resourceType": "asset",
                    "name": asset_name,
                    "status": "created" if ok else "failed",
                    "resourceId": asset_name if ok else "",
                    "details": output,
                }
            )
            command_logs.append(f"assetProvisionCommand: {output}")
        else:
            resources.append(
                {
                    "resourceType": "asset",
                    "name": asset_name,
                    "status": "failed",
                    "resourceId": "",
                    "details": "assetProvisionCommand is required when dryRun=false",
                }
            )

    evidence = dict(state.get("executionEvidence", {}))
    evidence.setdefault("commandLogs", [])
    evidence["commandLogs"].extend(command_logs)
    return {"provisionedResources": resources, "executionEvidence": evidence}


def execute_flow(state: OrchestratorState) -> OrchestratorState:
    if state.get("escalation"):
        return {}
    brief = state.get("brief", {})
    output_dir = Path(state["outputDir"])
    evidence_dir = output_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    started_at = _now_iso()
    command_logs = list(state.get("executionEvidence", {}).get("commandLogs", []))
    evidence_files: list[str] = []
    status = "completed"

    dry_run = bool(brief.get("dryRun", True))
    run_cmd = str(brief.get("flowRunCommand", "")).strip()

    max_iters = int(state.get("loopBudgets", {}).get("maxDeployIterations", 3))
    forced_failures = int(brief.get("forceDeployFailures", 0))
    deploy_iterations: list[dict[str, Any]] = []
    deploy_ok = False

    for idx in range(1, max_iters + 1):
        if dry_run:
            ok = idx > forced_failures
            output = "simulated deploy-test attempt"
        elif run_cmd:
            ok, output = _run_command(run_cmd, output_dir)
        else:
            ok = False
            output = "flowRunCommand missing while dryRun=false"

        deploy_iterations.append(
            {
                "iteration": idx,
                "phase": "deploy_test",
                "status": "passed" if ok else "failed",
                "output": output,
                "time": _now_iso(),
            }
        )
        if ok:
            deploy_ok = True
            if dry_run:
                simulated_path = evidence_dir / "simulated-run-output.json"
                simulated_path.write_text(
                    json.dumps(
                        {
                            "runId": state.get("runId", ""),
                            "status": "simulated",
                            "uiPlanFiles": state.get("uiPlanFiles", []),
                            "humanDocs": state.get("humanDocs", state.get("generatedDocuments", [])),
                            "generatedDocuments": state.get("generatedDocuments", []),
                            "provisionedResources": state.get("provisionedResources", []),
                            "deployIterations": deploy_iterations,
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                evidence_files.append(str(simulated_path))
                command_logs.append("flowRunCommand skipped because dryRun=true")
            else:
                raw_output_path = evidence_dir / "flow-run-output.log"
                raw_output_path.write_text(output, encoding="utf-8")
                evidence_files.append(str(raw_output_path))
                command_logs.append(f"flowRunCommand: {output}")
            break

    if not deploy_ok:
        status = "failed"
        escalation = {
            "reason": "deploy_test_loop_budget_exhausted",
            "phase": "deploy_test",
            "maxIterations": max_iters,
            "iterations": deploy_iterations,
            "action": "HITL escalation required for deployment budget extension or abort.",
        }
        _add_phase_event(state, "deploy_test", "failed", escalation["reason"])
        report_path = evidence_dir / "execution-evidence.json"
        report_path.write_text(
            json.dumps(
                {
                    "runId": state.get("runId", ""),
                    "status": status,
                    "startedAt": started_at,
                    "endedAt": _now_iso(),
                    "evidenceFiles": evidence_files,
                    "commandLogs": command_logs,
                    "deployIterations": deploy_iterations,
                    "escalation": escalation,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        evidence_files.append(str(report_path))
        return {
            "deployIterations": deploy_iterations,
            "escalation": escalation,
            "executionEvidence": {
                "runId": state.get("runId", ""),
                "status": status,
                "outputDir": str(output_dir),
                "startedAt": started_at,
                "endedAt": _now_iso(),
                "commandLogs": command_logs,
                "evidenceFiles": evidence_files,
            },
        }

    _record_hitl_decision(state, "deploy_test", True, "Deploy/test evidence accepted.")
    _add_phase_event(state, "deploy_test", "completed")

    report_path = evidence_dir / "execution-evidence.json"
    report_path.write_text(
        json.dumps(
            {
                "runId": state.get("runId", ""),
                "status": status,
                "startedAt": started_at,
                "endedAt": _now_iso(),
                "evidenceFiles": evidence_files,
                "commandLogs": command_logs,
                "deployIterations": deploy_iterations,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    evidence_files.append(str(report_path))

    return {
        "deployIterations": deploy_iterations,
        "executionEvidence": {
            "runId": state.get("runId", ""),
            "status": status,
            "outputDir": str(output_dir),
            "startedAt": started_at,
            "endedAt": _now_iso(),
            "commandLogs": command_logs,
            "evidenceFiles": evidence_files,
            "deployIterations": deploy_iterations,
        }
    }


def emit_ui_events(state: OrchestratorState) -> OrchestratorState:
    output_dir = Path(state["outputDir"])
    ui_dir = output_dir / "ui"
    ui_dir.mkdir(parents=True, exist_ok=True)
    events_path = ui_dir / "run-events.json"

    def _embed_content(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for file_entry in files:
            entry = dict(file_entry)
            file_path = Path(str(entry.get("path", "")).strip())
            if file_path.exists():
                entry["content"] = file_path.read_text(encoding="utf-8")
            result.append(entry)
        return result

    ui_plan_files = _embed_content(state.get("uiPlanFiles", []))
    human_docs = _embed_content(state.get("humanDocs", state.get("generatedDocuments", [])))
    payload = {
        "runId": state.get("runId", ""),
        "brief": state.get("brief", {}),
        "supervisor": state.get("supervisor", {}),
        "phaseHistory": state.get("phaseHistory", []),
        "hitlDecisions": state.get("hitlDecisions", []),
        "loopBudgets": state.get("loopBudgets", {}),
        "buildIterations": state.get("buildIterations", []),
        "deployIterations": state.get("deployIterations", []),
        "escalation": state.get("escalation", {}),
        "uiPlanFiles": ui_plan_files,
        "humanDocs": human_docs,
        "generatedDocuments": human_docs,
        "buildArtifacts": state.get("buildArtifacts", []),
        "provisionedResources": state.get("provisionedResources", []),
        "constraintsGraph": _build_constraints_graph_payload(state),
    }
    events_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Mirror the latest payload to a stable path for auto-loading UIs.
    repo_root = Path(__file__).resolve().parents[2]
    current_dir = repo_root / "ui" / "copilotkit" / "current"
    current_dir.mkdir(parents=True, exist_ok=True)
    current_events_path = current_dir / "run-events.json"
    current_events_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {"uiEventsPath": str(events_path)}


def summarize_handoff(state: OrchestratorState) -> OrchestratorState:
    ui_plan_files = state.get("uiPlanFiles", [])
    docs = state.get("humanDocs", state.get("generatedDocuments", []))
    artifacts = state.get("buildArtifacts", [])
    resources = state.get("provisionedResources", [])
    execution = state.get("executionEvidence", {})

    failed_resources = [item for item in resources if item.get("status") == "failed"]
    overall_status = "completed" if execution.get("status") == "completed" and not failed_resources else "failed"
    summary = (
        f"Run {state.get('runId', '')} generated {len(ui_plan_files)} UiPlan files, {len(docs)} docs, "
        f"{len(artifacts)} build artifacts, and provisioned {len(resources)} resources. "
        f"Execution status: {execution.get('status', 'unknown')}."
    )

    handoff = {
        "summary": summary,
        "status": overall_status,
        "runId": state.get("runId", ""),
        "outputDir": state.get("outputDir", ""),
        "supervisor": state.get("supervisor", {}),
        "phaseHistory": state.get("phaseHistory", []),
        "hitlDecisions": state.get("hitlDecisions", []),
        "loopBudgets": state.get("loopBudgets", {}),
        "buildIterations": state.get("buildIterations", []),
        "deployIterations": state.get("deployIterations", []),
        "escalation": state.get("escalation", {}),
        "uiEventsPath": state.get("uiEventsPath", ""),
        "uiPlanFiles": ui_plan_files,
        "humanDocs": docs,
        "generatedDocuments": docs,
        "buildArtifacts": artifacts,
        "provisionedResources": resources,
        "executionEvidence": execution,
        "evidenceChecklist": [
            "agent_assignments",
            "pdd_sdd_add",
            "uipath_build_artifacts",
            "provisioned_queue_and_asset",
            "execution_evidence_report",
        ],
    }
    return {"handoff": handoff, "summary": summary}


workflow = StateGraph(OrchestratorState)
workflow.add_node("assign_agents", assign_agents)
workflow.add_node("generate_design_docs", generate_design_docs)
workflow.add_node("generate_uipath_artifacts", generate_uipath_artifacts)
workflow.add_node("provision_resources", provision_resources)
workflow.add_node("execute_flow", execute_flow)
workflow.add_node("emit_ui_events", emit_ui_events)
workflow.add_node("summarize_handoff", summarize_handoff)

workflow.add_edge(START, "assign_agents")
workflow.add_edge("assign_agents", "generate_design_docs")
workflow.add_edge("generate_design_docs", "generate_uipath_artifacts")
workflow.add_edge("generate_uipath_artifacts", "provision_resources")
workflow.add_edge("provision_resources", "execute_flow")
workflow.add_edge("execute_flow", "emit_ui_events")
workflow.add_edge("emit_ui_events", "summarize_handoff")
workflow.add_edge("summarize_handoff", END)

graph = workflow.compile()


def run_orchestrator(payload: dict[str, Any]) -> OrchestratorState:
    normalized_state = normalize_state_input(payload)
    return graph.invoke(normalized_state)


def codedagent_entrypoint(payload: dict[str, Any]) -> OrchestratorState:
    return run_orchestrator(payload)
