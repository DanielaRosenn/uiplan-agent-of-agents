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

// CopilotStudioContext component temporarily disabled - requires CopilotKit
/*
interface CopilotStudioContextProps {
  bundleRoot: string;
  nodes: DiagramNode[];
  edges: DiagramEdge[];
  selectedNodeId: string | null;
  visualState: GraphVisualState;
  contextSourceCategories: ContextSourceCategory[];
  packageDetail: ApprovalPackageDetail | null;
  selectedProposalId: string | null;
  onSelectNodeId: (nodeId: string | null) => void;
  onSetVisualState: (state: GraphVisualState) => void;
}

function CopilotStudioContext({
  bundleRoot,
  nodes,
  edges,
  selectedNodeId,
  visualState,
  contextSourceCategories,
  packageDetail,
  selectedProposalId,
  onSelectNodeId,
  onSetVisualState,
}: CopilotStudioContextProps) {
  const selectedNode = useMemo(
    () => nodes.find((node) => node.id === selectedNodeId) ?? null,
    [nodes, selectedNodeId],
  );
  const typedGraph = useMemo(
    () => ({
      nodes: nodes.map((node) => ({
        id: node.id,
        title: node.title,
        kind: node.kind,
        description: node.description,
        source: node.source ?? null,
        role: node.role ?? null,
        output_type: node.output_type ?? null,
        project_types: node.project_types ?? [],
        context_policy: node.context_policy ?? null,
        strict_citation: node.strict_citation ?? null,
        layer: node.layer ?? null,
        status: node.status ?? null,
        metadata: node.metadata ?? {},
      })),
      edges,
    }),
    [edges, nodes],
  );
  const contextSourceSummary = useMemo(
    () =>
      contextSourceCategories.map((category) => ({
        id: category.id,
        title: category.title,
        description: category.description,
        source_count: category.sources.length,
        available_source_count: category.sources.filter((source) => source.available !== false)
          .length,
        sources: category.sources.map((source) => ({
          id: source.id,
          title: source.title,
          kind: source.kind,
          source: source.source,
          available: source.available,
        })),
      })),
    [contextSourceCategories],
  );
  const packageSummary = useMemo(
    () =>
      packageDetail == null
        ? null
        : {
            package_id: packageDetail.manifest.package_id,
            generated_stages: packageDetail.manifest.generated_stages,
            stage_statuses: packageDetail.approval_state.stage_statuses,
            proposal_count: packageDetail.proposals.length,
          },
    [packageDetail],
  );

  useCopilotAdditionalInstructions(
    {
      instructions:
        "Use UiPlan builder actions for context lookup, diagram suggestions, summaries, and preview/package request drafting. Do not write target files directly; generation creates approval packages only and apply is separate and guarded.",
    },
    [],
  );
  useCopilotAction(
    {
      name: "focusNodes",
      description:
        "Visually focus one or more ProjectGraph nodes on the canvas. Read-only; does not write files or call deployment APIs.",
      parameters: [
        {
          name: "ids",
          type: "string[]",
          description: "ProjectGraph node ids to highlight and focus.",
        },
      ],
      handler: async ({ ids }) => {
        const nodeIds = normalizeIds(ids).filter((id) => nodes.some((node) => node.id === id));
        const focusedNodeId = nodeIds[0] ?? null;
        onSetVisualState({
          focusedNodeId,
          highlightedNodeIds: nodeIds,
          highlightedEdgeIds: [],
          mode: nodeIds.length > 0 ? "focus" : "idle",
          summary:
            nodeIds.length > 0
              ? `Copilot focus: ${nodeIds.length} node(s) highlighted`
              : "Copilot focus: no matching nodes",
        });
        if (focusedNodeId) {
          onSelectNodeId(focusedNodeId);
        }
        return { highlighted_node_ids: nodeIds, safety: "visual-read-only" };
      },
    },
    [nodes, onSelectNodeId, onSetVisualState],
  );
  useCopilotAction(
    {
      name: "tracePath",
      description:
        "Highlight a connected path between source and target nodes, or the connected edges around a single node. Visual/read-only only.",
      parameters: [
        { name: "source", type: "string", description: "Source node id.", required: false },
        { name: "target", type: "string", description: "Target node id.", required: false },
        { name: "nodeId", type: "string", description: "Single node id to trace from.", required: false },
      ],
      handler: async ({ source, target, nodeId }) => {
        const sourceId = source || nodeId || selectedNodeId || "";
        const invalidNodeIds = unknownNodeIds([sourceId, target].filter(Boolean), nodes);
        if (invalidNodeIds.length > 0) {
          onSetVisualState({
            ...EMPTY_GRAPH_VISUAL_STATE,
            summary: `Copilot warning: ${invalidNodeIds.join(", ")} not found`,
          });
          return invalidNodeResult(invalidNodeIds);
        }
        const edgeIds = sourceId && target
          ? traceEdgeIds(sourceId, target, edges)
          : getConnectedEdges(sourceId, edges).map((edge) => edge.id);
        const highlightedNodeIds = nodeIdsForEdges(edgeIds, edges);
        if (sourceId && nodes.some((node) => node.id === sourceId)) {
          highlightedNodeIds.unshift(sourceId);
        }
        const nextNodeIds = unique(highlightedNodeIds);
        onSetVisualState({
          focusedNodeId: sourceId || null,
          highlightedNodeIds: nextNodeIds,
          highlightedEdgeIds: edgeIds,
          mode: edgeIds.length > 0 ? "trace" : "idle",
          summary:
            edgeIds.length > 0
              ? `Copilot trace: ${edgeIds.length} edge(s), ${nextNodeIds.length} node(s)`
              : target
                ? "Copilot trace: no directed path found"
                : "Copilot trace: no connected path found",
        });
        if (sourceId) {
          onSelectNodeId(sourceId);
        }
        return {
          highlighted_node_ids: nextNodeIds,
          highlighted_edge_ids: edgeIds,
          safety: "visual-read-only",
        };
      },
    },
    [edges, nodes, onSelectNodeId, onSetVisualState, selectedNodeId],
  );
  useCopilotAction(
    {
      name: "showDependencies",
      description:
        "Highlight dependency, context, tool, and skill edges around a ProjectGraph node. Visual/read-only only.",
      parameters: [
        { name: "nodeId", type: "string", description: "Node id to inspect.", required: false },
      ],
      handler: async ({ nodeId }) => {
        const focusId = nodeId || selectedNodeId || "";
        const invalidNodeIds = unknownNodeIds([focusId].filter(Boolean), nodes);
        if (invalidNodeIds.length > 0) {
          onSetVisualState({
            ...EMPTY_GRAPH_VISUAL_STATE,
            summary: `Copilot warning: ${invalidNodeIds.join(", ")} not found`,
          });
          return invalidNodeResult(invalidNodeIds);
        }
        const dependencyEdges = getConnectedEdges(focusId, edges).filter(
          (edge) =>
            CONTEXT_EDGE_TYPES.has(edge.edge_type ?? "") ||
            edge.branch === "context" ||
            edge.branch === "dependency",
        );
        const highlightedEdgeIds = dependencyEdges.map((edge) => edge.id);
        const highlightedNodeIds = unique([
          focusId,
          ...nodeIdsForEdges(highlightedEdgeIds, edges),
        ]);
        onSetVisualState({
          focusedNodeId: focusId || null,
          highlightedNodeIds,
          highlightedEdgeIds,
          mode: highlightedEdgeIds.length > 0 ? "dependencies" : "idle",
          summary:
            highlightedEdgeIds.length > 0
              ? `Copilot dependencies: ${highlightedEdgeIds.length} edge(s) around ${focusId}`
              : `Copilot dependencies: none found around ${focusId || "selection"}`,
        });
        if (focusId) {
          onSelectNodeId(focusId);
        }
        return {
          highlighted_node_ids: highlightedNodeIds,
          highlighted_edge_ids: highlightedEdgeIds,
          safety: "visual-read-only",
        };
      },
    },
    [edges, onSelectNodeId, onSetVisualState, selectedNodeId],
  );
  useCopilotAction(
    {
      name: "showContextForNode",
      description:
        "Highlight library and skill context nodes connected to a node. Visual/read-only only.",
      parameters: [
        { name: "nodeId", type: "string", description: "Node id to inspect.", required: false },
      ],
      handler: async ({ nodeId }) => {
        const focusId = nodeId || selectedNodeId || "";
        const invalidNodeIds = unknownNodeIds([focusId].filter(Boolean), nodes);
        if (invalidNodeIds.length > 0) {
          onSetVisualState({
            ...EMPTY_GRAPH_VISUAL_STATE,
            summary: `Copilot warning: ${invalidNodeIds.join(", ")} not found`,
          });
          return invalidNodeResult(invalidNodeIds);
        }
        const connectedEdges = getConnectedEdges(focusId, edges);
        const contextNodeIds = connectedEdges
          .flatMap((edge) => [edge.from, edge.to])
          .filter((id) => id !== focusId)
          .filter((id) => {
            const node = nodes.find((item) => item.id === id);
            return node ? CONTEXT_NODE_KINDS.has(node.kind) : false;
          });
        const contextEdgeIds = connectedEdges
          .filter((edge) => contextNodeIds.includes(edge.from) || contextNodeIds.includes(edge.to))
          .map((edge) => edge.id);
        const highlightedNodeIds = unique([focusId, ...contextNodeIds]);
        onSetVisualState({
          focusedNodeId: focusId || null,
          highlightedNodeIds,
          highlightedEdgeIds: contextEdgeIds,
          mode: contextNodeIds.length > 0 ? "context" : "idle",
          summary:
            contextNodeIds.length > 0
              ? `Copilot context: ${contextNodeIds.length} context node(s) for ${focusId}`
              : `Copilot context: no context nodes found for ${focusId || "selection"}`,
        });
        if (focusId) {
          onSelectNodeId(focusId);
        }
        return {
          context_node_ids: unique(contextNodeIds),
          highlighted_edge_ids: contextEdgeIds,
          safety: "visual-read-only",
        };
      },
    },
    [edges, nodes, onSelectNodeId, onSetVisualState, selectedNodeId],
  );
  useCopilotAction(
    {
      name: "renderSubgraph",
      description:
        "Render a small visual subgraph by highlighting matching nodes and their internal edges. Visual/read-only only.",
      parameters: [
        { name: "nodeIds", type: "string[]", description: "Node ids to include.", required: false },
        { name: "edgeIds", type: "string[]", description: "Edge ids to include.", required: false },
        { name: "nodeId", type: "string", description: "Center node id.", required: false },
      ],
      handler: async ({ nodeIds, edgeIds, nodeId }) => {
        const requestedNodeIds = normalizeIds(nodeIds);
        const requestedEdgeIds = normalizeIds(edgeIds);
        const centerNodeId = nodeId || requestedNodeIds[0] || selectedNodeId || "";
        const invalidNodeIds = unknownNodeIds(
          unique([nodeId || "", ...requestedNodeIds, centerNodeId].filter(Boolean)),
          nodes,
        );
        if (invalidNodeIds.length > 0) {
          onSetVisualState({
            ...EMPTY_GRAPH_VISUAL_STATE,
            summary: `Copilot warning: ${invalidNodeIds.join(", ")} not found`,
          });
          return invalidNodeResult(invalidNodeIds);
        }
        const connectedEdgeIds = centerNodeId
          ? getConnectedEdges(centerNodeId, edges).map((edge) => edge.id)
          : [];
        const highlightedEdgeIds = unique([...requestedEdgeIds, ...connectedEdgeIds]).filter((id) =>
          edges.some((edge) => edge.id === id),
        );
        const highlightedNodeIds = unique([
          centerNodeId,
          ...requestedNodeIds,
          ...nodeIdsForEdges(highlightedEdgeIds, edges),
        ]).filter((id) => nodes.some((node) => node.id === id));
        onSetVisualState({
          focusedNodeId: centerNodeId || null,
          highlightedNodeIds,
          highlightedEdgeIds,
          mode: highlightedNodeIds.length > 0 ? "subgraph" : "idle",
          summary: `Copilot subgraph: ${highlightedNodeIds.length} node(s), ${highlightedEdgeIds.length} edge(s)`,
        });
        if (centerNodeId) {
          onSelectNodeId(centerNodeId);
        }
        return {
          highlighted_node_ids: highlightedNodeIds,
          highlighted_edge_ids: highlightedEdgeIds,
          safety: "visual-read-only",
        };
      },
    },
    [edges, nodes, onSelectNodeId, onSetVisualState, selectedNodeId],
  );
  useCopilotAction(
    {
      name: "explainSelectedNode",
      description:
        "Return a deterministic structured explanation for the currently selected ProjectGraph node. Does not mutate files.",
      parameters: [],
      handler: async () => explainNode(selectedNode, edges),
    },
    [edges, selectedNode],
  );
  useCopilotReadable(
    {
      description: "Canonical ProjectGraph visual context",
      value: {
        bundle_root: bundleRoot,
        canonical_project_graph: typedGraph,
        selected_node: selectedNode,
        selected_node_id: selectedNodeId,
        visible_highlights: {
          focused_node_id: visualState.focusedNodeId,
          highlighted_node_ids: visualState.highlightedNodeIds,
          highlighted_edge_ids: visualState.highlightedEdgeIds,
          mode: visualState.mode,
          summary: visualState.summary,
        },
        package_state: {
          selected_package_id: packageDetail?.manifest.package_id ?? null,
          selected_proposal_id: selectedProposalId,
          package_summary: packageSummary,
        },
        context_sources: contextSourceSummary,
        safety: "copilot actions are visual/read-only and cannot apply, deploy, publish, or write files",
      },
    },
    [
      bundleRoot,
      contextSourceSummary,
      packageDetail,
      packageSummary,
      selectedNode,
      selectedNodeId,
      selectedProposalId,
      typedGraph,
      visualState,
    ],
  );
  useCopilotReadable(
    {
      description: "Current UiPlan diagram state",
      value: { bundleRoot, typedGraph, selectedNodeId, selectedProposalId, visualState },
    },
    [bundleRoot, selectedNodeId, selectedProposalId, typedGraph, visualState],
  );
  useCopilotReadable(
    {
      description: "Available UiPlan context source categories",
      value: contextSourceCategories,
    },
    [contextSourceCategories],
  );
  useCopilotReadable(
    {
      description: "Current approval package state",
      value: {
        selected_package_id: packageDetail?.manifest.package_id ?? null,
        selected_proposal_id: selectedProposalId,
        package_summary: packageSummary,
      },
    },
    [packageDetail, packageSummary, selectedProposalId],
  );
  useCopilotReadable(
    {
      description: "Generation safety policy",
      value: "Generation creates approval packages only; apply is separate and guarded",
    },
    [],
  );

  return null;
}
*/

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
    const loadBundle = async () => {
      try {
        const bundle = await apiClient.loadBundle(DEFAULT_BUNDLE_ROOT);
        setBundleRoot(bundle.root);
        try {
          const diagram = await apiClient.loadDiagram(bundle.root);
          if (isDiagramData(diagram)) {
            setNodes(diagram.nodes);
            setEdges(diagram.edges);
          }
        } catch {
          setNodes(DEFAULT_NODES);
          setEdges(DEFAULT_EDGES);
        }
      } catch {
        // Keep UI usable even if bundle loading fails.
      }
    };
    void loadBundle();
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
        explorer: (
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
