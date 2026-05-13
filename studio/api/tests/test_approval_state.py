import pytest

from app.generation_contracts.approval_state import (
    apply_transition,
    create_initial_approval_state,
)


def test_ready_proposal_can_be_approved_with_metadata() -> None:
    state = create_initial_approval_state(
        package_id="pkg-1",
        stage_ids=["01-plan", "02-scaffold"],
        proposal_ids=["01-plan:plan-doc"],
        source_graph_hash="graph-hash",
        context_manifest_hash="context-hash",
        proposal_hashes={"01-plan:plan-doc": "proposal-hash"},
    )

    updated = apply_transition(
        state,
        target="proposal",
        target_id="01-plan:plan-doc",
        next_status="approved",
        reviewer="Daniela",
        note="Plan package reviewed",
    )

    proposal = updated.proposals["01-plan:plan-doc"]
    assert proposal.review_status == "approved"
    assert proposal.reviewer == "Daniela"
    assert proposal.reviewer_notes == "Plan package reviewed"
    assert proposal.source_graph_hash == "graph-hash"


def test_approved_proposal_can_be_marked_applied_with_matching_preview() -> None:
    state = create_initial_approval_state(
        package_id="pkg-1",
        stage_ids=["01-plan"],
        proposal_ids=["01-plan:plan-doc"],
        source_graph_hash="graph-hash",
        context_manifest_hash="context-hash",
        proposal_hashes={"01-plan:plan-doc": "proposal-hash"},
    )
    state = apply_transition(
        state,
        target="proposal",
        target_id="01-plan:plan-doc",
        next_status="approved",
        reviewer="Daniela",
    )

    updated = apply_transition(
        state,
        target="proposal",
        target_id="01-plan:plan-doc",
        next_status="applied",
        reviewer="Daniela",
        preview_id="preview-123",
    )

    assert updated.proposals["01-plan:plan-doc"].apply_status == "applied"
    assert updated.proposals["01-plan:plan-doc"].preview_id == "preview-123"
    assert "preview-123" in updated.applied_preview_ids


def test_invalid_transition_is_rejected() -> None:
    state = create_initial_approval_state(
        package_id="pkg-1",
        stage_ids=["01-plan"],
        proposal_ids=["01-plan:plan-doc"],
        source_graph_hash="graph-hash",
        context_manifest_hash="context-hash",
        proposal_hashes={"01-plan:plan-doc": "proposal-hash"},
    )

    with pytest.raises(ValueError, match="not allowed"):
        apply_transition(
            state,
            target="proposal",
            target_id="01-plan:plan-doc",
            next_status="applied",
            reviewer="Daniela",
            preview_id="preview-123",
        )


def test_stage_transition_with_unknown_target_id_is_rejected() -> None:
    state = create_initial_approval_state(
        package_id="pkg-1",
        stage_ids=["01-plan"],
        proposal_ids=["01-plan:plan-doc"],
        source_graph_hash="graph-hash",
        context_manifest_hash="context-hash",
        proposal_hashes={"01-plan:plan-doc": "proposal-hash"},
    )

    with pytest.raises(ValueError, match="unknown stage target_id"):
        apply_transition(
            state,
            target="stage",
            target_id="03-code",
            next_status="ready_for_review",
        )


def test_proposal_transition_with_unknown_target_id_is_rejected() -> None:
    state = create_initial_approval_state(
        package_id="pkg-1",
        stage_ids=["01-plan"],
        proposal_ids=["01-plan:plan-doc"],
        source_graph_hash="graph-hash",
        context_manifest_hash="context-hash",
        proposal_hashes={"01-plan:plan-doc": "proposal-hash"},
    )

    with pytest.raises(ValueError, match="unknown proposal target_id"):
        apply_transition(
            state,
            target="proposal",
            target_id="01-plan:missing",
            next_status="approved",
            reviewer="Daniela",
        )


def test_repeat_apply_is_idempotent_and_does_not_duplicate_preview_id() -> None:
    state = create_initial_approval_state(
        package_id="pkg-1",
        stage_ids=["01-plan"],
        proposal_ids=["01-plan:plan-doc"],
        source_graph_hash="graph-hash",
        context_manifest_hash="context-hash",
        proposal_hashes={"01-plan:plan-doc": "proposal-hash"},
    )
    approved = apply_transition(
        state,
        target="proposal",
        target_id="01-plan:plan-doc",
        next_status="approved",
        reviewer="Daniela",
    )
    first_apply = apply_transition(
        approved,
        target="proposal",
        target_id="01-plan:plan-doc",
        next_status="applied",
        reviewer="Daniela",
        preview_id="preview-123",
    )

    second_apply = apply_transition(
        first_apply,
        target="proposal",
        target_id="01-plan:plan-doc",
        next_status="applied",
        reviewer="Daniela",
        preview_id="preview-123",
    )

    proposal = second_apply.proposals["01-plan:plan-doc"]
    assert proposal.review_status == "approved"
    assert proposal.apply_status == "applied"
    assert proposal.preview_id == "preview-123"
    assert second_apply.applied_preview_ids == ["preview-123"]


def test_repeat_apply_with_different_preview_id_is_rejected() -> None:
    state = create_initial_approval_state(
        package_id="pkg-1",
        stage_ids=["01-plan"],
        proposal_ids=["01-plan:plan-doc"],
        source_graph_hash="graph-hash",
        context_manifest_hash="context-hash",
        proposal_hashes={"01-plan:plan-doc": "proposal-hash"},
    )
    approved = apply_transition(
        state,
        target="proposal",
        target_id="01-plan:plan-doc",
        next_status="approved",
        reviewer="Daniela",
    )
    applied = apply_transition(
        approved,
        target="proposal",
        target_id="01-plan:plan-doc",
        next_status="applied",
        reviewer="Daniela",
        preview_id="preview-123",
    )

    with pytest.raises(ValueError, match="already applied with preview_id"):
        apply_transition(
            applied,
            target="proposal",
            target_id="01-plan:plan-doc",
            next_status="applied",
            reviewer="Daniela",
            preview_id="preview-456",
        )
