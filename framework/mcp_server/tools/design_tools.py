"""MCP surface for design proposals and approvals.

A project's first writes are gated on an approved design. The agent calls
``uipath_design_propose`` with a design summary derived from the user's
request (ideally after asking the user to confirm trade-offs via Cursor's
AskQuestion); the MCP returns a ``design_id`` and the project remains
write-locked until ``uipath_design_approve`` lands.
"""
from __future__ import annotations

import json
from typing import Any

from mcp.types import Tool, ToolAnnotations

from uipath_claude.tools import design_store


def _ro(title: str) -> ToolAnnotations:
    return ToolAnnotations(title=title, readOnlyHint=True)


def _staging(title: str) -> ToolAnnotations:
    return ToolAnnotations(
        title=title,
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
    )


def _decisive(title: str) -> ToolAnnotations:
    return ToolAnnotations(
        title=title,
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=True,
    )


def get_design_tools() -> list[Tool]:
    return [
        Tool(
            name="uipath_design_propose",
            description=(
                "Submit a design proposal for a UiPath project to the approval "
                "queue. The proposal must include a short user-facing summary "
                "(the architectural choices the user needs to approve), a "
                "longer body (workflow shape, packages, error handling, "
                "Orchestrator interactions), and citations to the library / "
                "official docs the design rests on. Returns a design_id and "
                "leaves the project WRITE-LOCKED: uipath_workflow_write_file "
                "and uipath_workflow_install_package will return [BLOCKED] "
                "until uipath_design_approve is invoked on this design_id. "
                "BEFORE calling this tool, ask the user (e.g. via Cursor's "
                "AskQuestion) to confirm the design choices, especially when "
                "trade-offs exist (REFramework vs simple sequence, library vs "
                "process, sync vs queue-driven). Only one pending proposal "
                "per project is kept; resubmitting replaces the prior pending."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": "Project root the design applies to.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Short title shown in approval prompts.",
                    },
                    "summary": {
                        "type": "string",
                        "description": (
                            "User-facing summary of the design choices that "
                            "need approval (1-3 short paragraphs)."
                        ),
                    },
                    "body": {
                        "type": "string",
                        "description": (
                            "Full design body: workflow shape, packages, "
                            "error handling, Orchestrator interactions."
                        ),
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Why this design over alternatives (optional).",
                        "default": "",
                    },
                    "citations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Library section ids or doc URLs the design "
                            "draws from."
                        ),
                        "default": [],
                    },
                    "resolutions": {
                        "type": "object",
                        "description": (
                            "Structured echo of every project-shape decision "
                            "the planner / BA resolved before proposing this "
                            "design. The approver sees these verbatim on the "
                            "approval card so they can catch wrong defaults "
                            "BEFORE any file is written. Recommended keys: "
                            "project_type, target_framework, expression_language, "
                            "attended_unattended, external_systems (list), "
                            "orchestrator_folder, deploy (bool), "
                            "destructive_actions (list), "
                            "open_questions_residue (list of items the agent "
                            "consciously defaulted and the user may override "
                            "at approval time). Unknown keys are preserved "
                            "under _extra. Omitting this field is deprecated "
                            "but still accepted for backwards compatibility; "
                            "a warning is returned in that case."
                        ),
                        "default": {},
                    },
                },
                "required": ["project_dir", "title", "summary", "body"],
            },
            annotations=_staging("Propose UiPath project design"),
        ),
        Tool(
            name="uipath_design_approve",
            description=(
                "Approve a pending design by id. After approval the project's "
                "design gate opens and uipath_workflow_write_file / "
                "_install_package can run for that project. Approval persists "
                "across MCP restarts (stored under "
                "~/.uipath-builder-agent/design_proposals.json or "
                "UIPATH_DESIGN_STORE_PATH)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "design_id": {
                        "type": "string",
                        "description": "Design id from uipath_design_propose.",
                    },
                    "note": {
                        "type": "string",
                        "description": "Optional note recorded with the approval.",
                        "default": "",
                    },
                    "actor": {
                        "type": "string",
                        "description": "Who approved (defaults to 'human').",
                        "default": "human",
                    },
                },
                "required": ["design_id"],
            },
            annotations=_decisive("Approve project design"),
        ),
        Tool(
            name="uipath_design_reject",
            description=(
                "Reject a pending design by id. The project stays write-locked "
                "until a new design is proposed and approved."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "design_id": {
                        "type": "string",
                        "description": "Design id from uipath_design_propose.",
                    },
                    "note": {
                        "type": "string",
                        "description": "Optional reason for the rejection.",
                        "default": "",
                    },
                    "actor": {
                        "type": "string",
                        "description": "Who rejected (defaults to 'human').",
                        "default": "human",
                    },
                },
                "required": ["design_id"],
            },
            annotations=_decisive("Reject project design"),
        ),
        Tool(
            name="uipath_design_list",
            description=(
                "List design proposals, optionally filtered by project_dir "
                "and / or status (pending|approved|rejected). Read-only."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": "Optional project filter.",
                    },
                    "status_filter": {
                        "type": "string",
                        "enum": ["pending", "approved", "rejected"],
                        "description": "Optional status filter.",
                    },
                },
            },
            annotations=_ro("List design proposals"),
        ),
        Tool(
            name="uipath_design_status",
            description=(
                "Read-only status of the design gate for a project. Reports "
                "whether approval is enabled, whether an approved design "
                "exists, and the latest pending proposal (if any)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": "Project root to inspect.",
                    },
                },
                "required": ["project_dir"],
            },
            annotations=_ro("Design gate status"),
        ),
    ]


def _proposal_to_dict(p: design_store.DesignProposal) -> dict[str, Any]:
    return p.to_dict()


async def call_design_tool(name: str, arguments: dict[str, Any]) -> Any:
    if name == "uipath_design_propose":
        proposal, warnings = design_store.propose(
            project_dir=arguments["project_dir"],
            title=arguments["title"],
            summary=arguments["summary"],
            body=arguments["body"],
            rationale=arguments.get("rationale", ""),
            citations=list(arguments.get("citations") or []),
            resolutions=arguments.get("resolutions") or {},
        )
        header = (
            f"[STAGED] design_id={proposal.design_id} "
            f"project={proposal.project_dir}"
        )
        warning_block = (
            ("\n\n[WARN] " + "\n[WARN] ".join(warnings)) if warnings else ""
        )
        return (
            f"{header}{warning_block}\n\n"
            f"{json.dumps(_proposal_to_dict(proposal), indent=2)}\n\n"
            f"Project stays write-locked. Run uipath_design_approve "
            f"{{ design_id: '{proposal.design_id}' }} after the user confirms."
        )

    if name == "uipath_design_approve":
        try:
            proposal = design_store.approve(
                arguments["design_id"],
                note=arguments.get("note", ""),
                actor=arguments.get("actor", "human"),
            )
        except KeyError as exc:
            return f"[ERR] {exc}"
        return (
            f"[OK] approved design_id={proposal.design_id} for "
            f"project={proposal.project_dir}\n"
            f"{json.dumps(_proposal_to_dict(proposal), indent=2)}"
        )

    if name == "uipath_design_reject":
        try:
            proposal = design_store.reject(
                arguments["design_id"],
                note=arguments.get("note", ""),
                actor=arguments.get("actor", "human"),
            )
        except KeyError as exc:
            return f"[ERR] {exc}"
        return (
            f"[OK] rejected design_id={proposal.design_id} for "
            f"project={proposal.project_dir}\n"
            f"{json.dumps(_proposal_to_dict(proposal), indent=2)}"
        )

    if name == "uipath_design_list":
        status_filter = arguments.get("status_filter")
        proposals = design_store.list_proposals(
            project_dir=arguments.get("project_dir"),
            status_filter=status_filter,  # type: ignore[arg-type]
        )
        if not proposals:
            return "No design proposals match the filter."
        return json.dumps([_proposal_to_dict(p) for p in proposals], indent=2)

    if name == "uipath_design_status":
        project_dir = arguments["project_dir"]
        approved = design_store.has_approved(project_dir)
        pending = design_store.latest_pending(project_dir)
        latest_approved = next(
            (
                p
                for p in design_store.list_proposals(
                    project_dir=project_dir, status_filter="approved"
                )
            ),
            None,
        )
        snapshot = {
            "project_dir": design_store._normalize_project_dir(project_dir),
            "approval_enabled": design_store._approval_enabled(),
            "has_approved_design": approved,
            "latest_pending": _proposal_to_dict(pending) if pending else None,
            "latest_approved_resolutions": (
                latest_approved.resolutions if latest_approved else None
            ),
            "latest_pending_resolutions": (
                pending.resolutions if pending else None
            ),
        }
        return json.dumps(snapshot, indent=2)

    raise ValueError(f"Unknown design tool: {name}")
