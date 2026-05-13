export type LayerKey =
  | "ui"
  | "api"
  | "agent"
  | "rpa"
  | "maestro"
  | "app"
  | "orchestrator"
  | "test"
  | "external"
  | "skills"
  | "uiplan";

/** Aggregate progress for a UiPlan tasks.md file or bundle. */
export interface TaskSummary {
  total: number;
  done: number;
  pending: number;
  in_progress: number;
  cancelled: number;
}

// ---------------------------------------------------------------------------
// AS-IS / TO-BE View Types
// ---------------------------------------------------------------------------

export interface SourceLink {
  path: string;
  anchor?: string;
  line?: number;
}

export interface PainPoint {
  label: string;
  description: string;
  related_handoff_ids?: string[];
}

export interface Handoff {
  id: string;
  from_actor: string;
  to_actor: string;
  channel: string;  // email | phone | excel | paper | meeting
  artifact: string;
  sla: string;
  pain: string;
  sequence: number;
  docs_path?: string;
}

export interface AsIsView {
  swimlanes: string[];
  handoffs: Handoff[];
  pain_points: PainPoint[];
  sources: SourceLink[];
}

export interface ToBeWorkflow {
  id: string;
  label: string;
  path?: string;
  planned_artifact?: string;
  artifact_type?: string;
  inputs?: string[];
  outputs?: string[];
  contracts?: string[];
  dependencies?: string[];
  readiness?: string;
  blockers?: string[];
  validator_roles?: string[];
  bucket: string;  // intake | processing | review | evidence
  internal_steps: Array<{id: string; label: string; shape: string}>;
  drill_docs_path?: string;
}

export interface ToBeIntegration {
  id: string;
  label: string;
  system: string;
  used_by_workflow_ids: string[];
  drill_docs_path?: string;
}

export interface ToBeOrchResource {
  id: string;
  label: string;
  resource_type: string;
  used_by_workflow_ids: string[];
  drill_docs_path?: string;
}

export interface ToBeHitl {
  id: string;
  label: string;
  channel: string;  // Action Center | Maestro | Slack | Custom
  actor: string;
  callback_contract: string;
  drill_docs_path?: string;
}

export interface ToBeBucket {
  id: string;
  label: string;
  bucket_type: string;  // triggers | intake | processing | integrations | hitl | evidence
  node_ids: string[];
}

export interface SequenceStep {
  from_participant: string;
  to_participant: string;
  label: string;
  sequence: number;
  is_return: boolean;
}

export interface ToBeView {
  buckets: ToBeBucket[];
  workflows: ToBeWorkflow[];
  integrations: ToBeIntegration[];
  orchestrator: ToBeOrchResource[];
  hitl: ToBeHitl[];
  runtime_sequence: SequenceStep[];
  sources: SourceLink[];
}

// ---------------------------------------------------------------------------

export type EdgeKind =
  | "import"
  | "call"
  | "invokes"
  | "transition"
  | "bridge"
  | "queue"
  | "publish"
  | "data"
  | "covers"
  | "uses"
  | "conditional";  // Conditional branch (If/Else)

/** "Which path of the process this edge belongs to" — drives BA path filter. */
export type PathClass = "happy" | "exception" | "loopback" | "alt";

/** Technical health of a node. */
export type NodeStatus = "ok" | "warn" | "error" | "stale" | "draft";

/** Lifecycle status a BA cares about — independent of technical health. */
export type BusinessStatus = "drafted" | "approved" | "in-build" | "live" | "retired";

export type NodeRole =
  | "hitl"
  | "approval"
  | "entrypoint"
  | "exit"
  | "test"
  | "deprecated"
  | "trigger"
  | "actor";

export interface ProjectCode {
  path: string;
  lines: string;
  snippet: string;
  language?: string;
}

export interface SkillRef {
  /** Skill id (e.g. "uipath-rpa", "uipath-agents"). Matches `uipath_skill_get` names. */
  id: string;
  /** Path inside the repo or skills submodule. */
  path: string;
  /** Why this skill applies to this node. */
  reason?: string;
  /** Optional origin: which submodule layer the skill came from. */
  origin?: string;
  score?: number;
  tags?: string[];
  triggers?: string[];
}

export interface DocCitation {
  book_id: string;
  chapter_id: string;
  section_id: string;
  snippet: string;
  /** Optional ranking score (higher = better). */
  score?: number;
  /** Optional URL or library href. */
  href?: string;
}

/** Anchor pointing back to the PDD/SDD/ADD that authorised this node. */
export interface PddAnchor {
  /** Document id, e.g. "PDD-ALPHA-01". */
  doc_id: string;
  /** Section heading anchor. */
  section: string;
  /** Optional relative path to the source document. */
  path?: string;
}

/**
 * Numbers a BA actually asks about: volume, SLA, business value.
 * All optional — present only on the nodes a BA marked up.
 */
export interface BusinessMeta {
  /** "How much of this happens?" — units per unit-of-time, e.g. "120 / day". */
  volume?: string;
  /** Service-level objective. */
  sla?: string;
  /** Business owner / sponsor. */
  owner?: string;
  /** Free-form business value note. */
  value?: string;
  /** Stakeholders this node serves. */
  consumers?: string[];
  /** Risk classification. */
  risk?: "low" | "medium" | "high";
}

export interface ProjectNodeBase {
  id: string;
  label: string;
  /** Semantic kind: file, function, agent_node, workflow, activity, endpoint, module, tool,
   *  flow, case, coded_app, action_app, queue, asset, process, folder, entity, test_case, test_set, ... */
  kind: string;
  layer: LayerKey | string;
  desc?: string;
  /** Long-form explanation. */
  concept?: string;
  code?: ProjectCode;
  meta?: Record<string, string | number | boolean>;
  /** Technical status — drives the colored pip on the canvas. */
  status?: NodeStatus;
  /** Lifecycle status — what a BA tracks. */
  business_status?: BusinessStatus;
  /** Special roles: HITL pause point, entrypoint, actor, trigger, etc. */
  roles?: NodeRole[];
  /** Library citations relevant to this node. */
  citations?: DocCitation[];
  /** Skills that govern how this node should be authored/reviewed. */
  skills?: SkillRef[];
  /** Anchor back to PDD/SDD/ADD section. */
  pdd_anchor?: PddAnchor;
  /** Business numbers. */
  business_meta?: BusinessMeta;
  /** Aggregate task progress (only on UiPlan tasks.md / bundle nodes). */
  task_summary?: TaskSummary;
  
  // Business logic visualization properties
  /** True if this node is a container (TaskNode, ProcessDiagram) that holds other nodes. */
  is_container?: boolean;
  /** True if this node is an activity inside a TaskNode. */
  is_activity?: boolean;
  /** True if this node is an entry point to the workflow. */
  is_entry?: boolean;
  /** Type of control flow structure (if, switch, foreach, parallel). */
  control_flow_type?: "if" | "switch" | "foreach" | "parallel";
  /** Parent TaskNode ID if this is an activity. */
  parent_task_node?: string;
  /** Business logic hierarchy level. */
  business_logic_level?: "entry" | "process" | "activity" | "integration";
  /** Activity type for activity nodes (InvokeWorkflowFile, Assign, etc.). */
  activity_type?: string;
  /** Condition expression for control flow nodes. */
  condition?: string;
  /** Workflow file reference for InvokeWorkflowFile activities. */
  workflow_file?: string;
}

export interface ProjectChildNode extends ProjectNodeBase {
  children?: ProjectSubGraph;
}

export interface ProjectNode extends ProjectNodeBase {
  children?: ProjectSubGraph;
}

export interface ProjectEdge {
  id: string;
  source: string;
  target: string;
  kind: EdgeKind | string;
  label?: string;
  desc?: string;
  /** Which process path this edge belongs to. Drives the BA path filter. */
  path_class?: PathClass;
  /** Optional payload schema reference (e.g. zod schema name, pydantic class). */
  payload_schema?: string;
  /** Citations explaining or documenting this edge. */
  citations?: DocCitation[];
}

export interface ProjectSubGraph {
  nodes: ProjectChildNode[];
  edges: ProjectEdge[];
}

export interface ProjectError {
  nodeId: string;
  severity: "error" | "warn" | "info";
  message: string;
}

/** Project-level overview a BA reads before diving in. */
export interface ProjectOverview {
  /** Plain-English process name. */
  name: string;
  /** What the process actually does, two-three sentences. */
  summary: string;
  /** Business owner / sponsor. */
  owner?: string;
  /** Stakeholder groups. */
  stakeholders?: string[];
  /** Triggers: scheduled, queue, http, manual, event. */
  triggers?: { kind: string; description: string }[];
  /** External actors / systems involved. */
  actors?: { name: string; role: string }[];
  /** Headline business numbers. */
  kpis?: { label: string; value: string }[];
  /** Where the PDD lives. */
  pdd?: PddAnchor;
}

export interface ProjectGraphMeta {
  worktree_id?: string;
  branch?: string;
  revision?: string;
  indexed_at?: string;
  /** Project type per CLAUDE.md §1: rpa, coded-agent, langgraph, maestro-flow, solution, mixed... */
  project_type?: string;
}

export interface ProjectGraph {
  projectType: string;
  /** BA-facing project overview. Optional but recommended. */
  overview?: ProjectOverview;
  nodes: ProjectNode[];
  edges: ProjectEdge[];
  errors?: ProjectError[];
  meta?: ProjectGraphMeta;
}

export interface Worktree {
  id: string;
  label: string;
  path: string;
  branch?: string;
  project_type?: string;
}
