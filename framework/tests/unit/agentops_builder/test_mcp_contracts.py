from __future__ import annotations

from framework.agentops_builder.mcp.registry import (
    PHASE_TOOL_PLAN_MAPPING,
    REGISTRY,
    contracts_by_category,
)


def test_registry_contract_fields_are_populated() -> None:
    assert REGISTRY
    for contract in REGISTRY.values():
        assert contract.tool_id
        assert contract.label
        assert contract.category.value
        assert contract.risk_level.value
        assert contract.approval_requirement.value
        assert contract.evidence_output
        assert contract.direct_call_policy.value


def test_required_task_5b_wrappers_are_in_registry() -> None:
    required = {
        "uipath_plan_review",
        "uipath_skill_match",
        "uipath_skill_get",
        "uipath_library_lookup",
        "uipath_workflow_read_file",
        "uipath_workflow_build_and_verify",
        "uipath_workflow_session_status",
        "orchestrator.telemetry_readiness",
    }
    assert required.issubset(set(REGISTRY))


def test_phase_mapping_references_known_tool_ids() -> None:
    known_ids = set(REGISTRY)
    assert PHASE_TOOL_PLAN_MAPPING
    for phase, tool_ids in PHASE_TOOL_PLAN_MAPPING.items():
        assert phase
        assert tool_ids
        for tool_id in tool_ids:
            assert tool_id in known_ids


def test_grouping_returns_expected_categories() -> None:
    grouped = contracts_by_category()
    assert "plan" in grouped
    assert "workflow" in grouped
    assert "orchestrator_action" in grouped
    assert all(grouped.values())

