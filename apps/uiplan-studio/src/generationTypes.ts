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
  diff?: string;
  diff_body?: string;
  diff_content?: string;
  citations: string[];
  findings: Array<{ severity: string; message: string; blocks_apply: boolean }>;
  apply_eligible: boolean;
}

export interface ProposalApprovalState {
  status?: ApprovalStatus;
  review_status?: ApprovalStatus;
  apply_status?: ApprovalStatus;
  proposal_id?: string;
  stage_id?: StageId;
  reviewer?: string | null;
  reviewer_notes?: string | null;
  source_graph_hash?: string;
  context_manifest_hash?: string;
  proposal_hash?: string;
  base_file_hash?: string | null;
  preview_id?: string | null;
  superseded_by?: string | null;
  blocked_reason?: string | null;
  updated_at?: string;
}

export interface ApprovalState {
  package_id: string;
  current_stage: StageId;
  stage_statuses: Record<StageId, ApprovalStatus>;
  proposals: Record<string, ProposalApprovalState | ApprovalStatus | unknown>;
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

export interface CommandRegistryEntry {
  command_id: string;
  purpose: string;
  owning_stage: StageId;
  executable: string;
  fixed_args: string[];
  working_directory_rule: "bundle_root" | "repo_root" | "service_root";
  allowed_path_inputs: string[];
  mutation_classification: "read-only" | "local-write" | "external-mutation";
  required_confirmation: boolean;
  credential_requirements: string[];
  output_summary_policy: string;
}

export interface CommandRegistry {
  schema_id: string;
  schema_version: string;
  commands: CommandRegistryEntry[];
}
