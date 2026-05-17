import type {
  AgentOpsDemoRun,
  DocCitation,
  ProjectGraph,
  SkillRef,
  Worktree,
} from "./types";
import { sampleGraph } from "../__fixtures__/sample";

const API_BASE = (import.meta.env?.VITE_UIPLAN_API_URL as string | undefined)?.replace(/\/$/, "")
  ?? "http://localhost:8000";

const FETCH_TIMEOUT_MS = 60000;

// Single demo fixture for fallback/testing only
const SAMPLE_FIXTURES: Record<string, ProjectGraph> = {
  demo: sampleGraph,
};

export interface DemoIntake {
  businessGoal: string;
  industry?: string;
  systems?: string[];
  constraints?: string[];
  successCriteria?: string[];
}

const FALLBACK_AGENTOPS_DEMO_RUN: AgentOpsDemoRun = {
  orchestrator_state: {
    current_phase: "Verification",
    status: "in_progress",
    active_workflow: "InvoiceExceptionOrchestrator",
    blocked: true,
  },
  specialist_assignments: [
    { agent: "discovery-agent", role: "Intake analysis", status: "done" },
    { agent: "solution-architect-agent", role: "TO-BE design", status: "done" },
    { agent: "builder-orchestrator", role: "Template clone + deltas", status: "in_progress" },
    { agent: "verifier-agent", role: "Gate verification", status: "pending" },
  ],
  as_is_view_model: {
    swimlanes: ["Finance analyst", "Approver", "Automation operator"],
    handoffs: [
      {
        id: "as-is-1",
        from_actor: "Finance analyst",
        to_actor: "Approver",
        channel: "email",
        artifact: "Invoice exception packet",
        sla: "4h",
        pain: "Manual follow-up and missing context",
        sequence: 1,
      },
    ],
    pain_points: [
      {
        label: "Manual triage",
        description: "Exception requests are routed manually across teams.",
        related_handoff_ids: ["as-is-1"],
      },
    ],
    sources: [{ path: "samples/invoice-exception/intake.json", anchor: "businessGoal" }],
  },
  to_be_view_model: {
    buckets: [
      { id: "bucket-intake", label: "Intake", bucket_type: "intake", node_ids: ["wf-intake"] },
      { id: "bucket-processing", label: "Processing", bucket_type: "processing", node_ids: ["wf-routing"] },
    ],
    workflows: [
      {
        id: "wf-intake",
        label: "Normalize exception intake",
        bucket: "intake",
        internal_steps: [{ id: "step-1", label: "Parse input", shape: "activity" }],
      },
    ],
    integrations: [],
    orchestrator: [],
    hitl: [],
    runtime_sequence: [],
    sources: [{ path: "samples/invoice-exception/intake.json", anchor: "successCriteria" }],
  },
  build_queue: [
    { id: "queue-1", title: "Clone base Studio template", status: "done", phase: "Build" },
    { id: "queue-2", title: "Apply generated workflows", status: "in_progress", phase: "Build" },
  ],
  verification_checklist: [
    { gate: "AS-IS captured", status: "passed", owner: "discovery-agent" },
    { gate: "TO-BE mapped", status: "passed", owner: "solution-architect-agent" },
    { gate: "Tests green", status: "pending", owner: "verifier-agent" },
  ],
  deployment_readiness_status: {
    status: "blocked",
    deployed: false,
    blocker: "Verification gates are still pending.",
    target: "personal-workspace",
  },
  handoff_summary: {
    summary: "Template clone completed. Generated deltas are ready for verification.",
    next_action: "Complete verification gates and package deployment evidence.",
    owner: "builder-orchestrator",
  },
};

const FALLBACK_DEMO_INTAKE: DemoIntake = {
  businessGoal: "Use an agent-of-agents orchestration flow to generate invoice exception automation via template-first Studio project creation.",
  industry: "Finance operations",
  systems: ["Email inbox", "ERP", "UiPath Action Center", "Orchestrator queue"],
  constraints: [
    "No production deployment",
    "Human approval before deploy",
    "Evidence required for every automation artifact",
  ],
  successCriteria: [
    "Generate AS-IS and TO-BE process views",
    "Assign specialist agents",
    "Clone the selected base template into a working project",
    "Apply generated changes on top of the cloned project",
    "Run verification gates",
    "Produce deployment handoff evidence",
  ],
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : null;
}

function asString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function normalizeAgentOpsDemoRun(value: unknown): AgentOpsDemoRun | null {
  const root = asRecord(value);
  if (!root) return null;

  const orchestratorState = asRecord(root.orchestrator_state);
  const asIsView = asRecord(root.as_is_view_model);
  const toBeView = asRecord(root.to_be_view_model);
  const deployment = asRecord(root.deployment_readiness_status);
  const handoffSummary = asRecord(root.handoff_summary);

  const assignments = Array.isArray(root.specialist_assignments)
    ? root.specialist_assignments
        .map((item) => {
          const record = asRecord(item);
          if (!record) return null;
          const agent = asString(record.agent);
          const role = asString(record.role);
          const status = asString(record.status);
          return agent && role && status ? { agent, role, status } : null;
        })
        .filter((item): item is AgentOpsDemoRun["specialist_assignments"][number] => item !== null)
    : [];

  const buildQueue = Array.isArray(root.build_queue)
    ? root.build_queue
        .map((item) => {
          const record = asRecord(item);
          if (!record) return null;
          const id = asString(record.id);
          const title = asString(record.title);
          const status = asString(record.status);
          const phase = asString(record.phase) ?? undefined;
          return id && title && status ? { id, title, status, phase } : null;
        })
        .filter((item): item is AgentOpsDemoRun["build_queue"][number] => item !== null)
    : [];

  const verificationChecklist = Array.isArray(root.verification_checklist)
    ? root.verification_checklist
        .map((item) => {
          const record = asRecord(item);
          if (!record) return null;
          const gate = asString(record.gate);
          const status = asString(record.status);
          const owner = asString(record.owner) ?? undefined;
          return gate && status ? { gate, status, owner } : null;
        })
        .filter((item): item is AgentOpsDemoRun["verification_checklist"][number] => item !== null)
    : [];

  if (
    !orchestratorState ||
    !asIsView ||
    !toBeView ||
    !deployment ||
    !handoffSummary ||
    !asString(orchestratorState.current_phase) ||
    !asString(orchestratorState.status) ||
    typeof deployment.deployed !== "boolean" ||
    !asString(deployment.status) ||
    !asString(handoffSummary.summary) ||
    assignments.length === 0 ||
    buildQueue.length === 0 ||
    verificationChecklist.length === 0
  ) {
    return null;
  }

  return {
    orchestrator_state: {
      current_phase: asString(orchestratorState.current_phase) ?? "Verification",
      status: asString(orchestratorState.status) ?? "in_progress",
      active_workflow: asString(orchestratorState.active_workflow) ?? undefined,
      blocked: typeof orchestratorState.blocked === "boolean" ? orchestratorState.blocked : undefined,
    },
    specialist_assignments: assignments,
    as_is_view_model: {
      swimlanes: asStringArray(asIsView.swimlanes),
      handoffs: Array.isArray(asIsView.handoffs)
        ? (asIsView.handoffs as AgentOpsDemoRun["as_is_view_model"]["handoffs"])
        : [],
      pain_points: Array.isArray(asIsView.pain_points)
        ? (asIsView.pain_points as AgentOpsDemoRun["as_is_view_model"]["pain_points"])
        : [],
      sources: Array.isArray(asIsView.sources)
        ? (asIsView.sources as AgentOpsDemoRun["as_is_view_model"]["sources"])
        : [],
    },
    to_be_view_model: {
      buckets: Array.isArray(toBeView.buckets)
        ? (toBeView.buckets as AgentOpsDemoRun["to_be_view_model"]["buckets"])
        : [],
      workflows: Array.isArray(toBeView.workflows)
        ? (toBeView.workflows as AgentOpsDemoRun["to_be_view_model"]["workflows"])
        : [],
      integrations: Array.isArray(toBeView.integrations)
        ? (toBeView.integrations as AgentOpsDemoRun["to_be_view_model"]["integrations"])
        : [],
      orchestrator: Array.isArray(toBeView.orchestrator)
        ? (toBeView.orchestrator as AgentOpsDemoRun["to_be_view_model"]["orchestrator"])
        : [],
      hitl: Array.isArray(toBeView.hitl) ? (toBeView.hitl as AgentOpsDemoRun["to_be_view_model"]["hitl"]) : [],
      runtime_sequence: Array.isArray(toBeView.runtime_sequence)
        ? (toBeView.runtime_sequence as AgentOpsDemoRun["to_be_view_model"]["runtime_sequence"])
        : [],
      sources: Array.isArray(toBeView.sources)
        ? (toBeView.sources as AgentOpsDemoRun["to_be_view_model"]["sources"])
        : [],
    },
    build_queue: buildQueue,
    verification_checklist: verificationChecklist,
    deployment_readiness_status: {
      status: asString(deployment.status) ?? "blocked",
      deployed: deployment.deployed as boolean,
      blocker: asString(deployment.blocker) ?? undefined,
      target: asString(deployment.target) ?? undefined,
    },
    handoff_summary: {
      summary: asString(handoffSummary.summary) ?? "Handoff summary pending",
      next_action: asString(handoffSummary.next_action) ?? undefined,
      owner: asString(handoffSummary.owner) ?? undefined,
    },
  };
}

async function fetchWithTimeout(url: string, init?: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

export interface LoadGraphResult {
  graph: ProjectGraph;
  source: "api" | "sample";
  error?: string;
}

export interface RefreshState {
  worktree_id: string;
  stamp: string | null;
  source_count: number;
}

/**
 * Load a project graph for the given worktree id.
 *
 * Fixture worktrees (demo / solution / empty) always resolve to the bundled
 * sample. Other ids are passed through to `/explorer/graph?worktree=…`; on
 * any failure (timeout, non-2xx, malformed) we fall back to the demo sample
 * so the UI never has to render an empty error screen.
 */
export async function loadProjectGraph(pathOrId: string): Promise<LoadGraphResult> {
  if (pathOrId in SAMPLE_FIXTURES) {
    return { graph: SAMPLE_FIXTURES[pathOrId], source: "sample" };
  }
  
  // Try Copilot-first mapping endpoint first
  try {
    const mapRes = await fetchWithTimeout(
      `${API_BASE}/mapping/map-folder`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: pathOrId }),
      },
    );
    if (mapRes.ok) {
      const body = await mapRes.json();
      const graph: ProjectGraph = {
        projectType: body.meta?.project_type || "unknown",
        nodes: body.nodes || [],
        edges: body.edges || [],
        errors: body.errors || [],
        meta: body.meta,
      };
      return { graph, source: body.source === "copilot" ? "api" : "api" };
    }
  } catch (err) {
    // Fall through to legacy endpoint
  }
  
  // Fallback to legacy explorer/graph endpoint
  try {
    const res = await fetchWithTimeout(
      `${API_BASE}/explorer/graph?worktree=${encodeURIComponent(pathOrId)}`,
    );
    if (!res.ok) {
      return { graph: sampleGraph, source: "sample", error: `HTTP ${res.status}` };
    }
    const body = (await res.json()) as ProjectGraph;
    if (!body || !Array.isArray(body.nodes) || !Array.isArray(body.edges)) {
      return { graph: sampleGraph, source: "sample", error: "Malformed response" };
    }
    return { graph: body, source: "api" };
  } catch (err) {
    return { graph: sampleGraph, source: "sample", error: (err as Error).message };
  }
}

export async function loadDemoIntake(): Promise<{ data: DemoIntake; source: "api" | "fallback"; error?: string }> {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/fixtures/demo/intake`);
    if (!res.ok) {
      return { data: FALLBACK_DEMO_INTAKE, source: "fallback", error: `HTTP ${res.status}` };
    }
    const body = (await res.json()) as Partial<DemoIntake>;
    if (!body || typeof body.businessGoal !== "string") {
      return { data: FALLBACK_DEMO_INTAKE, source: "fallback", error: "Malformed response" };
    }
    return {
      data: {
        businessGoal: body.businessGoal,
        industry: body.industry,
        systems: Array.isArray(body.systems) ? body.systems : [],
        constraints: Array.isArray(body.constraints) ? body.constraints : [],
        successCriteria: Array.isArray(body.successCriteria) ? body.successCriteria : [],
      },
      source: "api",
    };
  } catch (err) {
    return { data: FALLBACK_DEMO_INTAKE, source: "fallback", error: (err as Error).message };
  }
}

export async function runAgentOpsDemo(
  intake: DemoIntake,
): Promise<{ data: AgentOpsDemoRun; source: "api" | "fallback"; error?: string }> {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/agentops/demo/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(intake),
    });
    if (!res.ok) {
      return { data: FALLBACK_AGENTOPS_DEMO_RUN, source: "fallback", error: `HTTP ${res.status}` };
    }
    const body = await res.json();
    const normalized = normalizeAgentOpsDemoRun(body);
    if (!normalized) {
      return { data: FALLBACK_AGENTOPS_DEMO_RUN, source: "fallback", error: "Malformed response" };
    }
    return { data: normalized, source: "api" };
  } catch (err) {
    return { data: FALLBACK_AGENTOPS_DEMO_RUN, source: "fallback", error: (err as Error).message };
  }
}

export async function loadRefreshState(
  worktreeId: string,
): Promise<{ data: RefreshState | null; source: "api" | "missing"; error?: string }> {
  if (worktreeId in SAMPLE_FIXTURES) {
    return { data: null, source: "missing" };
  }
  try {
    const res = await fetchWithTimeout(
      `${API_BASE}/explorer/refresh-state?worktree=${encodeURIComponent(worktreeId)}`,
    );
    if (!res.ok) {
      return { data: null, source: "missing", error: `HTTP ${res.status}` };
    }
    const body = await res.json();
    if (!body || typeof body.worktree_id !== "string") {
      return { data: null, source: "missing", error: "Malformed response" };
    }
    return {
      data: {
        worktree_id: body.worktree_id,
        stamp: typeof body.stamp === "string" ? body.stamp : null,
        source_count: Number(body.source_count ?? 0),
      },
      source: "api",
    };
  } catch (err) {
    return { data: null, source: "missing", error: (err as Error).message };
  }
}

export interface KnowledgeResponse {
  citations: DocCitation[];
  skills: SkillRef[];
}

/**
 * Fetch live knowledge (library + skills) for a node.
 * Falls back to inline node citations/skills on any failure.
 */
export async function loadNodeKnowledge(
  worktreeId: string,
  nodeId: string,
  query: string,
): Promise<{ data: KnowledgeResponse; source: "api" | "inline"; error?: string }> {
  // Skip the network round-trip for fixture worktrees — they have no live backend.
  if (worktreeId in SAMPLE_FIXTURES) {
    return { data: { citations: [], skills: [] }, source: "inline" };
  }
  try {
    const res = await fetchWithTimeout(
      `${API_BASE}/explorer/knowledge?worktree=${encodeURIComponent(worktreeId)}` +
        `&node=${encodeURIComponent(nodeId)}&q=${encodeURIComponent(query)}`,
    );
    if (!res.ok) {
      return { data: { citations: [], skills: [] }, source: "inline", error: `HTTP ${res.status}` };
    }
    const body = await res.json();
    return {
      data: {
        citations: Array.isArray(body.citations) ? body.citations : [],
        skills: Array.isArray(body.skills) ? body.skills : [],
      },
      source: "api",
    };
  } catch (err) {
    return { data: { citations: [], skills: [] }, source: "inline", error: (err as Error).message };
  }
}

export interface LibrarySectionResponse {
  book_id: string;
  chapter_id: string;
  section_id: string;
  title?: string;
  body: string;
}

export interface SkillDetailResponse {
  id: string;
  description: string;
  path: string;
  origin?: string;
  tags: string[];
  triggers: string[];
  body: string;
}

/** Fetch a single library section's full body (for the in-Inspector reader). */
export async function loadLibrarySection(
  bookId: string, chapterId: string, sectionId: string,
): Promise<{ data: LibrarySectionResponse | null; source: "api" | "missing"; error?: string }> {
  try {
    const res = await fetchWithTimeout(
      `${API_BASE}/explorer/library/section` +
        `?book=${encodeURIComponent(bookId)}` +
        `&chapter=${encodeURIComponent(chapterId)}` +
        `&section=${encodeURIComponent(sectionId)}`,
    );
    if (!res.ok) {
      return { data: null, source: "missing", error: `HTTP ${res.status}` };
    }
    const body = await res.json();
    if (!body || typeof body.body !== "string") {
      return { data: null, source: "missing", error: "Malformed response" };
    }
    return { data: body as LibrarySectionResponse, source: "api" };
  } catch (err) {
    return { data: null, source: "missing", error: (err as Error).message };
  }
}

/** Fetch the full SKILL.md body for an aggregated skill node. */
export async function loadSkillDetail(
  skillId: string,
): Promise<{ data: SkillDetailResponse | null; source: "api" | "missing"; error?: string }> {
  try {
    const res = await fetchWithTimeout(
      `${API_BASE}/explorer/skill?id=${encodeURIComponent(skillId)}`,
    );
    if (!res.ok) {
      return { data: null, source: "missing", error: `HTTP ${res.status}` };
    }
    const body = await res.json();
    if (!body || typeof body.id !== "string") {
      return { data: null, source: "missing", error: "Malformed response" };
    }
    return { data: body as SkillDetailResponse, source: "api" };
  } catch (err) {
    return { data: null, source: "missing", error: (err as Error).message };
  }
}

export async function loadWorktrees(): Promise<{ items: Worktree[]; source: "api" | "sample"; error?: string }> {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/explorer/worktrees`);
    if (!res.ok) {
      return { items: SAMPLE_WORKTREES, source: "sample", error: `HTTP ${res.status}` };
    }
    const body = await res.json();
    if (!Array.isArray(body?.items)) {
      return { items: SAMPLE_WORKTREES, source: "sample", error: "Malformed response" };
    }
    // Always offer the in-memory fixtures alongside whatever the API returned.
    return { items: [...SAMPLE_WORKTREES, ...(body.items as Worktree[])], source: "api" };
  } catch (err) {
    return { items: SAMPLE_WORKTREES, source: "sample", error: (err as Error).message };
  }
}

/**
 * Best-effort "open in editor" — Cursor / VSCode register the `cursor://` URI.
 * Returns the URL we attempted (useful for tests).
 */
export function openInEditor(path: string, line?: number): string {
  const base = `cursor://file/${path.replace(/^\//, "")}`;
  const url = line ? `${base}:${line}` : base;
  if (typeof window !== "undefined") {
    window.location.href = url;
  }
  return url;
}
