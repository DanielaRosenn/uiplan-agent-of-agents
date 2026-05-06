export type ProjectGraphProjectType =
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

export type ProjectGraphNodeKind =
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

export type ProjectGraphEdgeKind =
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

export type ProjectGraphIssueSeverity = "error" | "warning" | "note";
export type ProjectGraphMetadata = Record<string, unknown>;
type OptionalInput<T> = T | null | undefined;

export interface ProjectGraphNode {
  id: string;
  label: string;
  kind: ProjectGraphNodeKind;
  layer?: string;
  metadata: ProjectGraphMetadata;
}

export interface ProjectGraphEdge {
  id: string;
  source: string;
  target: string;
  kind: ProjectGraphEdgeKind;
  label?: string;
  metadata: ProjectGraphMetadata;
}

export interface ProjectGraphCluster {
  id: string;
  label: string;
  nodeIds: string[];
  kind?: string;
  metadata: ProjectGraphMetadata;
}

export interface ProjectGraphIssue {
  id: string;
  message: string;
  severity: ProjectGraphIssueSeverity;
  targetId?: string;
  metadata: ProjectGraphMetadata;
}

export interface ProjectGraph {
  projectType: ProjectGraphProjectType;
  nodes: ProjectGraphNode[];
  edges: ProjectGraphEdge[];
  clusters: ProjectGraphCluster[];
  errors: ProjectGraphIssue[];
}

export interface ProjectGraphAdapterInput {
  projectType: ProjectGraphProjectType;
  source: unknown;
  context?: ProjectGraphMetadata;
}

export interface ProjectGraphAdapterResult {
  graph: ProjectGraph;
  issues: ProjectGraphIssue[];
}

export type ProjectGraphAdapter = (
  input: ProjectGraphAdapterInput,
) => ProjectGraphAdapterResult | Promise<ProjectGraphAdapterResult>;

export interface ProjectGraphNodeInput {
  id: string;
  label: string;
  kind: ProjectGraphNodeKind;
  layer?: OptionalInput<string>;
  metadata?: OptionalInput<ProjectGraphMetadata>;
}

export interface ProjectGraphEdgeInput {
  id: string;
  source: string;
  target: string;
  kind: ProjectGraphEdgeKind;
  label?: OptionalInput<string>;
  metadata?: OptionalInput<ProjectGraphMetadata>;
}

export interface ProjectGraphClusterInput {
  id: string;
  label: string;
  nodeIds?: OptionalInput<string[]>;
  kind?: OptionalInput<string>;
  metadata?: OptionalInput<ProjectGraphMetadata>;
}

export interface ProjectGraphIssueInput {
  id: string;
  message: string;
  severity: ProjectGraphIssueSeverity;
  targetId?: OptionalInput<string>;
  metadata?: OptionalInput<ProjectGraphMetadata>;
}

export interface ProjectGraphInput {
  projectType: ProjectGraphProjectType;
  nodes?: ProjectGraphNodeInput[];
  edges?: ProjectGraphEdgeInput[];
  clusters?: ProjectGraphClusterInput[];
  errors?: ProjectGraphIssueInput[];
}

export function normalizeProjectGraph(input: ProjectGraphInput): ProjectGraph {
  const graph: ProjectGraph = {
    projectType: input.projectType,
    nodes: (input.nodes ?? []).map((node) => ({
      id: node.id,
      label: node.label,
      kind: node.kind,
      ...(node.layer == null ? {} : { layer: node.layer }),
      metadata: node.metadata ?? {},
    })),
    edges: (input.edges ?? []).map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      kind: edge.kind,
      ...(edge.label == null ? {} : { label: edge.label }),
      metadata: edge.metadata ?? {},
    })),
    clusters: (input.clusters ?? []).map((cluster) => ({
      id: cluster.id,
      label: cluster.label,
      nodeIds: cluster.nodeIds ?? [],
      ...(cluster.kind == null ? {} : { kind: cluster.kind }),
      metadata: cluster.metadata ?? {},
    })),
    errors: (input.errors ?? []).map((error) => ({
      id: error.id,
      message: error.message,
      severity: error.severity,
      ...(error.targetId == null ? {} : { targetId: error.targetId }),
      metadata: error.metadata ?? {},
    })),
  };

  graph.errors = mergeProjectGraphDiagnostics(graph.errors, findReferenceDiagnostics(graph));
  return graph;
}

function mergeProjectGraphDiagnostics(
  existing: ProjectGraphIssue[],
  diagnostics: ProjectGraphIssue[],
): ProjectGraphIssue[] {
  const issueIds = new Set(existing.map((issue) => issue.id));
  return [
    ...existing,
    ...diagnostics.filter((diagnostic) => {
      if (issueIds.has(diagnostic.id)) {
        return false;
      }
      issueIds.add(diagnostic.id);
      return true;
    }),
  ];
}

function findReferenceDiagnostics(graph: ProjectGraph): ProjectGraphIssue[] {
  const nodeIds = new Set(graph.nodes.map((node) => node.id));
  const diagnostics: ProjectGraphIssue[] = [];

  graph.edges.forEach((edge) => {
    if (!nodeIds.has(edge.source)) {
      diagnostics.push(createMissingEdgeNodeIssue(edge.id, "source", edge.source));
    }
    if (!nodeIds.has(edge.target)) {
      diagnostics.push(createMissingEdgeNodeIssue(edge.id, "target", edge.target));
    }
  });

  graph.clusters.forEach((cluster) => {
    cluster.nodeIds.forEach((nodeId) => {
      if (!nodeIds.has(nodeId)) {
        diagnostics.push({
          id: `cluster:${cluster.id}:missing-member:${nodeId}`,
          message: `Cluster member references missing node '${nodeId}'.`,
          severity: "warning",
          targetId: cluster.id,
          metadata: { source: "projectGraph.normalize" },
        });
      }
    });
  });

  return diagnostics;
}

function createMissingEdgeNodeIssue(
  edgeId: string,
  endpoint: "source" | "target",
  nodeId: string,
): ProjectGraphIssue {
  return {
    id: `edge:${edgeId}:missing-${endpoint}`,
    message: `Edge ${endpoint} references missing node '${nodeId}'.`,
    severity: "warning",
    targetId: edgeId,
    metadata: { source: "projectGraph.normalize" },
  };
}
