# UiPlan Studio Generation Graph Phase 0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the contract-first foundation for UiPlan Studio generation packages, then ship Plan and Scaffold approval packages with durable approval metadata and preview/apply-only safety.

**Architecture:** Add a backend contract layer for typed generation graph schemas, approval state, package storage, path allowlisting, and command registry before any stage generator writes package data. Keep generation output inside `.uiplan/generation/packages/<package-id>/` and route all target file changes through hash-guarded preview/apply. Extend the existing React Studio UI to load packages, review stage/file metadata, approve proposals, and keep Code, Tests, Validation, publish, and deploy actions disabled.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, pytest, React 18, TypeScript, Vite, Vitest, Testing Library, CopilotKit.

---

## File Structure

- Create: `services/uiplan-studio-api/app/generation_contracts/__init__.py`  
  Package marker for Phase 0 contract modules.
- Create: `services/uiplan-studio-api/app/generation_contracts/constants.py`  
  Central schema ids, version strings, allowed statuses, stage ids, node roles, output types, project types, edge types, and blocked path segments.
- Create: `services/uiplan-studio-api/app/generation_contracts/models.py`  
  Pydantic request/response and manifest models shared by graph, package, state, proposal, and registry services.
- Create: `services/uiplan-studio-api/app/generation_contracts/schemas/generation-graph.v1.schema.json`  
  Stable local JSON Schema for `generation_graph.v1`.
- Create: `services/uiplan-studio-api/app/generation_contracts/schemas/approval-package.v1.schema.json`  
  Stable local JSON Schema for approval package manifests.
- Create: `services/uiplan-studio-api/app/generation_contracts/schemas/approval-state.v1.schema.json`  
  Stable local JSON Schema for durable stage and proposal approval metadata.
- Create: `services/uiplan-studio-api/app/generation_contracts/schemas/file-proposal.v1.schema.json`  
  Stable local JSON Schema for file proposals.
- Create: `services/uiplan-studio-api/app/generation_contracts/schemas/command-registry.v1.schema.json`  
  Stable local JSON Schema for allowed command records.
- Create: `services/uiplan-studio-api/app/generation_contracts/schema_service.py`  
  Loads schema files, exposes schema metadata, and copies schemas into each bundle generation directory.
- Create: `services/uiplan-studio-api/app/generation_contracts/approval_state.py`  
  Enforces allowed state transitions and stamps durable review/apply metadata.
- Create: `services/uiplan-studio-api/app/generation_contracts/path_allowlist.py`  
  Validates proposal target paths against bundle/repository roots and secret/dependency exclusions.
- Create: `services/uiplan-studio-api/app/generation_contracts/command_registry.py`  
  Defines Plan and Scaffold readiness command records and blocks external mutation commands from first-scope execution.
- Create: `services/uiplan-studio-api/app/generation_contracts/storage.py`  
  Creates `.uiplan/generation/` layout, writes manifests atomically, reads existing packages, and updates `approval-state.json`.
- Create: `services/uiplan-studio-api/app/generation_contracts/package_generation.py`  
  Builds deterministic Plan and Scaffold approval packages from a graph snapshot and context manifest.
- Create: `services/uiplan-studio-api/tests/test_generation_contract_schemas.py`  
  Unit tests for schema ids, enum coverage, and schema copy behavior.
- Create: `services/uiplan-studio-api/tests/test_approval_state.py`  
  Unit tests for allowed transitions, blocked/superseded metadata, and invalid transition errors.
- Create: `services/uiplan-studio-api/tests/test_path_allowlist_command_registry.py`  
  Unit tests for unsafe path rejection and command registry safety classifications.
- Create: `services/uiplan-studio-api/tests/test_approval_package_storage.py`  
  Service tests for bundle storage layout, package listing, state persistence, and no target-file writes.
- Create: `services/uiplan-studio-api/tests/test_stage_package_generation.py`  
  Service tests for Plan and Scaffold package generation and deferred Code/Tests/Validation behavior.
- Modify: `services/uiplan-studio-api/app/schemas.py`  
  Export API models for typed graphs, package summaries, proposal details, approval actions, and apply requests.
- Modify: `services/uiplan-studio-api/app/diagram_service.py`  
  Add migration from existing `diagram.json` nodes into `generation_graph.v1` while preserving legacy load/save.
- Modify: `services/uiplan-studio-api/app/main.py`  
  Add contract, graph, package, approval, and proposal preview/apply endpoints.
- Modify: `services/uiplan-studio-api/app/copilot_runtime.py`  
  Add preview-only package drafting actions for Plan and Scaffold.
- Modify: `services/uiplan-studio-api/tests/test_main.py`  
  Endpoint tests for health route exposure, package generation, approval state updates, and guarded apply behavior.
- Create: `apps/uiplan-studio/src/generationTypes.ts`  
  Frontend TypeScript types mirroring package summaries, stage manifests, file proposals, findings, and approval state.
- Modify: `apps/uiplan-studio/src/types.ts`  
  Extend existing diagram node and edge types with v1 role/output/project/context metadata while retaining current fields.
- Modify: `apps/uiplan-studio/src/api/client.ts`  
  Add API client methods for graph load/save, package generate/list/read, proposal preview/apply, approval updates, and command registry read.
- Create: `apps/uiplan-studio/src/components/ApprovalPackagePanel.tsx`  
  Bottom panel for stage tabs, file tree, proposal drilldown, citations, findings, approval metadata, and apply controls.
- Create: `apps/uiplan-studio/src/components/StageControls.tsx`  
  Stage action buttons for Generate Plan Package, Generate Scaffold Package, disabled future stages, and deploy/publish guard text.
- Create: `apps/uiplan-studio/src/components/ProposalDrilldown.tsx`  
  Proposal detail view showing target path, owner nodes, project types, hashes, diff, citations, findings, and approval/apply status.
- Modify: `apps/uiplan-studio/src/components/DiagramCanvas.tsx`  
  Display typed node role, output type, selected project types, and approval/readiness badges.
- Modify: `apps/uiplan-studio/src/components/ContextInspector.tsx`  
  Edit v1 node role, output type, project types, context policy, and strict citation metadata.
- Modify: `apps/uiplan-studio/src/components/AgentPanel.tsx`  
  Surface Copilot package drafting as preview-only actions for Plan and Scaffold.
- Modify: `apps/uiplan-studio/src/App.tsx`  
  Wire package state, package generation, approval actions, proposal preview/apply, and Copilot readable context.
- Create: `apps/uiplan-studio/src/__tests__/generationTypes.test.ts`  
  Type-level and runtime fixture tests for package payload shapes.
- Create: `apps/uiplan-studio/src/__tests__/ApprovalPackagePanel.test.tsx`  
  UI tests for stage tabs, proposal drilldown, approval metadata, and disabled future stages.
- Modify: `apps/uiplan-studio/src/__tests__/App.test.tsx`  
  Integration tests for Plan/Scaffold generation, approval, guarded apply, and no deploy/publish action exposure.
- Modify: `apps/uiplan-studio/e2e/library-context.spec.ts`  
  Extend smoke coverage for strict citation blockers and package review flow.
- Modify: `docs/superpowers/specs/2026-05-05-uiplan-studio-generation-graph-design.md`  
  Add a short implementation-note section only if execution reveals a contract naming correction that must be documented.

---

## Phase 0 Tasks

### Task 1: Contract Schemas And Shared Types

**Files:**
- Create: `services/uiplan-studio-api/app/generation_contracts/__init__.py`
- Create: `services/uiplan-studio-api/app/generation_contracts/constants.py`
- Create: `services/uiplan-studio-api/app/generation_contracts/models.py`
- Create: `services/uiplan-studio-api/app/generation_contracts/schemas/generation-graph.v1.schema.json`
- Create: `services/uiplan-studio-api/app/generation_contracts/schemas/approval-package.v1.schema.json`
- Create: `services/uiplan-studio-api/app/generation_contracts/schemas/approval-state.v1.schema.json`
- Create: `services/uiplan-studio-api/app/generation_contracts/schemas/file-proposal.v1.schema.json`
- Create: `services/uiplan-studio-api/app/generation_contracts/schemas/command-registry.v1.schema.json`
- Create: `services/uiplan-studio-api/app/generation_contracts/schema_service.py`
- Modify: `services/uiplan-studio-api/app/schemas.py`
- Test: `services/uiplan-studio-api/tests/test_generation_contract_schemas.py`

- [ ] **Step 1: Write the failing schema coverage tests**

```python
# services/uiplan-studio-api/tests/test_generation_contract_schemas.py
import json
from pathlib import Path

from app.generation_contracts.constants import (
    APPROVAL_STATUS_VALUES,
    COMMAND_REGISTRY_SCHEMA_ID,
    GENERATION_GRAPH_SCHEMA_ID,
    NODE_ROLES,
    OUTPUT_TYPES,
    PROJECT_TYPES,
    STAGE_IDS,
)
from app.generation_contracts.schema_service import copy_contract_schemas, load_contract_schemas


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


def test_copy_contract_schemas_writes_bundle_schema_directory(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    written = copy_contract_schemas(bundle_root)

    schema_dir = bundle_root / ".uiplan" / "generation" / "schemas"
    assert sorted(path.name for path in written) == sorted(load_contract_schemas())
    assert json.loads((schema_dir / "generation-graph.v1.schema.json").read_text())[
        "$id"
    ] == GENERATION_GRAPH_SCHEMA_ID
```

- [ ] **Step 2: Run schema tests to verify failure**

Run: `python -m pytest services/uiplan-studio-api/tests/test_generation_contract_schemas.py -q`  
Expected: FAIL with `ModuleNotFoundError: No module named 'app.generation_contracts'`.

- [ ] **Step 3: Add contract constants and schema loader**

```python
# services/uiplan-studio-api/app/generation_contracts/__init__.py
"""UiPlan Studio generation graph and approval package contracts."""
```

```python
# services/uiplan-studio-api/app/generation_contracts/constants.py
from __future__ import annotations

GENERATION_GRAPH_SCHEMA_ID = "https://uipath.local/uiplan/generation-graph.v1"
APPROVAL_PACKAGE_SCHEMA_ID = "https://uipath.local/uiplan/approval-package.v1"
APPROVAL_STATE_SCHEMA_ID = "https://uipath.local/uiplan/approval-state.v1"
FILE_PROPOSAL_SCHEMA_ID = "https://uipath.local/uiplan/file-proposal.v1"
COMMAND_REGISTRY_SCHEMA_ID = "https://uipath.local/uiplan/command-registry.v1"

SCHEMA_VERSION = "v1"
GENERATOR_VERSION = "uiplan-studio-generation-graph-phase-0"

NODE_ROLES = [
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

OUTPUT_TYPES = [
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

PROJECT_TYPES = [
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

EDGE_TYPES = [
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

CONTEXT_SOURCE_KINDS = [
    "repo_doc",
    "library_book",
    "skill",
    "tool",
    "source_file",
    "user_note",
    "validation_output",
]

CONTEXT_SCOPES = ["graph", "node", "edge", "file", "stage"]
CONTEXT_POLICIES = ["strict", "advisory"]
APPROVAL_STATUS_VALUES = [
    "not_started",
    "ready_for_review",
    "changes_requested",
    "approved",
    "blocked",
    "applied",
    "superseded",
]
STAGE_IDS = ["01-plan", "02-scaffold", "03-code", "04-tests", "05-validation"]
FIRST_SCOPE_STAGE_IDS = ["01-plan", "02-scaffold"]
DEFERRED_STAGE_IDS = ["03-code", "04-tests", "05-validation"]
```

```python
# services/uiplan-studio-api/app/generation_contracts/schema_service.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"


def load_contract_schemas() -> dict[str, dict[str, Any]]:
    schemas: dict[str, dict[str, Any]] = {}
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schemas[path.name] = json.loads(path.read_text(encoding="utf-8"))
    if len(schemas) != 5:
        raise RuntimeError(f"expected 5 contract schemas in {SCHEMA_DIR}, found {len(schemas)}")
    return schemas


def copy_contract_schemas(bundle_root: Path) -> list[Path]:
    schema_target = bundle_root / ".uiplan" / "generation" / "schemas"
    schema_target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, payload in load_contract_schemas().items():
        target = schema_target / name
        target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(target)
    return written
```

- [ ] **Step 4: Add Pydantic contract models and export API aliases**

```python
# services/uiplan-studio-api/app/generation_contracts/models.py
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
```

```python
# services/uiplan-studio-api/app/schemas.py
from app.generation_contracts.models import (
    ApprovalPackageManifest,
    ApprovalState,
    CommandRegistry,
    FileProposal,
    GenerationGraph,
    GenerationGraphEdge,
    GenerationGraphNode,
    ProposalState,
    StageManifest,
)
```

- [ ] **Step 5: Add the five schema files with matching ids**

Use the Pydantic model field names from Step 4. Each schema file must include `$schema`, `$id`, `title`, `type`, `x-uiplan-schema-version`, `required`, `properties`, and `additionalProperties: false` for top-level objects.

Run: `python -m pytest services/uiplan-studio-api/tests/test_generation_contract_schemas.py -q`  
Expected: PASS with five schema files copied into the temp bundle schema directory.

---

### Task 2: Durable Approval Package Storage And State Machine

**Files:**
- Create: `services/uiplan-studio-api/app/generation_contracts/approval_state.py`
- Create: `services/uiplan-studio-api/app/generation_contracts/storage.py`
- Create: `services/uiplan-studio-api/tests/test_approval_state.py`
- Create: `services/uiplan-studio-api/tests/test_approval_package_storage.py`
- Modify: `services/uiplan-studio-api/app/main.py`

- [ ] **Step 1: Write failing approval transition tests**

```python
# services/uiplan-studio-api/tests/test_approval_state.py
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
```

- [ ] **Step 2: Write failing storage layout tests**

```python
# services/uiplan-studio-api/tests/test_approval_package_storage.py
import json
from pathlib import Path

from app.generation_contracts.models import (
    ApprovalPackageManifest,
    ApprovalState,
    GenerationGraph,
    StageManifest,
)
from app.generation_contracts.storage import (
    create_package_layout,
    list_packages,
    read_package_state,
    write_package_state,
)


def test_create_package_layout_writes_phase_zero_directories(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    graph = GenerationGraph(
        graph_id="graph-1",
        bundle_root=str(bundle_root),
        created_from="test",
    )

    layout = create_package_layout(
        bundle_root=bundle_root,
        package_id="pkg-1",
        graph=graph,
        context_manifest={"attachments": []},
        stages=[
            StageManifest(
                stage_id="01-plan",
                status="ready_for_review",
                input_graph_hash="graph-hash",
                input_context_hash="context-hash",
            )
        ],
        proposal_hashes={"01-plan:plan-doc": "proposal-hash"},
    )

    package_root = bundle_root / ".uiplan" / "generation" / "packages" / "pkg-1"
    assert layout.package_root == package_root
    assert (package_root / "manifest.json").is_file()
    assert (package_root / "graph.snapshot.json").is_file()
    assert (package_root / "context.manifest.json").is_file()
    assert (package_root / "approval-state.json").is_file()
    assert (package_root / "stages" / "01-plan" / "proposals").is_dir()
    assert (package_root / "stages" / "01-plan" / "diffs").is_dir()
    assert not (package_root / "stages" / "03-code").exists()
    assert json.loads((package_root / "manifest.json").read_text())["package_id"] == "pkg-1"


def test_package_state_round_trip_persists_review_metadata(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    package_root = bundle_root / ".uiplan" / "generation" / "packages" / "pkg-1"
    package_root.mkdir(parents=True)
    state = ApprovalState(
        package_id="pkg-1",
        current_stage="01-plan",
        stage_statuses={"01-plan": "ready_for_review", "02-scaffold": "not_started"},
    )

    write_package_state(package_root, state)

    loaded = read_package_state(package_root)
    assert loaded.package_id == "pkg-1"
    assert loaded.stage_statuses["01-plan"] == "ready_for_review"


def test_list_packages_returns_manifest_summaries(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    package_root = bundle_root / ".uiplan" / "generation" / "packages" / "pkg-1"
    package_root.mkdir(parents=True)
    manifest = ApprovalPackageManifest(
        package_id="pkg-1",
        graph_id="graph-1",
        bundle_root=str(bundle_root),
        generated_stages=["01-plan"],
        safety_policy={"direct_writes": False, "external_mutation": False},
    )
    (package_root / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

    packages = list_packages(bundle_root)

    assert [package.package_id for package in packages] == ["pkg-1"]
```

- [ ] **Step 3: Run approval and storage tests to verify failure**

Run: `python -m pytest services/uiplan-studio-api/tests/test_approval_state.py services/uiplan-studio-api/tests/test_approval_package_storage.py -q`  
Expected: FAIL with missing `approval_state` and `storage` modules.

- [ ] **Step 4: Implement transition rules exactly**

```python
# services/uiplan-studio-api/app/generation_contracts/approval_state.py
from __future__ import annotations

from app.generation_contracts.models import ApprovalState, ApprovalStatus, ProposalState, StageId, utc_now_iso

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
) -> ApprovalState:
    stage_statuses = {stage_id: "not_started" for stage_id in stage_ids}
    if "01-plan" in stage_statuses:
        stage_statuses["01-plan"] = "ready_for_review"
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
        current = updated.stage_statuses[target_id]
        _assert_allowed(current, next_status)
        updated.stage_statuses[target_id] = next_status
        updated.current_stage = target_id
    elif target == "proposal":
        proposal = updated.proposals[target_id]
        current = proposal.apply_status if next_status == "applied" else proposal.review_status
        _assert_allowed(current, next_status)
        if next_status == "applied":
            if proposal.review_status != "approved":
                raise ValueError("applied transition is not allowed before approval")
            if not preview_id:
                raise ValueError("preview_id is required when applying a proposal")
            proposal.apply_status = "applied"
            proposal.preview_id = preview_id
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
```

- [ ] **Step 5: Implement package storage layout**

Implement `services/uiplan-studio-api/app/generation_contracts/storage.py` with:

```python
PACKAGE_STAGE_DIRS = {
    "01-plan": ("proposals", "diffs"),
    "02-scaffold": ("proposals", "diffs"),
}
```

The `create_package_layout()` function must:

- write schemas through `copy_contract_schemas(bundle_root)`,
- create `.uiplan/generation/packages/<package-id>/`,
- write `manifest.json`, `graph.snapshot.json`, `context.manifest.json`, and `approval-state.json`,
- create only `stages/01-plan` and `stages/02-scaffold` directories for generated first-scope stages,
- write each `stage.manifest.json`,
- write empty `findings.json` and `reviewer-notes.md` files for each generated first-scope stage,
- avoid creating `03-code`, `04-tests`, or `05-validation` directories.

Run: `python -m pytest services/uiplan-studio-api/tests/test_approval_state.py services/uiplan-studio-api/tests/test_approval_package_storage.py -q`  
Expected: PASS.

---

### Task 3: Path Allowlist And Command Registry

**Files:**
- Create: `services/uiplan-studio-api/app/generation_contracts/path_allowlist.py`
- Create: `services/uiplan-studio-api/app/generation_contracts/command_registry.py`
- Create: `services/uiplan-studio-api/tests/test_path_allowlist_command_registry.py`

- [ ] **Step 1: Write failing path and command tests**

```python
# services/uiplan-studio-api/tests/test_path_allowlist_command_registry.py
from pathlib import Path

import pytest

from app.generation_contracts.command_registry import get_command_registry
from app.generation_contracts.path_allowlist import validate_target_path


@pytest.mark.parametrize(
    "target_path",
    [
        "/tmp/outside.md",
        "../outside.md",
        ".env",
        "config/tenant.secret.json",
        "skills/skills/uipath-rpa/SKILL.md",
        "node_modules/pkg/index.js",
        ".git/config",
        "dist/app.js",
    ],
)
def test_validate_target_path_rejects_unsafe_targets(tmp_path: Path, target_path: str) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    with pytest.raises(ValueError):
        validate_target_path(
            bundle_root=bundle_root,
            target_path=target_path,
            stage_id="01-plan",
            file_kind="document",
        )


def test_validate_target_path_allows_plan_and_scaffold_targets(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    plan_target = validate_target_path(
        bundle_root=bundle_root,
        target_path="docs/plan.md",
        stage_id="01-plan",
        file_kind="document",
    )
    scaffold_target = validate_target_path(
        bundle_root=bundle_root,
        target_path="projects/Agent.Intake/pyproject.toml",
        stage_id="02-scaffold",
        file_kind="project_scaffold",
    )

    assert plan_target == bundle_root / "docs" / "plan.md"
    assert scaffold_target == bundle_root / "projects" / "Agent.Intake" / "pyproject.toml"


def test_command_registry_contains_first_scope_commands_without_external_mutation() -> None:
    registry = get_command_registry()
    commands = {command.command_id: command for command in registry.commands}

    assert {"plan.markdown.readiness", "scaffold.manifest.readiness"}.issubset(commands)
    assert all(command.mutation_classification != "external-mutation" for command in registry.commands)
    assert all(command.required_confirmation is False for command in registry.commands)
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest services/uiplan-studio-api/tests/test_path_allowlist_command_registry.py -q`  
Expected: FAIL with missing modules.

- [ ] **Step 3: Implement path allowlist**

```python
# services/uiplan-studio-api/app/generation_contracts/path_allowlist.py
from __future__ import annotations

from pathlib import Path

SECRET_NAME_FRAGMENTS = ("secret", "credential", "token", "private-key", "private_key")
BLOCKED_SEGMENTS = {".git", "skills", "node_modules", "dist", "build", "__pycache__", ".vite"}
PLAN_PREFIXES = ("docs/", ".cursor/plans/")
SCAFFOLD_PREFIXES = ("projects/", "apps/", "services/", "packages/", "libs/")


def validate_target_path(
    *,
    bundle_root: Path,
    target_path: str,
    stage_id: str,
    file_kind: str,
) -> Path:
    raw = target_path.strip().replace("\\", "/")
    if not raw:
        raise ValueError("target path is required")
    if Path(raw).is_absolute():
        raise ValueError("absolute proposal paths are not allowed")
    if raw == ".env" or raw.endswith("/.env") or any(fragment in raw.lower() for fragment in SECRET_NAME_FRAGMENTS):
        raise ValueError("secret-like proposal paths are not allowed")
    parts = [part for part in raw.split("/") if part]
    if ".." in parts:
        raise ValueError("path traversal is not allowed")
    if any(part in BLOCKED_SEGMENTS for part in parts):
        raise ValueError("proposal path targets a blocked directory")
    if stage_id == "01-plan" and not raw.startswith(PLAN_PREFIXES):
        raise ValueError("Plan proposals must target documentation paths")
    if stage_id == "02-scaffold" and not raw.startswith(SCAFFOLD_PREFIXES):
        raise ValueError("Scaffold proposals must target explicit project or manifest paths")
    resolved_root = bundle_root.resolve()
    resolved_target = (resolved_root / raw).resolve()
    try:
        resolved_target.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("proposal path resolves outside the bundle root") from exc
    return resolved_target
```

- [ ] **Step 4: Implement first-scope command registry**

```python
# services/uiplan-studio-api/app/generation_contracts/command_registry.py
from __future__ import annotations

from app.generation_contracts.models import CommandRegistry, CommandRegistryEntry


def get_command_registry() -> CommandRegistry:
    return CommandRegistry(
        commands=[
            CommandRegistryEntry(
                command_id="plan.markdown.readiness",
                purpose="Check generated Plan markdown for required sections and citation markers.",
                owning_stage="01-plan",
                executable="python",
                fixed_args=["-m", "pytest", "services/uiplan-studio-api/tests/test_stage_package_generation.py"],
                working_directory_rule="repo_root",
                allowed_path_inputs=["docs/**/*.md", ".cursor/plans/**/*.md"],
                mutation_classification="read-only",
                required_confirmation=False,
                credential_requirements=[],
                output_summary_policy="Persist pass/fail count and first five assertion messages.",
            ),
            CommandRegistryEntry(
                command_id="scaffold.manifest.readiness",
                purpose="Check scaffold proposal manifests without creating project files.",
                owning_stage="02-scaffold",
                executable="python",
                fixed_args=["-m", "pytest", "services/uiplan-studio-api/tests/test_stage_package_generation.py"],
                working_directory_rule="repo_root",
                allowed_path_inputs=["projects/**", "apps/**", "services/**"],
                mutation_classification="read-only",
                required_confirmation=False,
                credential_requirements=[],
                output_summary_policy="Persist pass/fail count and first five assertion messages.",
            ),
        ]
    )
```

- [ ] **Step 5: Run targeted tests**

Run: `python -m pytest services/uiplan-studio-api/tests/test_path_allowlist_command_registry.py -q`  
Expected: PASS.

---

### Task 4: Backend Plan Package Generation

**Files:**
- Create: `services/uiplan-studio-api/app/generation_contracts/package_generation.py`
- Modify: `services/uiplan-studio-api/app/main.py`
- Modify: `services/uiplan-studio-api/app/schemas.py`
- Create: `services/uiplan-studio-api/tests/test_stage_package_generation.py`
- Modify: `services/uiplan-studio-api/tests/test_main.py`

- [ ] **Step 1: Write failing Plan package generation tests**

```python
# services/uiplan-studio-api/tests/test_stage_package_generation.py
import json
from pathlib import Path

from app.generation_contracts.models import GenerationContextAttachment, GenerationGraph, GenerationGraphNode
from app.generation_contracts.package_generation import generate_approval_package


def _mixed_graph(bundle_root: Path) -> GenerationGraph:
    return GenerationGraph(
        graph_id="graph-plan",
        bundle_root=str(bundle_root),
        created_from="test",
        nodes=[
            GenerationGraphNode(
                id="intake",
                title="Customer Intake",
                role="process_step",
                output_type="document",
                project_types=["docs", "coded-agent"],
                description="Capture customer request and decide next action.",
                context_attachment_ids=["ctx-1"],
            ),
            GenerationGraphNode(
                id="deploy",
                title="Deployment Gate",
                role="deployment_gate",
                output_type="approval_gate",
                project_types=["platform-resource"],
                description="Manual deployment readiness only.",
                context_attachment_ids=["ctx-2"],
            ),
        ],
        context_attachments=[
            GenerationContextAttachment(
                source_kind="repo_doc",
                source_id="docs/PDD.md",
                citation="docs/PDD.md",
                scope="graph",
                policy="advisory",
                summary="Business context for intake.",
            ),
            GenerationContextAttachment(
                source_kind="library_book",
                source_id="uipath-cli/package-analyze",
                citation="uipath-cli/package-analyze",
                scope="node",
                policy="strict",
                summary="Deployment gate commands are strict context.",
            ),
        ],
    )


def test_generate_plan_package_persists_manifest_and_proposal(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    package = generate_approval_package(
        bundle_root=bundle_root,
        graph=_mixed_graph(bundle_root),
        requested_stages=["01-plan"],
        reviewer="Daniela",
    )

    package_root = bundle_root / ".uiplan" / "generation" / "packages" / package.package_id
    plan_stage = package_root / "stages" / "01-plan"
    proposals = sorted((plan_stage / "proposals").glob("*.md"))

    assert package.generated_stages == ["01-plan"]
    assert len(proposals) == 1
    proposal_text = proposals[0].read_text(encoding="utf-8")
    assert "# UiPlan Generation Plan" in proposal_text
    assert "Customer Intake" in proposal_text
    assert "uipath-cli/package-analyze" in proposal_text
    assert "No deploy, publish, invoke, or external mutation command is executed." in proposal_text
    state = json.loads((package_root / "approval-state.json").read_text(encoding="utf-8"))
    assert state["stage_statuses"]["01-plan"] == "ready_for_review"
    assert state["stage_statuses"]["03-code"] == "not_started"


def test_plan_package_blocks_missing_strict_context_for_deployment_gate(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    graph = _mixed_graph(bundle_root)
    graph.context_attachments = [
        attachment for attachment in graph.context_attachments if attachment.policy != "strict"
    ]

    package = generate_approval_package(
        bundle_root=bundle_root,
        graph=graph,
        requested_stages=["01-plan"],
        reviewer="Daniela",
    )

    package_root = bundle_root / ".uiplan" / "generation" / "packages" / package.package_id
    findings = json.loads(
        (package_root / "stages" / "01-plan" / "findings.json").read_text(encoding="utf-8")
    )
    assert findings[0]["severity"] == "error"
    assert findings[0]["blocks_apply"] is True
    assert "strict citation" in findings[0]["message"].lower()
```

- [ ] **Step 2: Run Plan generation tests to verify failure**

Run: `python -m pytest services/uiplan-studio-api/tests/test_stage_package_generation.py::test_generate_plan_package_persists_manifest_and_proposal -q`  
Expected: FAIL with missing `package_generation` module.

- [ ] **Step 3: Implement deterministic Plan package generator**

Implement `generate_approval_package()` in `services/uiplan-studio-api/app/generation_contracts/package_generation.py` with these rules:

- Accept only requested stages in `["01-plan", "02-scaffold"]`; raise `ValueError("stage generation is deferred: <stage>")` for `03-code`, `04-tests`, and `05-validation`.
- Compute `package_id` as `pkg-<first-12-chars-of-sha256(graph json + requested stages)>`.
- Build `graph.snapshot.json` from the supplied `GenerationGraph`.
- Build `context.manifest.json` with `attachments`, `strict_attachment_count`, and `advisory_attachment_count`.
- Generate one Plan proposal at `docs/uiplan-generation-plan.md`.
- Write proposal content to `stages/01-plan/proposals/uiplan-generation-plan.md`.
- Write unified diff against empty content to `stages/01-plan/diffs/uiplan-generation-plan.md.diff`.
- Include citation strings from strict and advisory attachments in the proposal metadata.
- Record a blocking finding when any `deployment_gate`, `orchestrator_resource`, `validation_report`, `asset`, `queue`, runtime, security, credential, deploy, or production-scoped node lacks a strict citation.
- Set `apply_eligible` to `False` when blocking findings exist and `True` otherwise.

Plan proposal content must include these exact headings:

```markdown
# UiPlan Generation Plan

## Solution Intent

## Architecture

## Graph Nodes

## Context And Citations

## Safety Policy

## Implementation Sequence
```

- [ ] **Step 4: Add backend endpoints for Plan package generation and package read**

Add models to `services/uiplan-studio-api/app/schemas.py`:

```python
class GenerateApprovalPackageRequest(BaseModel):
    bundle_root: str
    graph: GenerationGraph
    stages: list[StageId]
    reviewer: str | None = None


class PackageListResponse(BaseModel):
    packages: list[ApprovalPackageManifest]


class PackageDetailResponse(BaseModel):
    manifest: ApprovalPackageManifest
    approval_state: ApprovalState
    stages: list[StageManifest]
    proposals: list[FileProposal]
```

Add routes to `services/uiplan-studio-api/app/main.py`:

- `POST /generation/packages` creates Plan/Scaffold packages.
- `GET /generation/packages?bundle_root=<root>` lists package manifests.
- `GET /generation/packages/{package_id}?bundle_root=<root>` returns manifest, state, stage manifests, and file proposal manifests.

Run: `python -m pytest services/uiplan-studio-api/tests/test_stage_package_generation.py -q`  
Expected: Plan package tests PASS and deferred-stage test still absent until Task 5.

- [ ] **Step 5: Add API tests for Plan route and no target-file writes**

Append to `services/uiplan-studio-api/tests/test_main.py`:

```python
def test_generation_package_endpoint_creates_plan_package_without_target_write(monkeypatch, tmp_path):
    plans_root = tmp_path / "plans"
    bundle_root = plans_root / "example"
    bundle_root.mkdir(parents=True)
    monkeypatch.setattr(main, "PLANS_ROOT", plans_root.resolve())
    target_doc = bundle_root / "docs" / "uiplan-generation-plan.md"

    client = TestClient(app)
    response = client.post(
        "/generation/packages",
        json={
            "bundle_root": str(bundle_root),
            "reviewer": "Daniela",
            "stages": ["01-plan"],
            "graph": {
                "graph_id": "graph-api",
                "bundle_root": str(bundle_root),
                "created_from": "test",
                "nodes": [
                    {
                        "id": "plan-node",
                        "title": "Plan Node",
                        "role": "process_step",
                        "output_type": "document",
                        "project_types": ["docs"],
                        "description": "Create implementation plan.",
                    }
                ],
                "edges": [],
                "context_attachments": [],
                "generation_profile": {"allowed_project_types": ["docs"]},
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["generated_stages"] == ["01-plan"]
    assert not target_doc.exists()
```

Run: `python -m pytest services/uiplan-studio-api/tests/test_main.py::test_generation_package_endpoint_creates_plan_package_without_target_write -q`  
Expected: PASS.

---

### Task 5: Backend Scaffold Package Generation

**Files:**
- Modify: `services/uiplan-studio-api/app/generation_contracts/package_generation.py`
- Modify: `services/uiplan-studio-api/app/generation_contracts/storage.py`
- Modify: `services/uiplan-studio-api/tests/test_stage_package_generation.py`
- Modify: `services/uiplan-studio-api/tests/test_main.py`

- [ ] **Step 1: Add failing Scaffold and deferred-stage tests**

```python
# append to services/uiplan-studio-api/tests/test_stage_package_generation.py
import pytest


def test_generate_scaffold_package_uses_prior_plan_and_writes_manifest_proposals(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    graph = _mixed_graph(bundle_root)

    package = generate_approval_package(
        bundle_root=bundle_root,
        graph=graph,
        requested_stages=["01-plan", "02-scaffold"],
        reviewer="Daniela",
    )

    package_root = bundle_root / ".uiplan" / "generation" / "packages" / package.package_id
    scaffold_stage = package_root / "stages" / "02-scaffold"
    proposals = sorted(path.name for path in (scaffold_stage / "proposals").glob("*"))

    assert "projects-customer-intake-manifest.json" in proposals
    manifest = json.loads(
        (scaffold_stage / "proposals" / "projects-customer-intake-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["package_name"] == "UiPlan.CustomerIntake"
    assert manifest["project_types"] == ["docs", "coded-agent"]
    assert manifest["direct_write"] is False
    assert manifest["external_mutation"] is False
    state = json.loads((package_root / "approval-state.json").read_text(encoding="utf-8"))
    assert state["stage_statuses"]["02-scaffold"] == "ready_for_review"


def test_code_tests_and_validation_generation_are_deferred(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    with pytest.raises(ValueError, match="stage generation is deferred: 03-code"):
        generate_approval_package(
            bundle_root=bundle_root,
            graph=_mixed_graph(bundle_root),
            requested_stages=["03-code"],
            reviewer="Daniela",
        )
```

- [ ] **Step 2: Run Scaffold tests to verify failure**

Run: `python -m pytest services/uiplan-studio-api/tests/test_stage_package_generation.py::test_generate_scaffold_package_uses_prior_plan_and_writes_manifest_proposals services/uiplan-studio-api/tests/test_stage_package_generation.py::test_code_tests_and_validation_generation_are_deferred -q`  
Expected: first test FAIL because Scaffold is not generated yet; second test PASS only if Task 4 already rejected deferred stages.

- [ ] **Step 3: Implement Scaffold package generation**

Extend `generate_approval_package()` so `02-scaffold`:

- Requires `01-plan` in the same package request or an approved prior Plan package in storage.
- Generates one JSON scaffold proposal per `project_component` or `process_step` node with project types.
- Uses deterministic proposal file names: `projects-<slug>-manifest.json`.
- Targets `projects/<PascalTitle>/project.manifest.json`.
- Stores proposed content containing `package_name`, `node_id`, `project_types`, `recommended_files`, `non_secret_config`, `direct_write: false`, and `external_mutation: false`.
- Uses `validate_target_path()` with `stage_id="02-scaffold"` and `file_kind="project_scaffold"`.
- Records recommended command ids from `get_command_registry()` in `stage.manifest.json`.

For the sample `Customer Intake` node, the generated JSON content must include:

```json
{
  "package_name": "UiPlan.CustomerIntake",
  "node_id": "intake",
  "project_types": ["docs", "coded-agent"],
  "recommended_files": [
    "projects/CustomerIntake/README.md",
    "projects/CustomerIntake/project.manifest.json"
  ],
  "non_secret_config": {
    "secret_storage": "Use Orchestrator assets or environment variable references only"
  },
  "direct_write": false,
  "external_mutation": false
}
```

- [ ] **Step 4: Add route test for rejected deferred stages**

Append to `services/uiplan-studio-api/tests/test_main.py`:

```python
def test_generation_package_endpoint_rejects_deferred_stage(monkeypatch, tmp_path):
    plans_root = tmp_path / "plans"
    bundle_root = plans_root / "example"
    bundle_root.mkdir(parents=True)
    monkeypatch.setattr(main, "PLANS_ROOT", plans_root.resolve())

    client = TestClient(app)
    response = client.post(
        "/generation/packages",
        json={
            "bundle_root": str(bundle_root),
            "stages": ["03-code"],
            "graph": {
                "graph_id": "graph-api",
                "bundle_root": str(bundle_root),
                "created_from": "test",
                "nodes": [],
                "edges": [],
                "context_attachments": [],
            },
        },
    )

    assert response.status_code == 400
    assert "stage generation is deferred: 03-code" in response.json()["detail"]
```

- [ ] **Step 5: Run backend package generation tests**

Run: `python -m pytest services/uiplan-studio-api/tests/test_stage_package_generation.py services/uiplan-studio-api/tests/test_main.py -q`  
Expected: PASS with Plan and Scaffold package generation, no target source writes, and deferred-stage rejection covered.

---

### Task 6: Frontend Approval Package UI And Stage Controls

**Files:**
- Create: `apps/uiplan-studio/src/generationTypes.ts`
- Create: `apps/uiplan-studio/src/components/ApprovalPackagePanel.tsx`
- Create: `apps/uiplan-studio/src/components/StageControls.tsx`
- Create: `apps/uiplan-studio/src/components/ProposalDrilldown.tsx`
- Modify: `apps/uiplan-studio/src/api/client.ts`
- Modify: `apps/uiplan-studio/src/types.ts`
- Modify: `apps/uiplan-studio/src/components/DiagramCanvas.tsx`
- Modify: `apps/uiplan-studio/src/components/ContextInspector.tsx`
- Modify: `apps/uiplan-studio/src/App.tsx`
- Create: `apps/uiplan-studio/src/__tests__/generationTypes.test.ts`
- Create: `apps/uiplan-studio/src/__tests__/ApprovalPackagePanel.test.tsx`
- Modify: `apps/uiplan-studio/src/__tests__/App.test.tsx`

- [ ] **Step 1: Write failing UI tests for package review**

```tsx
// apps/uiplan-studio/src/__tests__/ApprovalPackagePanel.test.tsx
import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import ApprovalPackagePanel from "../components/ApprovalPackagePanel";
import type { ApprovalPackageDetail } from "../generationTypes";

const packageDetail: ApprovalPackageDetail = {
  manifest: {
    package_id: "pkg-1",
    graph_id: "graph-1",
    bundle_root: ".cursor/plans/example",
    generated_stages: ["01-plan", "02-scaffold"],
    created_at: "2026-05-05T00:00:00Z",
    schema_id: "https://uipath.local/uiplan/approval-package.v1",
    schema_version: "v1",
    generator_version: "uiplan-studio-generation-graph-phase-0",
    safety_policy: { direct_writes: false, external_mutation: false },
  },
  approval_state: {
    package_id: "pkg-1",
    current_stage: "01-plan",
    stage_statuses: {
      "01-plan": "ready_for_review",
      "02-scaffold": "ready_for_review",
      "03-code": "not_started",
      "04-tests": "not_started",
      "05-validation": "not_started",
    },
    proposals: {},
    applied_preview_ids: [],
    superseded_preview_ids: [],
    reviewer_notes: [],
    updated_at: "2026-05-05T00:00:00Z",
  },
  stages: [
    {
      stage_id: "01-plan",
      status: "ready_for_review",
      input_graph_hash: "graph-hash",
      input_context_hash: "context-hash",
      generated_files: ["docs/uiplan-generation-plan.md"],
      required_approvals: ["proposal"],
      blocking_findings: [],
      validation_commands: ["plan.markdown.readiness"],
      apply_eligible: true,
    },
  ],
  proposals: [
    {
      proposal_id: "01-plan:uiplan-generation-plan",
      stage_id: "01-plan",
      target_path: "docs/uiplan-generation-plan.md",
      file_kind: "document",
      owning_node_ids: ["intake"],
      project_type_ids: ["docs"],
      proposed_content_hash: "proposal-hash",
      base_hash: null,
      diff_path: "stages/01-plan/diffs/uiplan-generation-plan.md.diff",
      proposal_path: "stages/01-plan/proposals/uiplan-generation-plan.md",
      citations: ["docs/PDD.md"],
      findings: [],
      apply_eligible: true,
    },
  ],
};

test("renders package stages, proposal drilldown, citations, and disabled future stages", () => {
  const onApproveProposal = vi.fn();
  const onPreviewProposal = vi.fn();
  const onApplyProposal = vi.fn();

  render(
    <ApprovalPackagePanel
      packageDetail={packageDetail}
      selectedProposalId="01-plan:uiplan-generation-plan"
      onSelectProposal={() => undefined}
      onApproveProposal={onApproveProposal}
      onPreviewProposal={onPreviewProposal}
      onApplyProposal={onApplyProposal}
    />,
  );

  expect(screen.getByText("Approval Package")).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Plan ready_for_review" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Scaffold ready_for_review" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Code deferred" })).toBeDisabled();
  expect(screen.getByText("docs/uiplan-generation-plan.md")).toBeInTheDocument();
  expect(screen.getByText("docs/PDD.md")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Approve proposal" }));
  expect(onApproveProposal).toHaveBeenCalledWith("01-plan:uiplan-generation-plan");
});
```

- [ ] **Step 2: Write failing app integration test for package generation flow**

Append to `apps/uiplan-studio/src/__tests__/App.test.tsx`:

```tsx
test("generates Plan and Scaffold approval packages without deploy actions", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: { "spec.md": "# Spec\n", "plan.md": "# Plan\n", "tasks.md": "# Tasks\n" },
      });
    }
    if (url.endsWith("/generation/packages") && !url.includes("?")) {
      return mockJsonResponse({
        package_id: "pkg-1",
        graph_id: "graph-1",
        bundle_root: ".cursor/plans/example",
        generated_stages: ["01-plan"],
        created_at: "2026-05-05T00:00:00Z",
        schema_id: "https://uipath.local/uiplan/approval-package.v1",
        schema_version: "v1",
        generator_version: "uiplan-studio-generation-graph-phase-0",
        safety_policy: { direct_writes: false, external_mutation: false },
      });
    }
    if (url.includes("/generation/packages/pkg-1")) {
      return mockJsonResponse({
        manifest: {
          package_id: "pkg-1",
          graph_id: "graph-1",
          bundle_root: ".cursor/plans/example",
          generated_stages: ["01-plan"],
          created_at: "2026-05-05T00:00:00Z",
          schema_id: "https://uipath.local/uiplan/approval-package.v1",
          schema_version: "v1",
          generator_version: "uiplan-studio-generation-graph-phase-0",
          safety_policy: { direct_writes: false, external_mutation: false },
        },
        approval_state: {
          package_id: "pkg-1",
          current_stage: "01-plan",
          stage_statuses: {
            "01-plan": "ready_for_review",
            "02-scaffold": "not_started",
            "03-code": "not_started",
            "04-tests": "not_started",
            "05-validation": "not_started",
          },
          proposals: {},
          applied_preview_ids: [],
          superseded_preview_ids: [],
          reviewer_notes: [],
          updated_at: "2026-05-05T00:00:00Z",
        },
        stages: [],
        proposals: [],
      });
    }
    return mockJsonResponse({ categories: [] });
  });

  render(<App />);
  await screen.findByText("UiPlan Studio");
  fireEvent.click(await screen.findByRole("button", { name: "Generate Plan Package" }));

  await waitFor(() =>
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/generation/packages",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"stages":["01-plan"]'),
      }),
    ),
  );
  expect(await screen.findByText("Approval Package")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Deploy/i })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Publish/i })).not.toBeInTheDocument();
});
```

- [ ] **Step 3: Run UI tests to verify failure**

Run: `cd apps/uiplan-studio; npm test -- src/__tests__/ApprovalPackagePanel.test.tsx src/__tests__/App.test.tsx`  
Expected: FAIL because the new components and API methods do not exist.

- [ ] **Step 4: Add frontend generation types and API methods**

Create `apps/uiplan-studio/src/generationTypes.ts` with exported types:

```ts
export type StageId = "01-plan" | "02-scaffold" | "03-code" | "04-tests" | "05-validation";
export type ApprovalStatus =
  | "not_started"
  | "ready_for_review"
  | "changes_requested"
  | "approved"
  | "blocked"
  | "applied"
  | "superseded";
export type ProjectType =
  | "rpa"
  | "coded-automation"
  | "coded-agent"
  | "maestro-flow"
  | "coded-app"
  | "coded-action-app"
  | "api-workflow"
  | "solution"
  | "library"
  | "test"
  | "docs"
  | "platform-resource";

export interface ApprovalPackageManifest {
  schema_id: string;
  schema_version: string;
  package_id: string;
  graph_id: string;
  bundle_root: string;
  generated_stages: StageId[];
  generator_version: string;
  created_at: string;
  safety_policy: Record<string, string | boolean>;
}

export interface StageManifest {
  stage_id: StageId;
  status: ApprovalStatus;
  input_graph_hash: string;
  input_context_hash: string;
  generated_files: string[];
  required_approvals: string[];
  blocking_findings: Array<{ severity: string; message: string; blocks_apply: boolean }>;
  validation_commands: string[];
  apply_eligible: boolean;
}

export interface FileProposal {
  proposal_id: string;
  stage_id: StageId;
  target_path: string;
  file_kind: string;
  owning_node_ids: string[];
  project_type_ids: ProjectType[];
  proposed_content_hash: string;
  base_hash: string | null;
  diff_path: string;
  proposal_path: string;
  citations: string[];
  findings: Array<{ severity: string; message: string; blocks_apply: boolean }>;
  apply_eligible: boolean;
}

export interface ApprovalState {
  package_id: string;
  current_stage: StageId;
  stage_statuses: Record<StageId, ApprovalStatus>;
  proposals: Record<string, unknown>;
  reviewer_notes: string[];
  applied_preview_ids: string[];
  superseded_preview_ids: string[];
  updated_at: string;
}

export interface ApprovalPackageDetail {
  manifest: ApprovalPackageManifest;
  approval_state: ApprovalState;
  stages: StageManifest[];
  proposals: FileProposal[];
}
```

Update `apps/uiplan-studio/src/api/client.ts` with methods:

- `generateApprovalPackage(bundleRoot, graph, stages, reviewer)`
- `listApprovalPackages(bundleRoot)`
- `loadApprovalPackage(bundleRoot, packageId)`
- `updateApprovalState(bundleRoot, packageId, target, targetId, nextStatus, reviewer, note)`
- `previewProposal(bundleRoot, packageId, proposalId)`
- `applyProposalPreview(bundleRoot, packageId, proposalId, previewId)`

- [ ] **Step 5: Implement package panel and stage controls**

`ApprovalPackagePanel` must:

- render tabs for Plan and Scaffold when present,
- render disabled tabs labelled `Code deferred`, `Tests deferred`, and `Validation deferred`,
- list proposals by `target_path`,
- render selected proposal details through `ProposalDrilldown`,
- show citations, findings, hashes, owning nodes, project types, and apply eligibility,
- enable approve only when proposal `apply_eligible` is true,
- enable apply only after preview id exists in parent state.

`StageControls` must:

- show `Generate Plan Package`,
- show `Generate Scaffold Package` disabled until Plan stage status is `approved` or package includes `01-plan`,
- show future stage buttons disabled with labels `Code deferred`, `Tests deferred`, and `Validation deferred`,
- show guard text: `Deploy and publish are out of scope for generation packages.`

Run: `cd apps/uiplan-studio; npm test -- src/__tests__/ApprovalPackagePanel.test.tsx src/__tests__/App.test.tsx`  
Expected: PASS.

---

### Task 7: Copilot And Context Integration For Package Drafting

**Files:**
- Modify: `services/uiplan-studio-api/app/copilot_runtime.py`
- Modify: `services/uiplan-studio-api/tests/test_main.py`
- Modify: `apps/uiplan-studio/src/components/AgentPanel.tsx`
- Modify: `apps/uiplan-studio/src/App.tsx`
- Modify: `apps/uiplan-studio/src/__tests__/App.test.tsx`

- [ ] **Step 1: Write failing Copilot action tests**

Append to `services/uiplan-studio-api/tests/test_main.py`:

```python
def test_copilotkit_info_exposes_package_drafting_actions() -> None:
    client = TestClient(app)
    response = client.get("/copilotkit/info")

    assert response.status_code == 200
    action_names = {action["name"] for action in response.json()["actions"]}
    assert "draft_plan_package_request" in action_names
    assert "draft_scaffold_package_request" in action_names


def test_copilot_package_drafting_actions_are_preview_only() -> None:
    client = TestClient(app)
    response = client.post(
        "/copilotkit/runtime/action/draft_plan_package_request",
        json={
            "arguments": {
                "bundle_root": ".cursor/plans/example",
                "graph_id": "graph-1",
                "selected_node_id": "intake",
            }
        },
    )

    assert response.status_code == 200
    result = response.json()["result"]
    assert result["endpoint"] == "/generation/packages"
    assert result["method"] == "POST"
    assert result["write_policy"] == "approval_package_only"
    assert result["body"]["stages"] == ["01-plan"]
```

- [ ] **Step 2: Run Copilot tests to verify failure**

Run: `python -m pytest services/uiplan-studio-api/tests/test_main.py::test_copilotkit_info_exposes_package_drafting_actions services/uiplan-studio-api/tests/test_main.py::test_copilot_package_drafting_actions_are_preview_only -q`  
Expected: FAIL because actions are not registered.

- [ ] **Step 3: Add preview-only Copilot package draft actions**

Update `services/uiplan-studio-api/app/copilot_runtime.py`:

- Add `draft_plan_package_request` and `draft_scaffold_package_request` to `COPILOT_ACTION_NAMES`.
- Implement both handlers returning endpoint `/generation/packages`, method `POST`, `write_policy: "approval_package_only"`, no target-file content, no apply instruction, and no deploy/publish command.
- Add fallback action handlers and official `Action` metadata for both actions.
- Keep `draft_section_preview_request` for legacy document previews.

The Plan action response body must include:

```python
{
    "bundle_root": bundle_root,
    "stages": ["01-plan"],
    "reviewer": None,
    "graph_ref": {"graph_id": graph_id, "selected_node_id": selected_node_id},
}
```

The Scaffold action response body must include:

```python
{
    "bundle_root": bundle_root,
    "stages": ["02-scaffold"],
    "reviewer": None,
    "graph_ref": {"graph_id": graph_id, "selected_node_id": selected_node_id},
}
```

- [ ] **Step 4: Surface package drafting in frontend Copilot context**

Update `apps/uiplan-studio/src/App.tsx` so `CopilotStudioContext` readable state includes:

- current `bundleRoot`,
- current typed graph fields,
- selected package id,
- selected proposal id,
- loaded package detail summary,
- safety policy text `Generation creates approval packages only; apply is separate and guarded`.

Update `apps/uiplan-studio/src/components/AgentPanel.tsx` to render two buttons:

- `Draft Plan package request`
- `Draft Scaffold package request`

Both buttons call parent handlers that populate the chat log with the drafted request summary and do not apply or write target files.

- [ ] **Step 5: Run backend and frontend Copilot tests**

Run: `python -m pytest services/uiplan-studio-api/tests/test_main.py -q`  
Expected: PASS.

Run: `cd apps/uiplan-studio; npm test -- src/__tests__/App.test.tsx`  
Expected: PASS, including package drafting controls and no deploy/publish buttons.

---

### Task 8: Docs, E2E, And Final Verification

**Files:**
- Modify: `apps/uiplan-studio/e2e/library-context.spec.ts`
- Modify: `docs/superpowers/specs/2026-05-05-uiplan-studio-generation-graph-design.md`
- Test: `services/uiplan-studio-api/tests/test_generation_contract_schemas.py`
- Test: `services/uiplan-studio-api/tests/test_approval_state.py`
- Test: `services/uiplan-studio-api/tests/test_path_allowlist_command_registry.py`
- Test: `services/uiplan-studio-api/tests/test_approval_package_storage.py`
- Test: `services/uiplan-studio-api/tests/test_stage_package_generation.py`
- Test: `services/uiplan-studio-api/tests/test_main.py`
- Test: `apps/uiplan-studio/src/__tests__/generationTypes.test.ts`
- Test: `apps/uiplan-studio/src/__tests__/ApprovalPackagePanel.test.tsx`
- Test: `apps/uiplan-studio/src/__tests__/App.test.tsx`
- Test: `apps/uiplan-studio/e2e/library-context.spec.ts`

- [ ] **Step 1: Extend E2E smoke test for package flow**

Add an E2E scenario to `apps/uiplan-studio/e2e/library-context.spec.ts` that:

- opens UiPlan Studio,
- attaches library context,
- clicks `Generate Plan Package`,
- verifies `Approval Package` appears,
- verifies `Code deferred`, `Tests deferred`, and `Validation deferred` are visible and disabled,
- verifies no `Deploy` or `Publish` button exists,
- opens one proposal drilldown,
- verifies citations and findings sections are visible.

Run: `cd apps/uiplan-studio; npx playwright test e2e/library-context.spec.ts`  
Expected: PASS against the local dev server configured for the existing E2E suite.

- [ ] **Step 2: Add a spec implementation note if naming drift was found**

Only modify `docs/superpowers/specs/2026-05-05-uiplan-studio-generation-graph-design.md` if execution standardized one contract name differently than the approved design. The allowed note format is:

```markdown
## Implementation Notes

- Phase 0 implementation standardizes package stage file proposal directories as `proposals/` in manifests and API payloads. Existing prose that mentions `proposed-files/` is treated as historical wording for the same concept.
```

Run: `git diff -- docs/superpowers/specs/2026-05-05-uiplan-studio-generation-graph-design.md`  
Expected: empty diff unless the exact note above was needed.

- [ ] **Step 3: Run backend verification**

Run: `python -m pytest services/uiplan-studio-api/tests/test_generation_contract_schemas.py services/uiplan-studio-api/tests/test_approval_state.py services/uiplan-studio-api/tests/test_path_allowlist_command_registry.py services/uiplan-studio-api/tests/test_approval_package_storage.py services/uiplan-studio-api/tests/test_stage_package_generation.py services/uiplan-studio-api/tests/test_main.py -q`  
Expected: PASS.

- [ ] **Step 4: Run frontend verification**

Run: `cd apps/uiplan-studio; npm test -- src/__tests__/generationTypes.test.ts src/__tests__/ApprovalPackagePanel.test.tsx src/__tests__/App.test.tsx`  
Expected: PASS.

Run: `cd apps/uiplan-studio; npm run build`  
Expected: PASS with Vite build output and no TypeScript errors.

- [ ] **Step 5: Run safety verification**

Run: `python -m uipath_claude.skills.submodule_guard`  
Expected: `submodule-guard: OK`.

Run: `git diff --name-only`  
Expected: only files listed in this plan plus generated package fixture files created by tests under temporary directories outside the repository.

Run: `git diff --check`  
Expected: no whitespace errors.

---

## Cross-Task Safety Invariants

- Generation endpoints create approval package files under `.uiplan/generation/` only.
- No generation endpoint writes target source, document, manifest, asset, queue, package, deployment, or runtime files directly.
- Preview/apply remains the only route from proposal content to target files.
- Apply requires an approved proposal, a preview id, and a matching base hash.
- Plan and Scaffold are the only generated stages in first implementation scope.
- Code, Tests, and Validation generation routes return errors or disabled UI states until the same contracts are used.
- Strict citations block apply for deployment, production, runtime, security, credential, Orchestrator resource, and validation-scoped nodes.
- Deploy, publish, invoke, job run, package upload, asset creation, queue creation, and external mutation commands are not exposed as executable package actions.
- Secrets are represented only as references to Orchestrator assets, environment variables, or bindings.
- Existing user files are not overwritten without preview, diff, approval, and hash check.

---

## Self-Review

### 1) Spec Coverage

- Phase 0 contract scope is covered by Tasks 1, 2, and 3: schema files/versioning, approval state machine, durable metadata, package/proposal storage layout, path allowlist, and command registry.
- First implementation scope is covered by Tasks 4 and 5: Plan and Scaffold approval packages only, with durable approval state and proposal metadata.
- Code, Tests, and Validation deferral is covered by Task 5 backend tests and Task 6 UI disabled states.
- Safety invariants are covered by Tasks 3, 4, 5, 6, and 8: no direct writes, strict path checks, preview/apply-only controls, no deploy/publish/runtime mutation actions, and strict citation blockers.
- UI workflow requirements are covered by Task 6: stage tabs, file drilldown, citations, findings, reviewer metadata, and apply controls.
- Copilot/context integration is covered by Task 7: package drafting actions are preview-only and grounded in current graph/package context.
- Verification strategy is covered by Task 8 with backend, frontend, E2E, build, guard, and diff checks.

### 2) Placeholder Scan

- The plan avoids unresolved marker strings and ellipsis markers.
- Every task has exact file paths, exact commands, expected outcomes, and concrete test or implementation detail.
- Code, schema, and UI names are defined before later tasks reference them.

### 3) Type Consistency

- Backend stage ids are consistently `01-plan`, `02-scaffold`, `03-code`, `04-tests`, and `05-validation`.
- Approval statuses are consistently `not_started`, `ready_for_review`, `changes_requested`, `approved`, `blocked`, `applied`, and `superseded`.
- Schema ids consistently use `https://uipath.local/uiplan/<contract>.v1`.
- Package storage consistently uses `.uiplan/generation/packages/<package-id>/stages/<stage-id>/proposals/` and `diffs/`.
- Frontend types mirror backend manifest, state, stage, and proposal model names.
