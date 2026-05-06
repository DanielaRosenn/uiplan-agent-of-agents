import type { DiagramData, DiagramEdge, DiagramNode } from "./types";

const DEFAULT_PROJECT_TYPES = ["docs"] as const;

type GenerationNodeRole =
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

type GenerationOutputType =
  | "none"
  | "document"
  | "project_scaffold"
  | "source_file"
  | "test_file"
  | "config"
  | "orchestrator_resource"
  | "validation_report"
  | "approval_gate";

type GenerationEdgeType =
  | "drives"
  | "generates"
  | "depends_on"
  | "uses_context"
  | "uses_skill"
  | "validates"
  | "blocks"
  | "deploys"
  | "observes"
  | "documents";

type ContextAttachmentPolicy = "strict" | "advisory";
type ContextAttachmentSourceKind =
  | "repo_doc"
  | "library_book"
  | "skill"
  | "tool"
  | "source_file"
  | "user_note"
  | "validation_output";

interface GenerationGraphContextAttachment {
  source_kind: ContextAttachmentSourceKind;
  source_id: string;
  citation: string | null;
  scope: "node";
  policy: ContextAttachmentPolicy;
  summary: string;
}

interface GenerationGraphNodePayload {
  id: string;
  title: string;
  role: GenerationNodeRole;
  output_type: GenerationOutputType;
  project_types: string[];
  description: string;
  x: number;
  y: number;
  source: string | null;
  context_attachment_ids: string[];
}

interface GenerationGraphEdgePayload {
  id: string;
  from: string;
  to: string;
  edge_type: GenerationEdgeType;
  label: string;
}

export interface GenerationGraphPayload {
  graph_id: string;
  bundle_root: string;
  created_from: "uiplan-studio";
  nodes: GenerationGraphNodePayload[];
  edges: GenerationGraphEdgePayload[];
  context_attachments: GenerationGraphContextAttachment[];
  generation_profile: {
    allowed_project_types: string[];
  };
}

function mapNodeRole(kind: DiagramNode["kind"]): GenerationNodeRole {
  switch (kind) {
    case "document":
      return "generated_artifact";
    case "workflow":
      return "process_step";
    case "skill":
      return "skill";
    case "library":
      return "docs_context";
    case "review":
      return "review_gate";
    default:
      return "process_step";
  }
}

function mapOutputType(kind: DiagramNode["kind"]): GenerationOutputType {
  switch (kind) {
    case "document":
      return "document";
    case "review":
      return "approval_gate";
    default:
      return "project_scaffold";
  }
}

function mapEdgeType(edge: DiagramEdge): GenerationEdgeType {
  if (isGenerationEdgeType(edge.edge_type)) {
    return edge.edge_type;
  }
  const normalized = edge.label.trim().toLowerCase();
  if (normalized.includes("valid")) return "validates";
  if (normalized.includes("block")) return "blocks";
  if (normalized.includes("deploy")) return "deploys";
  if (normalized.includes("generate")) return "generates";
  if (normalized.includes("depend")) return "depends_on";
  if (normalized.includes("skill") || normalized.includes("guide")) return "uses_skill";
  if (normalized.includes("context") || normalized.includes("ground")) return "uses_context";
  if (normalized.includes("document")) return "documents";
  if (normalized.includes("observe")) return "observes";
  return "drives";
}

function isGenerationEdgeType(value: unknown): value is GenerationEdgeType {
  return (
    value === "drives" ||
    value === "generates" ||
    value === "depends_on" ||
    value === "uses_context" ||
    value === "uses_skill" ||
    value === "validates" ||
    value === "blocks" ||
    value === "deploys" ||
    value === "observes" ||
    value === "documents"
  );
}

function isContextAttachmentPolicy(value: unknown): value is ContextAttachmentPolicy {
  return value === "strict" || value === "advisory";
}

function isContextAttachmentSourceKind(value: unknown): value is ContextAttachmentSourceKind {
  return (
    value === "repo_doc" ||
    value === "library_book" ||
    value === "skill" ||
    value === "tool" ||
    value === "source_file" ||
    value === "user_note" ||
    value === "validation_output"
  );
}

function stableHash(value: string): string {
  let hash = 5381;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 33) ^ value.charCodeAt(index);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function sourceKindForNode(node: DiagramNode): ContextAttachmentSourceKind {
  if (node.kind === "library") return "library_book";
  if (node.kind === "skill") return "skill";
  if (node.role === "tool") return "tool";
  if (node.source?.endsWith(".md")) return "repo_doc";
  if (node.source) return "source_file";
  return "user_note";
}

function contextAttachmentKey(attachment: GenerationGraphContextAttachment): string {
  return JSON.stringify({
    source_kind: attachment.source_kind,
    source_id: attachment.source_id,
    citation: attachment.citation,
    scope: attachment.scope,
    policy: attachment.policy,
    summary: attachment.summary,
  });
}

function contextAttachmentRefs(attachment: GenerationGraphContextAttachment): string[] {
  return [attachment.source_id, attachment.citation]
    .filter((value): value is string => typeof value === "string" && value.trim().length > 0)
    .filter((value, index, values) => values.indexOf(value) === index);
}

function normalizeMetadataContextAttachments(node: DiagramNode): GenerationGraphContextAttachment[] {
  const rawAttachments = node.metadata?.context_attachments ?? node.metadata?.contextAttachments;
  const attachments = Array.isArray(rawAttachments) ? rawAttachments : [];
  return attachments
    .map((attachment, index) => {
      if (typeof attachment !== "object" || attachment == null) {
        return null;
      }
      const raw = attachment as Record<string, unknown>;
      const sourceId =
        typeof raw.source_id === "string"
          ? raw.source_id
          : typeof raw.sourceId === "string"
            ? raw.sourceId
            : node.source ?? `${node.id}:metadata:${index}`;
      const citation =
        typeof raw.citation === "string" && raw.citation.trim()
          ? raw.citation
          : node.strict_citation ?? node.source ?? sourceId;
      const policy = isContextAttachmentPolicy(raw.policy) ? raw.policy : node.context_policy ?? "advisory";
      const sourceKind = isContextAttachmentSourceKind(raw.source_kind)
        ? raw.source_kind
        : isContextAttachmentSourceKind(raw.sourceKind)
          ? raw.sourceKind
          : sourceKindForNode(node);
      const summary =
        typeof raw.summary === "string" && raw.summary.trim()
          ? raw.summary
          : `Context for ${node.title}`;
      return {
        source_kind: sourceKind,
        source_id: sourceId,
        citation,
        scope: "node" as const,
        policy,
        summary,
      };
    })
    .filter((attachment): attachment is GenerationGraphContextAttachment => attachment != null);
}

function createImplicitContextAttachment(node: DiagramNode): GenerationGraphContextAttachment | null {
  if (!node.context_policy && !node.strict_citation && !node.source) {
    return null;
  }

  const sourceId = node.source ?? node.strict_citation ?? node.id;
  const citation = node.strict_citation ?? node.source ?? sourceId;
  return {
    source_kind: sourceKindForNode(node),
    source_id: sourceId,
    citation,
    scope: "node",
    policy: node.context_policy ?? "advisory",
    summary: node.strict_citation
      ? `Strict context for ${node.title}`
      : `Source context for ${node.title}`,
  };
}

function collectNodeContextAttachments(node: DiagramNode): GenerationGraphContextAttachment[] {
  const attachments = normalizeMetadataContextAttachments(node);
  const implicitAttachment = createImplicitContextAttachment(node);
  if (implicitAttachment) {
    attachments.push(implicitAttachment);
  }
  const byKey = new Map<string, GenerationGraphContextAttachment>();
  attachments.forEach((attachment) => byKey.set(contextAttachmentKey(attachment), attachment));
  return [...byKey.values()].sort((left, right) =>
    contextAttachmentKey(left).localeCompare(contextAttachmentKey(right)),
  );
}

export function toGenerationGraphPayload(bundleRoot: string, graph: DiagramData): GenerationGraphPayload {
  const attachmentsByNodeId = new Map<string, GenerationGraphContextAttachment[]>();
  graph.nodes.forEach((node) => {
    attachmentsByNodeId.set(node.id, collectNodeContextAttachments(node));
  });
  const nodes = graph.nodes
    .slice()
    .sort((left, right) => left.id.localeCompare(right.id))
    .map((node) => ({
      id: node.id,
      title: node.title,
      role: node.role ?? mapNodeRole(node.kind),
      output_type: node.output_type ?? mapOutputType(node.kind),
      project_types: node.project_types?.length ? [...node.project_types] : [...DEFAULT_PROJECT_TYPES],
      description: node.description,
      x: node.x,
      y: node.y,
      source: node.source ?? null,
      context_attachment_ids:
        attachmentsByNodeId.get(node.id)?.flatMap(contextAttachmentRefs) ?? [],
    }));
  const edges = graph.edges
    .slice()
    .sort((left, right) => left.id.localeCompare(right.id))
    .map((edge) => ({
      id: edge.id,
      from: edge.from,
      to: edge.to,
      edge_type: mapEdgeType(edge),
      label: edge.label,
    }));
  const contextAttachments = [...attachmentsByNodeId.values()]
    .flat()
    .sort((left, right) => contextAttachmentKey(left).localeCompare(contextAttachmentKey(right)));
  const graphId = `graph-${stableHash(
    JSON.stringify({
      bundle_root: bundleRoot,
      nodes,
      edges,
      context_attachments: contextAttachments,
    }),
  )}`;
  return {
    graph_id: graphId,
    bundle_root: bundleRoot,
    created_from: "uiplan-studio",
    nodes,
    edges,
    context_attachments: contextAttachments,
    generation_profile: {
      allowed_project_types: [...DEFAULT_PROJECT_TYPES],
    },
  };
}
