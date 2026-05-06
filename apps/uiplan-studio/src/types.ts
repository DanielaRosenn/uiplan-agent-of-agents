export type DocumentName = "spec.md" | "plan.md" | "tasks.md";

export type DiagramNodeKind = "document" | "workflow" | "skill" | "library" | "review";
export type DiagramNodeRole =
  | "process_step"
  | "project_component"
  | "generated_artifact"
  | "test"
  | "tool"
  | "asset"
  | "queue"
  | "docs_context"
  | "skill"
  | "deployment_gate"
  | "review_gate";
export type DiagramOutputType =
  | "none"
  | "document"
  | "project_scaffold"
  | "source_file"
  | "test_file"
  | "config"
  | "orchestrator_resource"
  | "validation_report"
  | "approval_gate";
export type DiagramProjectType =
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
export type ContextPolicy = "strict" | "advisory";

export interface DiagramNode {
  id: string;
  title: string;
  kind: DiagramNodeKind;
  description: string;
  x: number;
  y: number;
  source?: string;
  role?: DiagramNodeRole;
  output_type?: DiagramOutputType;
  project_types?: DiagramProjectType[];
  context_policy?: ContextPolicy;
  strict_citation?: string;
  layer?: string;
  icon_hint?: string;
  visual_role?: string;
  status?: "ready" | "needs_context" | "blocked" | "draft" | "approved";
  metadata?: Record<string, unknown>;
}

export interface DiagramEdge {
  id: string;
  from: string;
  to: string;
  label: string;
  edge_type?: string;
  branch?: "success" | "fallback" | "dependency" | "context";
  metadata?: Record<string, unknown>;
}

export interface DiagramData {
  nodes: DiagramNode[];
  edges: DiagramEdge[];
}

export interface BundleData {
  slug: string;
  status: string;
  root: string;
  documents: Record<DocumentName, string>;
}

export interface Finding {
  rule?: string;
  severity?: string;
  message?: string;
  document?: string;
}

export interface ReviewResponse {
  findings: Finding[];
  findings_by_document?: Record<string, Finding[]>;
  acceptance_ready?: boolean;
}

export interface LifecycleReadinessResponse {
  status: "ready" | "blocked";
  acceptance_ready: boolean;
  error_count: number;
  findings_by_document?: Record<string, Finding[]>;
}

export interface SectionPreviewResponse {
  preview_id: string;
  proposed_content: string;
  diff: string;
}

export interface LibraryContextItem {
  book_id: string;
  chapter_id: string;
  section_id: string;
  score: number;
  snippet: string;
  full_text?: string | null;
}

export interface LibraryContextResponse {
  query: string;
  items: LibraryContextItem[];
}

export interface ContextSource {
  id: string;
  title: string;
  kind: DiagramNodeKind;
  category: string;
  description: string;
  source: string;
  available: boolean;
}

export interface ContextSourceCategory {
  id: string;
  title: string;
  description: string;
  sources: ContextSource[];
}

export interface ContextSourcesResponse {
  categories: ContextSourceCategory[];
}

export interface AssistantMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AssistantChatResponse {
  message: string;
  suggested_nodes: DiagramNode[];
}
