import React, { useEffect, useMemo, useState } from "react";
// CopilotKit temporarily disabled - causing agent errors
// import {
//   CopilotKit,
//   useCopilotAdditionalInstructions,
//   useCopilotAction,
//   useCopilotReadable,
// } from "@copilotkit/react-core";

import { createApiClient } from "./api/client";
import { resolveApiBaseUrl } from "./config";
import { CleanLayout } from "./components/CleanLayout";
import DiagramCanvas from "./components/DiagramCanvas";
import GraphBuilderInspector from "./components/GraphBuilderInspector";
import GraphExplorerPanel from "./components/GraphExplorerPanel";
import type { ApprovalPackageDetail, ApprovalStatus } from "./generationTypes";
import { toDiagramData } from "./graphWorkspace/adapters";
import { projectGraphToDiagramData } from "./projectGraph/diagramAdapter";
import { createStarterProjectGraphTemplate } from "./projectGraph/templates";
import type {
  AssistantMessage,
  ContextSource,
  ContextSourceCategory,
  DiagramData,
  DiagramEdge,
  DiagramNode,
  DocumentName,
  Finding,
  LibraryContextItem,
  LifecycleReadinessResponse,
  ReviewResponse,
} from "./types";
import "./styles.css";

const DEFAULT_BUNDLE_ROOT = ".cursor/plans/example";
const STARTER_DIAGRAM = projectGraphToDiagramData(createStarterProjectGraphTemplate());
const CORE_NODE_IDS = new Set([
  "spec",
  "plan",
  "tasks",
  "skills",
  "library",
  "review",
  "tools",
  "success_package",
  "needs_context",
]);
const EMPTY_DOCUMENTS: Record<DocumentName, string> = {
  "spec.md": "",
  "plan.md": "",
  "tasks.md": "",
};
const API_BASE_URL = resolveApiBaseUrl(import.meta.env.VITE_UIPLAN_API_URL);
const COPILOT_RUNTIME_URL = `${API_BASE_URL}/copilotkit`;
const DEFAULT_NODES: DiagramNode[] = STARTER_DIAGRAM.nodes;
const DEFAULT_EDGES: DiagramEdge[] = STARTER_DIAGRAM.edges;
const DEFAULT_MESSAGES: AssistantMessage[] = [
  {
    role: "assistant",
    content:
      "I can help visualize UiPath flows, connect skills and book context, and turn the diagram into plan edits.",
  },
];
const CONTEXT_EDGE_TYPES = new Set(["uses_context", "uses_skill", "depends_on"]);
const CONTEXT_NODE_KINDS = new Set<DiagramNode["kind"]>(["library", "skill"]);

type GraphVisualMode = "idle" | "focus" | "trace" | "dependencies" | "context" | "subgraph";

interface GraphVisualState {
  focusedNodeId: string | null;
  highlightedNodeIds: string[];
  highlightedEdgeIds: string[];
  mode: GraphVisualMode;
  summary: string | null;
}

interface ResolvedContextCitation {
  source_type: string;
  source_id: string;
  snippet: string;
  strict: boolean;
}

const EMPTY_GRAPH_VISUAL_STATE: GraphVisualState = {
  focusedNodeId: null,
  highlightedNodeIds: [],
  highlightedEdgeIds: [],
  mode: "idle",
  summary: null,
};

function unique(values: string[]) {
  return Array.from(new Set(values.filter(Boolean)));
}

function createUniqueCopilotNodeId(existingNodeIds: Set<string>) {
  let suffix = 0;
  let candidate = `copilot-node-${Date.now()}`;
  while (existingNodeIds.has(candidate)) {
    suffix += 1;
    candidate = `copilot-node-${Date.now()}-${suffix}`;
  }
  return candidate;
}

function normalizeIds(value: string[] | string | undefined) {
  if (Array.isArray(value)) {
    return unique(value);
  }
  return typeof value === "string" && value.trim() ? [value.trim()] : [];
}

function getConnectedEdges(nodeId: string, edges: DiagramEdge[]) {
  return edges.filter((edge) => edge.from === nodeId || edge.to === nodeId);
}

function getOutgoingEdges(nodeId: string, edges: DiagramEdge[]) {
  return edges.filter((edge) => edge.from === nodeId);
}

function traceEdgeIds(sourceId: string, targetId: string, edges: DiagramEdge[]) {
  const queue: Array<{ nodeId: string; edgeIds: string[] }> = [{ nodeId: sourceId, edgeIds: [] }];
  const visited = new Set([sourceId]);

  while (queue.length > 0) {
    const current = queue.shift();
    if (!current) {
      continue;
    }
    if (current.nodeId === targetId) {
      return current.edgeIds;
    }

    for (const edge of getOutgoingEdges(current.nodeId, edges)) {
      const nextNodeId = edge.to;
      if (visited.has(nextNodeId)) {
        continue;
      }
      visited.add(nextNodeId);
      queue.push({ nodeId: nextNodeId, edgeIds: [...current.edgeIds, edge.id] });
    }
  }

  return [];
}

function nodeIdsForEdges(edgeIds: string[], edges: DiagramEdge[]) {
  const edgeIdSet = new Set(edgeIds);
  return unique(
    edges
      .filter((edge) => edgeIdSet.has(edge.id))
      .flatMap((edge) => [edge.from, edge.to]),
  );
}

function unknownNodeIds(nodeIds: string[], nodes: DiagramNode[]) {
  const existingNodeIds = new Set(nodes.map((node) => node.id));
  return unique(nodeIds).filter((id) => !existingNodeIds.has(id));
}

function invalidNodeResult(nodeIds: string[]) {
  return {
    status: "warning",
    warning: `Unknown node id(s): ${nodeIds.join(", ")}`,
    highlighted_node_ids: [],
    highlighted_edge_ids: [],
    safety: "visual-read-only",
  };
}

function explainNode(node: DiagramNode | null, edges: DiagramEdge[]) {
  if (!node) {
    return {
      id: null,
      title: null,
      summary: "No ProjectGraph node is selected.",
      safety: "visual-read-only",
      connected_edges: [],
    };
  }

  const connectedEdges = getConnectedEdges(node.id, edges).map((edge) => ({
    id: edge.id,
    from: edge.from,
    to: edge.to,
    label: edge.label,
    edge_type: edge.edge_type ?? null,
  }));

  return {
    id: node.id,
    title: node.title,
    kind: node.kind,
    role: node.role ?? null,
    output_type: node.output_type ?? null,
    source: node.source ?? null,
    summary: node.description,
    context_policy: node.context_policy ?? null,
    connected_edges: connectedEdges,
    safety: "visual-read-only",
  };
}

// CopilotKit integration removed - see commit 64fdbae for history

function isDiagramData(value: unknown): value is DiagramData {
  const diagram = value as Partial<DiagramData>;
  return Array.isArray(diagram?.nodes) && Array.isArray(diagram?.edges);
}

function getProposalReviewStatus(
  packageDetail: ApprovalPackageDetail,
  proposalId: string,
): ApprovalStatus | null {
  const proposalState = packageDetail.approval_state.proposals[proposalId];
  if (typeof proposalState === "string") {
    return proposalState as ApprovalStatus;
  }
  if (
    typeof proposalState === "object" &&
    proposalState !== null &&
    "review_status" in proposalState &&
    typeof proposalState.review_status === "string"
  ) {
    return proposalState.review_status as ApprovalStatus;
  }
  if (
    typeof proposalState === "object" &&
    proposalState !== null &&
    "status" in proposalState &&
    typeof proposalState.status === "string"
  ) {
    return proposalState.status as ApprovalStatus;
  }
  return null;
}

export default function App() {
  const apiClient = useMemo(() => createApiClient({ baseUrl: API_BASE_URL }), []);
  const [bundleRoot, setBundleRoot] = useState(DEFAULT_BUNDLE_ROOT);
  const [nodes, setNodes] = useState<DiagramNode[]>(DEFAULT_NODES);
  const [edges, setEdges] = useState<DiagramEdge[]>(DEFAULT_EDGES);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>("plan");
  const [isLoadingProject, setIsLoadingProject] = useState(true);
  const [graphVisualState, setGraphVisualState] = useState<GraphVisualState>(
    EMPTY_GRAPH_VISUAL_STATE,
  );
  const [resolvedContextCitations, setResolvedContextCitations] = useState<ResolvedContextCitation[]>(
    [],
  );
  const [isResolvingContext, setIsResolvingContext] = useState(false);
  const [contextSourceCategories, setContextSourceCategories] = useState<ContextSourceCategory[]>(
    [],
  );
  const selectedNode = nodes.find((node) => node.id === selectedNodeId) ?? null;

  useEffect(() => {
    const loadProjectGraph = async () => {
      setIsLoadingProject(true);
      try {
        const workspace = await apiClient.indexWorkspace(DEFAULT_BUNDLE_ROOT);
        const diagram = toDiagramData(workspace);
        setNodes(diagram.nodes);
        setEdges(diagram.edges);
      } catch {
        // Fall back to default nodes/edges if indexing fails
        setNodes(DEFAULT_NODES);
        setEdges(DEFAULT_EDGES);
      } finally {
        setIsLoadingProject(false);
      }
    };
    void loadProjectGraph();
  }, [apiClient]);

  useEffect(() => {
    const loadContextSources = async () => {
      try {
        const response = await apiClient.loadContextSources();
        setContextSourceCategories(Array.isArray(response.categories) ? response.categories : []);
      } catch {
        setContextSourceCategories([]);
      }
    };
    void loadContextSources();
  }, [apiClient]);

  useEffect(() => {
    setSelectedNodeId((currentSelectedNodeId) => {
      if (
        currentSelectedNodeId &&
        nodes.some((node) => node.id === currentSelectedNodeId)
      ) {
        return currentSelectedNodeId;
      }
      return nodes[0]?.id ?? null;
    });
  }, [nodes]);

  useEffect(() => {
    setResolvedContextCitations([]);
  }, [selectedNodeId]);


  const handleResolveContext = async () => {
    if (!selectedNodeId) {
      return;
    }
    setIsResolvingContext(true);
    const sourceIds = unique(
      contextSourceCategories
        .filter((category) => category.sources.some((source) => source.available !== false))
        .map((category) => category.id),
    );
    try {
      const response = await apiClient.resolveGraphNodeContext(
        selectedNodeId,
        selectedNode?.title ?? "",
        sourceIds.length > 0 ? sourceIds : ["library", "skills"],
      );
      setResolvedContextCitations(response.citations ?? []);
    } catch {
      setResolvedContextCitations([]);
    } finally {
      setIsResolvingContext(false);
    }
  };

  const handleMoveNode = (nodeId: string, x: number, y: number) => {
    setNodes((current) =>
      current.map((node) => (node.id === nodeId ? { ...node, x, y } : node)),
    );
  };

  return (
    <CleanLayout>
      {{
        explorer: isLoadingProject ? (
          <div style={{ padding: "20px" }}>
            <h2>Graph Explorer</h2>
            <div className="loading-skeleton loading-skeleton-tall"></div>
            <div className="loading-skeleton"></div>
            <div className="loading-skeleton loading-skeleton-short"></div>
            <div className="loading-skeleton"></div>
            <div className="loading-skeleton loading-skeleton-short"></div>
          </div>
        ) : (
          <GraphExplorerPanel
            nodes={nodes}
            selectedNodeId={selectedNode?.id ?? null}
            onSelectNodeId={setSelectedNodeId}
          />
        ),
        canvas: (
          <DiagramCanvas
            nodes={nodes}
            edges={edges}
            selectedNodeId={selectedNode?.id ?? null}
            visualState={graphVisualState}
            edgeTargetId=""
            edgeLabel=""
            canDeleteSelectedNode={false}
            packageDetail={null}
            selectedProposalId={null}
            proposalPreviewId={null}
            onSelectNodeId={setSelectedNodeId}
            onMoveNode={handleMoveNode}
            onAddNode={() => {}}
            onDeleteSelectedNode={() => {}}
            onChangeEdgeTargetId={() => {}}
            onChangeEdgeLabel={() => {}}
            onCreateEdge={() => {}}
          />
        ),
        inspector: (
          <GraphBuilderInspector
            selectedNode={selectedNode}
            resolvedCitations={resolvedContextCitations}
            isResolvingContext={isResolvingContext}
            onResolveContext={handleResolveContext}
          />
        ),
      }}
    </CleanLayout>
  );
}
