from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.generation_contracts.constants import (
    APPROVAL_PACKAGE_SCHEMA_ID,
    APPROVAL_STATE_SCHEMA_ID,
    COMMAND_REGISTRY_SCHEMA_ID,
    FILE_PROPOSAL_SCHEMA_ID,
    GENERATION_GRAPH_SCHEMA_ID,
    GENERATOR_VERSION,
    SCHEMA_VERSION,
)

StageId = Literal["01-plan", "02-scaffold", "03-code", "04-tests", "05-validation"]
ApprovalStatus = Literal[
    "not_started",
    "ready_for_review",
    "changes_requested",
    "approved",
    "blocked",
    "applied",
    "superseded",
]
NodeRole = Literal[
    "process_step",
    "project_component",
    "generated_artifact",
    "test",
    "tool",
    "asset",
    "queue",
    "docs_context",
    "skill",
    "deployment_gate",
    "review_gate",
]
OutputType = Literal[
    "none",
    "document",
    "project_scaffold",
    "source_file",
    "test_file",
    "config",
    "orchestrator_resource",
    "validation_report",
    "approval_gate",
]
ProjectType = Literal[
    "rpa",
    "coded-automation",
    "coded-agent",
    "maestro-flow",
    "coded-app",
    "coded-action-app",
    "api-workflow",
    "solution",
    "library",
    "test",
    "docs",
    "platform-resource",
]
EdgeType = Literal[
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
]
ContextPolicy = Literal["strict", "advisory"]
ContextScope = Literal["graph", "node", "edge", "file", "stage"]
ContextSourceKind = Literal[
    "repo_doc",
    "library_book",
    "skill",
    "tool",
    "source_file",
    "user_note",
    "validation_output",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class GenerationContextAttachment(BaseModel):
    source_kind: ContextSourceKind
    source_id: str
    citation: str | None = None
    scope: ContextScope
    policy: ContextPolicy
    summary: str


class GenerationGraphNode(BaseModel):
    id: str
    title: str
    role: NodeRole
    output_type: OutputType
    project_types: list[ProjectType] = Field(default_factory=list)
    description: str
    x: int = 0
    y: int = 0
    source: str | None = None
    context_attachment_ids: list[str] = Field(default_factory=list)


class GenerationGraphEdge(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    from_: str = Field(alias="from")
    to: str
    edge_type: EdgeType
    label: str | None = None


class GenerationProfile(BaseModel):
    target_workspace: str | None = None
    package_name_prefix: str | None = None
    allowed_project_types: list[ProjectType] = Field(default_factory=list)


class GenerationGraph(BaseModel):
    schema_id: str = GENERATION_GRAPH_SCHEMA_ID
    schema_version: str = SCHEMA_VERSION
    graph_id: str
    bundle_root: str
    created_from: str
    nodes: list[GenerationGraphNode] = Field(default_factory=list)
    edges: list[GenerationGraphEdge] = Field(default_factory=list)
    context_attachments: list[GenerationContextAttachment] = Field(default_factory=list)
    approval_state_ref: str | None = None
    generation_profile: GenerationProfile = Field(default_factory=GenerationProfile)


class FindingRecord(BaseModel):
    severity: Literal["error", "warning", "note"]
    message: str
    scope: Literal["graph", "stage", "node", "edge", "file", "command"]
    target_id: str | None = None
    blocks_apply: bool = False


class FileProposal(BaseModel):
    schema_id: str = FILE_PROPOSAL_SCHEMA_ID
    schema_version: str = SCHEMA_VERSION
    proposal_id: str
    stage_id: StageId
    target_path: str
    file_kind: OutputType
    owning_node_ids: list[str] = Field(default_factory=list)
    project_type_ids: list[ProjectType] = Field(default_factory=list)
    proposed_content_hash: str
    base_hash: str | None = None
    diff_path: str
    proposal_path: str
    citations: list[str] = Field(default_factory=list)
    findings: list[FindingRecord] = Field(default_factory=list)
    apply_eligible: bool = False


class StageManifest(BaseModel):
    stage_id: StageId
    status: ApprovalStatus = "not_started"
    input_graph_hash: str
    input_context_hash: str
    generated_files: list[str] = Field(default_factory=list)
    required_approvals: list[str] = Field(default_factory=list)
    blocking_findings: list[FindingRecord] = Field(default_factory=list)
    validation_commands: list[str] = Field(default_factory=list)
    apply_eligible: bool = False


class ProposalState(BaseModel):
    proposal_id: str
    stage_id: StageId
    review_status: ApprovalStatus = "ready_for_review"
    apply_status: ApprovalStatus = "not_started"
    reviewer: str | None = None
    reviewer_notes: str | None = None
    source_graph_hash: str
    context_manifest_hash: str
    proposal_hash: str
    base_file_hash: str | None = None
    preview_id: str | None = None
    superseded_by: str | None = None
    blocked_reason: str | None = None
    updated_at: str = Field(default_factory=utc_now_iso)


class ApprovalState(BaseModel):
    schema_id: str = APPROVAL_STATE_SCHEMA_ID
    schema_version: str = SCHEMA_VERSION
    package_id: str
    current_stage: StageId = "01-plan"
    stage_statuses: dict[StageId, ApprovalStatus]
    proposals: dict[str, ProposalState] = Field(default_factory=dict)
    reviewer_notes: list[str] = Field(default_factory=list)
    applied_preview_ids: list[str] = Field(default_factory=list)
    superseded_preview_ids: list[str] = Field(default_factory=list)
    updated_at: str = Field(default_factory=utc_now_iso)


class ApprovalPackageManifest(BaseModel):
    schema_id: str = APPROVAL_PACKAGE_SCHEMA_ID
    schema_version: str = SCHEMA_VERSION
    package_id: str
    graph_id: str
    bundle_root: str
    generated_stages: list[StageId]
    generator_version: str = GENERATOR_VERSION
    created_at: str = Field(default_factory=utc_now_iso)
    graph_snapshot_path: str = "graph.snapshot.json"
    context_manifest_path: str = "context.manifest.json"
    approval_state_path: str = "approval-state.json"
    safety_policy: dict[str, str | bool]


class CommandRegistryEntry(BaseModel):
    command_id: str
    purpose: str
    owning_stage: StageId
    executable: str
    fixed_args: list[str] = Field(default_factory=list)
    working_directory_rule: Literal["bundle_root", "repo_root", "service_root"]
    allowed_path_inputs: list[str] = Field(default_factory=list)
    mutation_classification: Literal["read-only", "local-write", "external-mutation"]
    required_confirmation: bool
    credential_requirements: list[str] = Field(default_factory=list)
    output_summary_policy: str


class CommandRegistry(BaseModel):
    schema_id: str = COMMAND_REGISTRY_SCHEMA_ID
    schema_version: str = SCHEMA_VERSION
    commands: list[CommandRegistryEntry]
