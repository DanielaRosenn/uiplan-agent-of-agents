import type { DocCitation, ProjectGraph, SkillRef, Worktree } from "./types";
import { sampleGraph } from "../__fixtures__/sample";
import { sampleEmptyGraph, sampleSolutionGraph } from "../__fixtures__/sampleSolution";

const API_BASE = (import.meta.env?.VITE_UIPLAN_API_URL as string | undefined)?.replace(/\/$/, "")
  ?? "http://localhost:8000";

const FETCH_TIMEOUT_MS = 4000;

const SAMPLE_FIXTURES: Record<string, ProjectGraph> = {
  demo: sampleGraph,
  solution: sampleSolutionGraph,
  empty: sampleEmptyGraph,
};

const SAMPLE_WORKTREES: Worktree[] = [
  { id: "demo",     label: "Demo · renewal commitment", path: "(in-memory)", branch: "main",            project_type: "mixed" },
  { id: "solution", label: "Solution · order-to-cash",  path: "(in-memory)", branch: "feat/q3-solution", project_type: "solution" },
  { id: "empty",    label: "Empty worktree",            path: "(in-memory)", branch: "—",                 project_type: "—" },
];

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

/**
 * Load a project graph for the given worktree id.
 *
 * Fixture worktrees (demo / solution / empty) always resolve to the bundled
 * sample. Other ids are passed through to `/explorer/graph?worktree=…`; on
 * any failure (timeout, non-2xx, malformed) we fall back to the demo sample
 * so the UI never has to render an empty error screen.
 */
export async function loadProjectGraph(worktreeId: string): Promise<LoadGraphResult> {
  if (worktreeId in SAMPLE_FIXTURES) {
    return { graph: SAMPLE_FIXTURES[worktreeId], source: "sample" };
  }
  try {
    const res = await fetchWithTimeout(
      `${API_BASE}/explorer/graph?worktree=${encodeURIComponent(worktreeId)}`,
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
