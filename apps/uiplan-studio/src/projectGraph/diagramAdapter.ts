import type { DiagramData, DiagramEdge, DiagramNode } from "../types";
import type {
  ProjectGraph,
  ProjectGraphEdge,
  ProjectGraphNode,
  ProjectGraphNodeKind,
} from "./types";

const STARTER_NODE_ALIASES: Record<string, string> = {
  chat_trigger: "spec",
  planning_agent: "plan",
  if_ready: "review",
};

const STARTER_NODE_TITLES: Record<string, string> = {
  spec: "Chat Trigger",
  plan: "Workflow Plan",
  review: "Ready?",
};

const STARTER_NODE_SOURCES: Record<string, string> = {
  spec: "spec.md",
  plan: "plan.md",
  review: "Phase 0 approval gate",
};

const DEFAULT_DESCRIPTIONS: Record<ProjectGraphNodeKind, string> = {
  process_step: "Starts or shapes the planning flow.",
  project_component: "Generates the reviewed UiPath work package.",
  generated_artifact: "Reviewable output created by the package flow.",
  test: "Validates generated behavior before handoff.",
  tool: "Local or MCP capability used by generation.",
  asset: "Runtime configuration or Orchestrator resource.",
  queue: "Transaction boundary and retry context.",
  docs_context: "Grounding material for safe generation.",
  skill: "Authoring guidance applied to generated work.",
  deployment_gate: "Build-loop checkpoint before release.",
  review_gate: "Human approval and readiness decision.",
};

function readString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined;
}

function readPosition(node: ProjectGraphNode): { x: number; y: number } {
  const positionHint = node.metadata.positionHint;
  if (
    typeof positionHint === "object" &&
    positionHint !== null &&
    "x" in positionHint &&
    "y" in positionHint
  ) {
    const { x, y } = positionHint as { x?: unknown; y?: unknown };
    return {
      x: typeof x === "number" ? x + 56 : 56,
      y: typeof y === "number" ? y + 150 : 150,
    };
  }
  return { x: 56, y: 150 };
}

function mapNodeId(nodeId: string): string {
  return STARTER_NODE_ALIASES[nodeId] ?? nodeId;
}

function mapNodeKind(kind: ProjectGraphNodeKind): DiagramNode["kind"] {
  switch (kind) {
    case "generated_artifact":
      return "document";
    case "docs_context":
      return "library";
    case "skill":
      return "skill";
    case "review_gate":
    case "deployment_gate":
      return "review";
    default:
      return "workflow";
  }
}

function mapOutputType(kind: ProjectGraphNodeKind): DiagramNode["output_type"] {
  switch (kind) {
    case "generated_artifact":
      return "document";
    case "docs_context":
      return "none";
    case "review_gate":
    case "deployment_gate":
      return "approval_gate";
    case "test":
      return "test_file";
    case "asset":
    case "queue":
      return "orchestrator_resource";
    case "tool":
    case "skill":
      return "config";
    default:
      return "project_scaffold";
  }
}

function mapStatus(node: ProjectGraphNode): DiagramNode["status"] {
  const visualRole = readString(node.metadata.visualRole);
  if (visualRole === "success_branch") return "ready";
  if (visualRole === "fallback_branch") return "needs_context";
  if (visualRole === "decision_branch") return "draft";
  return "draft";
}

function mapBranch(edge: ProjectGraphEdge): DiagramEdge["branch"] {
  const branch = readString(edge.metadata.branch);
  if (branch === "success" || branch === "fallback") return branch;
  if (edge.kind === "uses_context" || edge.kind === "uses_skill") return "context";
  if (edge.kind === "depends_on") return "dependency";
  return undefined;
}

export function projectGraphToDiagramData(graph: ProjectGraph): DiagramData {
  const nodes = graph.nodes.map((node): DiagramNode => {
    const id = mapNodeId(node.id);
    const position = readPosition(node);
    const visualRole = readString(node.metadata.visualRole);
    return {
      id,
      title: STARTER_NODE_TITLES[id] ?? node.label,
      kind: mapNodeKind(node.kind),
      description: readString(node.metadata.description) ?? DEFAULT_DESCRIPTIONS[node.kind],
      x: position.x,
      y: position.y,
      source: STARTER_NODE_SOURCES[id] ?? readString(node.metadata.source),
      role: node.kind,
      output_type: mapOutputType(node.kind),
      project_types: [graph.projectType],
      context_policy:
        node.kind === "docs_context" || node.kind === "skill" || node.kind === "tool"
          ? "strict"
          : "advisory",
      layer: node.layer,
      icon_hint: readString(node.metadata.iconHint),
      visual_role: visualRole,
      status: mapStatus(node),
      metadata: {
        ...node.metadata,
        projectGraphNodeId: node.id,
        projectGraphKind: node.kind,
      },
    };
  });

  const edges = graph.edges.map((edge): DiagramEdge => ({
    id: edge.id,
    from: mapNodeId(edge.source),
    to: mapNodeId(edge.target),
    label: edge.label ?? edge.kind,
    edge_type: edge.kind,
    branch: mapBranch(edge),
    metadata: {
      ...edge.metadata,
      projectGraphEdgeId: edge.id,
    },
  }));

  return { nodes, edges };
}
