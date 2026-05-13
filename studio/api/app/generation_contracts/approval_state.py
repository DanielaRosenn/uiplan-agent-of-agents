from __future__ import annotations

from app.generation_contracts.models import (
    ApprovalState,
    ApprovalStatus,
    ProposalState,
    utc_now_iso,
)

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "not_started": {"ready_for_review", "blocked"},
    "ready_for_review": {"changes_requested", "approved", "blocked", "superseded"},
    "changes_requested": {"ready_for_review", "blocked", "superseded"},
    "approved": {"applied", "blocked", "superseded"},
    "blocked": {"ready_for_review", "superseded"},
    "applied": set(),
    "superseded": set(),
}


def create_initial_approval_state(
    *,
    package_id: str,
    stage_ids: list[str],
    proposal_ids: list[str],
    source_graph_hash: str,
    context_manifest_hash: str,
    proposal_hashes: dict[str, str],
    ready_stage_ids: list[str] | None = None,
) -> ApprovalState:
    stage_statuses = {stage_id: "not_started" for stage_id in stage_ids}
    for stage_id in ready_stage_ids or []:
        if stage_id in stage_statuses:
            stage_statuses[stage_id] = "ready_for_review"
    proposals = {
        proposal_id: ProposalState(
            proposal_id=proposal_id,
            stage_id=proposal_id.split(":", 1)[0],
            review_status="ready_for_review",
            apply_status="not_started",
            source_graph_hash=source_graph_hash,
            context_manifest_hash=context_manifest_hash,
            proposal_hash=proposal_hashes[proposal_id],
        )
        for proposal_id in proposal_ids
    }
    return ApprovalState(
        package_id=package_id,
        current_stage="01-plan",
        stage_statuses=stage_statuses,
        proposals=proposals,
    )


def apply_transition(
    state: ApprovalState,
    *,
    target: str,
    target_id: str,
    next_status: ApprovalStatus,
    reviewer: str | None = None,
    note: str | None = None,
    preview_id: str | None = None,
    blocked_reason: str | None = None,
    superseded_by: str | None = None,
) -> ApprovalState:
    updated = state.model_copy(deep=True)
    if target == "stage":
        if target_id not in updated.stage_statuses:
            raise ValueError(f"unknown stage target_id: {target_id}")
        current = updated.stage_statuses[target_id]
        _assert_allowed(current, next_status)
        updated.stage_statuses[target_id] = next_status
        updated.current_stage = target_id
    elif target == "proposal":
        if target_id not in updated.proposals:
            raise ValueError(f"unknown proposal target_id: {target_id}")
        proposal = updated.proposals[target_id]
        if proposal.apply_status == "applied" and next_status != "applied":
            raise ValueError("proposal is already applied; review transitions are closed")
        current = proposal.review_status
        _assert_allowed(current, next_status)
        if next_status == "applied":
            if proposal.review_status != "approved":
                raise ValueError("applied transition is not allowed before approval")
            if not preview_id:
                raise ValueError("preview_id is required when applying a proposal")
            if proposal.apply_status == "applied":
                if proposal.preview_id != preview_id:
                    raise ValueError(
                        "proposal already applied with preview_id "
                        f"{proposal.preview_id}, got {preview_id}"
                    )
                if preview_id not in updated.applied_preview_ids:
                    updated.applied_preview_ids.append(preview_id)
                return updated
            proposal.apply_status = "applied"
            proposal.preview_id = preview_id
            if preview_id not in updated.applied_preview_ids:
                updated.applied_preview_ids.append(preview_id)
        else:
            proposal.review_status = next_status
        proposal.reviewer = reviewer
        proposal.reviewer_notes = note
        proposal.blocked_reason = blocked_reason
        proposal.superseded_by = superseded_by
        proposal.updated_at = utc_now_iso()
    else:
        raise ValueError(f"unsupported transition target: {target}")
    updated.updated_at = utc_now_iso()
    return updated


def _assert_allowed(current: str, next_status: str) -> None:
    if next_status not in ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"transition from {current} to {next_status} is not allowed")
