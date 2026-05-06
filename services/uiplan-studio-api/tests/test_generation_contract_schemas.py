import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from app.generation_contracts.constants import (
    APPROVAL_STATUS_VALUES,
    COMMAND_REGISTRY_SCHEMA_ID,
    GENERATION_GRAPH_SCHEMA_ID,
    NODE_ROLES,
    OUTPUT_TYPES,
    PROJECT_TYPES,
    STAGE_IDS,
)
from app.generation_contracts.schema_service import (
    copy_contract_schemas,
    load_contract_schemas,
)


def _collect_schema_errors(schema: dict, payload: dict) -> list:
    validator = Draft202012Validator(schema)
    return list(validator.iter_errors(payload))


def test_contract_schema_files_have_stable_ids_and_versions() -> None:
    schemas = load_contract_schemas()

    assert set(schemas) == {
        "generation-graph.v1.schema.json",
        "approval-package.v1.schema.json",
        "approval-state.v1.schema.json",
        "file-proposal.v1.schema.json",
        "command-registry.v1.schema.json",
    }
    assert schemas["generation-graph.v1.schema.json"]["$id"] == GENERATION_GRAPH_SCHEMA_ID
    assert schemas["command-registry.v1.schema.json"]["$id"] == COMMAND_REGISTRY_SCHEMA_ID
    assert schemas["generation-graph.v1.schema.json"]["x-uiplan-schema-version"] == "v1"


def test_generation_graph_schema_covers_v1_enums() -> None:
    graph_schema = load_contract_schemas()["generation-graph.v1.schema.json"]
    node_props = graph_schema["properties"]["nodes"]["items"]["properties"]
    edge_props = graph_schema["properties"]["edges"]["items"]["properties"]

    assert set(node_props["role"]["enum"]) == set(NODE_ROLES)
    assert set(node_props["output_type"]["enum"]) == set(OUTPUT_TYPES)
    assert set(node_props["project_types"]["items"]["enum"]) == set(PROJECT_TYPES)
    assert set(edge_props["edge_type"]["enum"]) == {
        "drives",
        "generates",
        "depends_on",
        "uses_context",
        "uses_skill",
        "validates",
        "blocks",
        "deploys",
        "observes",
        "documents",
    }


def test_approval_state_schema_covers_status_and_stage_values() -> None:
    state_schema = load_contract_schemas()["approval-state.v1.schema.json"]
    status_enum = state_schema["$defs"]["approvalStatus"]["enum"]
    stage_enum = state_schema["$defs"]["stageId"]["enum"]

    assert set(status_enum) == set(APPROVAL_STATUS_VALUES)
    assert stage_enum == STAGE_IDS


def test_approval_state_schema_restricts_stage_status_keys() -> None:
    state_schema = load_contract_schemas()["approval-state.v1.schema.json"]
    stage_statuses = state_schema["properties"]["stage_statuses"]

    assert stage_statuses["propertyNames"]["$ref"] == "#/$defs/stageId"
    assert stage_statuses["additionalProperties"]["$ref"] == "#/$defs/approvalStatus"
    assert "06-release" not in state_schema["$defs"]["stageId"]["enum"]


def test_approval_state_runtime_rejects_invalid_stage_status_key() -> None:
    state_schema = load_contract_schemas()["approval-state.v1.schema.json"]
    payload = {
        "schema_id": "approval-state.v1",
        "schema_version": "v1",
        "package_id": "pkg-1",
        "current_stage": "01-plan",
        "stage_statuses": {"06-release": "approved"},
        "proposals": {},
        "reviewer_notes": [],
        "applied_preview_ids": [],
        "superseded_preview_ids": [],
        "updated_at": "2026-05-05T00:00:00Z",
    }

    errors = _collect_schema_errors(state_schema, payload)

    assert any(error.validator == "enum" and list(error.path) == ["stage_statuses"] for error in errors)


def test_approval_state_schema_restricts_proposal_payload_shape() -> None:
    state_schema = load_contract_schemas()["approval-state.v1.schema.json"]
    proposal_state = state_schema["$defs"]["proposalState"]

    assert state_schema["properties"]["proposals"]["additionalProperties"]["$ref"] == (
        "#/$defs/proposalState"
    )
    assert set(proposal_state["required"]) == {
        "proposal_id",
        "stage_id",
        "review_status",
        "apply_status",
        "source_graph_hash",
        "context_manifest_hash",
        "proposal_hash",
        "updated_at",
    }
    assert proposal_state["additionalProperties"] is False


def test_approval_state_runtime_rejects_malformed_proposal_entry() -> None:
    state_schema = load_contract_schemas()["approval-state.v1.schema.json"]
    payload = {
        "schema_id": "approval-state.v1",
        "schema_version": "v1",
        "package_id": "pkg-1",
        "current_stage": "01-plan",
        "stage_statuses": {"01-plan": "approved"},
        "proposals": {
            "proposal-1": {
                "proposal_id": "proposal-1",
                "stage_id": "01-plan",
                "review_status": "approved",
                "source_graph_hash": "graph-hash",
                "context_manifest_hash": "ctx-hash",
                "proposal_hash": "proposal-hash",
                "updated_at": "2026-05-05T00:00:00Z",
            }
        },
        "reviewer_notes": [],
        "applied_preview_ids": [],
        "superseded_preview_ids": [],
        "updated_at": "2026-05-05T00:00:00Z",
    }

    errors = _collect_schema_errors(state_schema, payload)

    assert any(
        error.validator == "required"
        and list(error.path) == ["proposals", "proposal-1"]
        and "apply_status" in error.message
        for error in errors
    )


def test_file_proposal_schema_restricts_findings_payload_shape() -> None:
    proposal_schema = load_contract_schemas()["file-proposal.v1.schema.json"]
    finding_record = proposal_schema["$defs"]["findingRecord"]

    assert proposal_schema["properties"]["findings"]["items"]["$ref"] == "#/$defs/findingRecord"
    assert set(finding_record["required"]) == {
        "severity",
        "message",
        "scope",
        "target_id",
        "blocks_apply",
    }
    assert finding_record["properties"]["severity"]["enum"] == ["error", "warning", "note"]
    assert finding_record["additionalProperties"] is False


def test_file_proposal_runtime_rejects_malformed_finding_item() -> None:
    proposal_schema = load_contract_schemas()["file-proposal.v1.schema.json"]
    payload = {
        "schema_id": "file-proposal.v1",
        "schema_version": "v1",
        "proposal_id": "proposal-1",
        "stage_id": "01-plan",
        "target_path": "docs/plan.md",
        "file_kind": "document",
        "owning_node_ids": ["node-1"],
        "project_type_ids": ["docs"],
        "proposed_content_hash": "hash-1",
        "diff_path": "artifacts/diff.patch",
        "proposal_path": "artifacts/proposal.md",
        "citations": [],
        "findings": [
            {
                "severity": "error",
                "message": "Missing target",
                "scope": "file",
                "target_id": "docs/plan.md",
                "blocks_apply": "yes",
            }
        ],
        "apply_eligible": False,
    }

    errors = _collect_schema_errors(proposal_schema, payload)

    assert any(
        error.validator == "type"
        and list(error.path) == ["findings", 0, "blocks_apply"]
        for error in errors
    )


def test_copy_contract_schemas_writes_bundle_schema_directory(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    written = copy_contract_schemas(bundle_root)

    schema_dir = bundle_root / ".uiplan" / "generation" / "schemas"
    assert sorted(path.name for path in written) == sorted(load_contract_schemas())
    assert json.loads((schema_dir / "generation-graph.v1.schema.json").read_text())[
        "$id"
    ] == GENERATION_GRAPH_SCHEMA_ID


def test_copy_contract_schemas_requires_existing_directory(tmp_path: Path) -> None:
    missing_dir = tmp_path / "missing"
    with pytest.raises(ValueError, match="existing directory"):
        copy_contract_schemas(missing_dir)


def test_copy_contract_schemas_rejects_file_path(tmp_path: Path) -> None:
    file_path = tmp_path / "not-a-dir.txt"
    file_path.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="existing directory"):
        copy_contract_schemas(file_path)
