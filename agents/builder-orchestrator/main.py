from __future__ import annotations

from typing import Any
from typing import TypedDict

from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph


class OrchestratorState(TypedDict, total=False):
    intake: dict[str, Any]
    classification: str
    agentAssignments: list[dict[str, str]]
    planSummary: str
    verificationStatus: str
    deploymentReadiness: str
    handoff: dict[str, Any]


def _to_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [value]
    return []


def normalize_state_input(payload: dict[str, Any]) -> OrchestratorState:
    if "intake" in payload and isinstance(payload.get("intake"), dict):
        state: OrchestratorState = dict(payload)
    else:
        # Accept raw intake input and normalize into graph state.
        state = {"intake": dict(payload)}

    intake = state.get("intake", {})
    if not isinstance(intake, dict):
        intake = {}

    state["intake"] = {
        "businessGoal": intake.get("businessGoal", ""),
        "industry": intake.get("industry", ""),
        "systems": _to_string_list(intake.get("systems", [])),
        "constraints": _to_string_list(intake.get("constraints", [])),
        "successCriteria": _to_string_list(intake.get("successCriteria", [])),
    }
    return state


def classify_request(state: OrchestratorState) -> OrchestratorState:
    intake = state.get("intake", {})
    systems = intake.get("systems", [])
    success_criteria = intake.get("successCriteria", [])

    is_enterprise_shape = (
        isinstance(intake.get("businessGoal"), str)
        and isinstance(systems, list)
        and isinstance(success_criteria, list)
    )

    classification = "enterprise_agent_builder" if is_enterprise_shape else "generic_request"
    return {"classification": classification}


def assign_agents(state: OrchestratorState) -> OrchestratorState:
    assignments = [
        {
            "phase": "discovery",
            "agent": "discovery-agent",
            "responsibility": "Normalize intake and produce AS-IS facts.",
        },
        {
            "phase": "architecture",
            "agent": "solution-architect-agent",
            "responsibility": "Draft TO-BE architecture and workflow catalog.",
        },
        {
            "phase": "generation",
            "agent": "workflow-generator-agent",
            "responsibility": "Prepare implementation artifacts for build.",
        },
        {
            "phase": "verification",
            "agent": "verifier-agent",
            "responsibility": "Evaluate gate outputs and mark status.",
        },
        {
            "phase": "deployment evidence",
            "agent": "deployment-evidence-agent",
            "responsibility": "Assemble versions, runs, and blockers handoff.",
        },
    ]
    return {"agentAssignments": assignments}


def draft_solution_plan(state: OrchestratorState) -> OrchestratorState:
    intake = state.get("intake", {})
    goal = intake.get("businessGoal")
    if not isinstance(goal, str) or not goal.strip():
        goal = "Build an enterprise automation solution."

    systems = _to_string_list(intake.get("systems", []))
    constraints = _to_string_list(intake.get("constraints", []))
    success_criteria = _to_string_list(intake.get("successCriteria", []))

    summary = (
        f"{goal} Coordinate specialist agents across discovery, architecture, generation, "
        f"verification, and deployment evidence. Target systems: {', '.join(systems)}. "
        f"Constraints: {', '.join(constraints)}. Success criteria: {', '.join(success_criteria)}."
    )
    return {"planSummary": summary}


def request_approval(state: OrchestratorState) -> OrchestratorState:
    if state.get("verificationStatus") == "passed":
        # Preserve resumed/approved state.
        return {"verificationStatus": "passed"}
    return {"verificationStatus": "pending_approval"}


def prepare_build(state: OrchestratorState) -> OrchestratorState:
    verification_status = state.get("verificationStatus", "unknown")
    if verification_status == "passed":
        readiness = "ready"
    else:
        readiness = "blocked_pending_verification"
    return {"deploymentReadiness": readiness}


def summarize_handoff(state: OrchestratorState) -> OrchestratorState:
    handoff = {
        "summary": state.get("planSummary", ""),
        "classification": state.get("classification", "unknown"),
        "deploymentReadiness": state.get("deploymentReadiness", "unknown"),
        "evidenceChecklist": [
            "intake_snapshot",
            "agent_assignments",
            "verification_results",
            "deployment_readiness_report",
        ],
    }
    return {"handoff": handoff}


workflow = StateGraph(OrchestratorState)
workflow.add_node("classify_request", classify_request)
workflow.add_node("assign_agents", assign_agents)
workflow.add_node("draft_solution_plan", draft_solution_plan)
workflow.add_node("request_approval", request_approval)
workflow.add_node("prepare_build", prepare_build)
workflow.add_node("summarize_handoff", summarize_handoff)

workflow.add_edge(START, "classify_request")
workflow.add_edge("classify_request", "assign_agents")
workflow.add_edge("assign_agents", "draft_solution_plan")
workflow.add_edge("draft_solution_plan", "request_approval")
workflow.add_edge("request_approval", "prepare_build")
workflow.add_edge("prepare_build", "summarize_handoff")
workflow.add_edge("summarize_handoff", END)

graph = workflow.compile()


def run_orchestrator(payload: dict[str, Any]) -> OrchestratorState:
    normalized_state = normalize_state_input(payload)
    return graph.invoke(normalized_state)


def codedagent_entrypoint(payload: dict[str, Any]) -> OrchestratorState:
    return run_orchestrator(payload)
