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

export type EdgeKind =
  | "import"
  | "call"
  | "invokes"
  | "transition"
  | "bridge"
  | "queue"
  | "publish"
  | "data"
  | "covers";

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
