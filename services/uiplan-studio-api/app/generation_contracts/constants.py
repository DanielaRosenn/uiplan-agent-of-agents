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
