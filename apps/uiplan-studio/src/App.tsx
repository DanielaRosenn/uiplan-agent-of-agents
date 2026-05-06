import React, { useEffect, useMemo, useState } from "react";
import {
  CopilotKit,
  useCopilotAdditionalInstructions,
  useCopilotAction,
  useCopilotReadable,
} from "@copilotkit/react-core";

import { createApiClient } from "./api/client";
import { resolveApiBaseUrl } from "./config";
import AgentPanel from "./components/AgentPanel";
import ApprovalPackagePanel from "./components/ApprovalPackagePanel";
import BundleNavigator from "./components/BundleNavigator";
import ContextInspector from "./components/ContextInspector";
import ContextSourcesPanel from "./components/ContextSourcesPanel";
import DiagramCanvas from "./components/DiagramCanvas";
import DiffPanel from "./components/DiffPanel";
import FindingsPanel from "./components/FindingsPanel";
import GraphBuilderInspector from "./components/GraphBuilderInspector";
import GraphExplorerPanel from "./components/GraphExplorerPanel";
import LibraryContextPanel from "./components/LibraryContextPanel";
import LifecyclePanel from "./components/LifecyclePanel";
import StageControls from "./components/StageControls";
import SectionEditor from "./components/SectionEditor";
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
  const [documents, setDocuments] = useState<Record<DocumentName, string>>(EMPTY_DOCUMENTS);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [readiness, setReadiness] = useState<LifecycleReadinessResponse | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<DocumentName>("spec.md");
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [nodes, setNodes] = useState<DiagramNode[]>(DEFAULT_NODES);
  const [edges, setEdges] = useState<DiagramEdge[]>(DEFAULT_EDGES);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>("plan");
  const [edgeTargetId, setEdgeTargetId] = useState("review");
  const [edgeLabel, setEdgeLabel] = useState("connects to");
  const [messages, setMessages] = useState<AssistantMessage[]>(DEFAULT_MESSAGES);
  const [previewDiff, setPreviewDiff] = useState<string | null>(null);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [libraryContext, setLibraryContext] = useState<LibraryContextItem[]>([]);
  const [contextSourceCategories, setContextSourceCategories] = useState<ContextSourceCategory[]>(
    [],
  );
  const [previewContextSource, setPreviewContextSource] = useState<string | null>(null);
  const [packageDetail, setPackageDetail] = useState<ApprovalPackageDetail | null>(null);
  const [selectedProposalId, setSelectedProposalId] = useState<string | null>(null);
  const [proposalPreviewIds, setProposalPreviewIds] = useState<Record<string, string>>({});
  const [proposalPreviewDiffs, setProposalPreviewDiffs] = useState<Record<string, string>>({});
  const [generationErrorMessage, setGenerationErrorMessage] = useState<string | null>(null);
  const [graphVisualState, setGraphVisualState] = useState<GraphVisualState>(
    EMPTY_GRAPH_VISUAL_STATE,
  );
  const proposalPreviewId =
    selectedProposalId == null ? null : proposalPreviewIds[selectedProposalId] ?? null;
  const proposalPreviewDiff =
    selectedProposalId == null ? null : proposalPreviewDiffs[selectedProposalId] ?? null;
  const selectedNode = nodes.find((node) => node.id === selectedNodeId) ?? null;
  const canDeleteSelectedNode = selectedNode != null && !CORE_NODE_IDS.has(selectedNode.id);

  useEffect(() => {
    const loadBundle = async () => {
      try {
        const bundle = await apiClient.loadBundle(DEFAULT_BUNDLE_ROOT);
        setBundleRoot(bundle.root);
        setDocuments(bundle.documents);
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
    const nextTarget = nodes.find((node) => node.id !== selectedNodeId)?.id ?? "";
    const targetMissing = !nodes.some((node) => node.id === edgeTargetId);
    if (!edgeTargetId || edgeTargetId === selectedNodeId || targetMissing) {
      setEdgeTargetId(nextTarget);
    }
  }, [edgeTargetId, nodes, selectedNodeId]);

  const handleFindingSelect = (finding: Finding) => {
    setSelectedFinding(finding);
    if (
      finding.document === "spec.md" ||
      finding.document === "plan.md" ||
      finding.document === "tasks.md"
    ) {
      setSelectedDocument(finding.document);
    }
    setSelectedNodeId("review");
  };

  const handleDiagramPreviewClick = async () => {
    const libraryPayload = libraryContext.map((item) => ({
      book_id: item.book_id,
      chapter_id: item.chapter_id,
      section_id: item.section_id,
      score: item.score,
      snippet: item.snippet,
    }));
    try {
      const preview = await apiClient.previewDiagramDocument(
        bundleRoot,
        selectedDocument,
        nodes,
        edges,
        selectedNode?.id ?? null,
        libraryPayload,
      );
      setPreviewDiff(preview.diff);
      setPreviewId(preview.preview_id);
      if (libraryContext.length > 0) {
        const top = libraryContext[0];
        setPreviewContextSource(`${top.book_id}/${top.chapter_id}/${top.section_id}`);
      } else {
        setPreviewContextSource(null);
      }
    } catch {
      // Keep UI interactive even when backend is unavailable.
      setPreviewDiff(
        `--- ${selectedDocument}\n+++ ${selectedDocument}\n+<!-- diagram preview unavailable -->`,
      );
      setPreviewId(null);
      setPreviewContextSource(null);
    }
  };

  const handleFixSelectedFinding = async (finding: Finding) => {
    const fixHint = finding.rule ? `\n<!-- fix: ${finding.rule} -->\n` : "\n<!-- fix -->\n";
    try {
      const preview = await apiClient.previewSection(
        bundleRoot,
        selectedDocument,
        `${documents[selectedDocument]}${fixHint}`,
        [],
      );
      setPreviewDiff(preview.diff);
      setPreviewId(preview.preview_id);
    } catch {
      setPreviewDiff(`--- ${selectedDocument}\n+++ ${selectedDocument}\n+${fixHint.trimEnd()}`);
      setPreviewId(null);
    }
  };

  const handleSearchLibrary = async (query: string) => {
    try {
      const response = await apiClient.searchLibraryContext(query);
      setLibraryContext(response.items);
      setSelectedNodeId("library");
    } catch {
      setLibraryContext([]);
    }
  };

  const handleInsertCitation = (item: LibraryContextItem) => {
    const citation = `[${item.book_id}/${item.chapter_id}/${item.section_id}]`;
    const source = `${item.book_id}/${item.chapter_id}/${item.section_id}`;
    setDocuments((current) => ({
      ...current,
      [selectedDocument]: `${current[selectedDocument]}\n${citation}\n`,
    }));
    setNodes((current) => {
      const nodeId = `library-${item.book_id}-${item.chapter_id}-${item.section_id}`;
      if (current.some((node) => node.id === nodeId)) {
        return current;
      }
      return [
        ...current,
        {
          id: nodeId,
          title: item.section_id,
          kind: "library",
          description: item.snippet,
          x: 760,
          y: 300,
          source,
        },
      ];
    });
  };

  const handleAddContextSource = (source: ContextSource) => {
    if (source.available === false) {
      return;
    }

    const nodeId = `source-${source.category}-${source.id}`.replace(/[^a-zA-Z0-9_-]+/g, "-");
    if (nodes.some((node) => node.id === nodeId)) {
      setSelectedNodeId(nodeId);
      return;
    }

    const existingKindCount = nodes.filter((node) => node.kind === source.kind).length;
    const nextNode: DiagramNode = {
      id: nodeId,
      title: source.title,
      kind: source.kind,
      description: source.description,
      x: 760,
      y: 96 + existingKindCount * 112,
      source: source.source,
    };
    setNodes((current) => [...current, nextNode]);
    setSelectedNodeId(nodeId);
  };

  const handleSaveDocument = async () => {
    const content = documents[selectedDocument];
    try {
      const preview = await apiClient.previewSection(bundleRoot, selectedDocument, content, []);
      setPreviewDiff(preview.diff);
      setPreviewId(preview.preview_id);
      setPreviewContextSource(null);
    } catch {
      // Keep editor interactive even when backend preview fails.
    }
  };

  const handleSaveDiagram = async () => {
    try {
      await apiClient.saveDiagram(bundleRoot, nodes, edges);
    } catch {
      // Keep canvas interactive even when backend save fails.
    }
  };

  const handleRunReview = async () => {
    let reviewResult: ReviewResponse | null = null;
    try {
      reviewResult = await apiClient.runReview(
        documents["spec.md"],
        documents["plan.md"],
        documents["tasks.md"],
      );
      setFindings(reviewResult.findings ?? []);
    } catch {
      setFindings([]);
    }

    try {
      const readinessResult = await apiClient.runLifecycleReadiness(
        documents["spec.md"],
        documents["plan.md"],
        documents["tasks.md"],
      );
      setReadiness(readinessResult);
    } catch {
      setReadiness(
        reviewResult == null
          ? null
          : {
              status: "blocked",
              acceptance_ready: Boolean(reviewResult.acceptance_ready),
              error_count: (reviewResult.findings ?? []).filter(
                (finding) => finding.severity?.toLowerCase() === "error",
              ).length,
              findings_by_document: reviewResult.findings_by_document,
            },
      );
    }
  };

  const handleApplyPreview = async () => {
    if (previewId == null) {
      return;
    }
    try {
      await apiClient.applyPreview(previewId);
      setPreviewId(null);
      setPreviewDiff(null);
      const bundle = await apiClient.loadBundle(bundleRoot);
      setDocuments(bundle.documents);
      setBundleRoot(bundle.root);
    } catch {
      // Keep preview visible so user can retry.
    }
  };

  const handleMoveNode = (nodeId: string, x: number, y: number) => {
    setNodes((current) =>
      current.map((node) => (node.id === nodeId ? { ...node, x, y } : node)),
    );
  };

  const handleAddNode = (kind: DiagramNode["kind"]) => {
    const existingKindCount = nodes.filter((node) => node.kind === kind).length;
    const nodeId = `${kind}-${Date.now()}`;
    const nextNode: DiagramNode = {
      id: nodeId,
      title: `New ${kind}`,
      kind,
      description: `Describe this ${kind} context.`,
      x: 760,
      y: 96 + existingKindCount * 112,
      source: "",
    };
    setNodes((current) => [...current, nextNode]);
    setSelectedNodeId(nodeId);
  };

  const handleUpdateNode = (nodeId: string, updates: Partial<DiagramNode>) => {
    setNodes((current) =>
      current.map((node) => (node.id === nodeId ? { ...node, ...updates } : node)),
    );
  };

  const handleCreateEdge = () => {
    const label = edgeLabel.trim();
    const targetExists = nodes.some((node) => node.id === edgeTargetId);
    if (
      !selectedNode ||
      !edgeTargetId ||
      selectedNode.id === edgeTargetId ||
      !label ||
      !targetExists
    ) {
      return;
    }
    setEdges((current) => [
      ...current,
      {
        id: [
          selectedNode.id,
          edgeTargetId,
          label.toLowerCase().replace(/\W+/g, "-"),
          current.length + 1,
        ].join("-"),
        from: selectedNode.id,
        to: edgeTargetId,
        label,
      },
    ]);
    setEdgeLabel("connects to");
  };

  const handleDeleteSelectedNode = () => {
    if (!selectedNode || CORE_NODE_IDS.has(selectedNode.id)) {
      return;
    }
    const remainingNodes = nodes.filter((node) => node.id !== selectedNode.id);
    setNodes(remainingNodes);
    setEdges((current) =>
      current.filter((edge) => edge.from !== selectedNode.id && edge.to !== selectedNode.id),
    );
    setSelectedNodeId(remainingNodes[0]?.id ?? null);
  };

  const handleLoadStarterTemplate = async () => {
    try {
      const template = await apiClient.loadStarterProjectGraphTemplate();
      const diagram = projectGraphToDiagramData(template.graph);
      setNodes(diagram.nodes);
      setEdges(diagram.edges);
      setSelectedNodeId("plan");
    } catch {
      setNodes(DEFAULT_NODES);
      setEdges(DEFAULT_EDGES);
      setSelectedNodeId("plan");
    }
  };

  const handleSendMessage = async (message: string) => {
    setMessages((current) => [...current, { role: "user", content: message }]);
    try {
      const response = await apiClient.chatWithAssistant(message, nodes, selectedNode?.id ?? null);
      setMessages((current) => [...current, { role: "assistant", content: response.message }]);
      if (response.suggested_nodes.length > 0) {
        setNodes((current) => {
          const existingIds = new Set(current.map((node) => node.id));
          return [
            ...current,
            ...response.suggested_nodes.filter((node) => !existingIds.has(node.id)),
          ];
        });
      }
    } catch {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content:
            "I could not reach the local assistant endpoint. The diagram stays editable while the API is offline.",
        },
      ]);
    }
  };

  const appendDraftMessage = (label: "Plan" | "Scaffold", stages: string[]) => {
    const selectedNodeLabel = selectedNode?.id ?? "none";
    setMessages((current) => [
      ...current,
      {
        role: "assistant",
        content: `Drafted ${label} package request: POST /generation/packages with stages ${JSON.stringify(stages)}, bundle_root "${bundleRoot}", graph_ref { graph_id: "visual-builder-graph", selected_node_id: "${selectedNodeLabel}" }, write_policy approval_package_only.`,
      },
    ]);
  };

  const handleDraftPlanPackageRequest = () => {
    appendDraftMessage("Plan", ["01-plan"]);
  };

  const handleDraftScaffoldPackageRequest = () => {
    appendDraftMessage("Scaffold", ["02-scaffold"]);
  };

  const loadPackageDetail = async (
    packageId: string,
    options: { preservePreviewState?: boolean } = {},
  ) => {
    const detail = await apiClient.loadApprovalPackage(bundleRoot, packageId);
    setPackageDetail(detail);
    setSelectedProposalId((current) =>
      current && detail.proposals.some((proposal) => proposal.proposal_id === current)
        ? current
        : detail.proposals[0]?.proposal_id ?? null,
    );
    if (!options.preservePreviewState) {
      setProposalPreviewIds({});
      setProposalPreviewDiffs({});
    }
  };

  const handleGeneratePlanPackage = async () => {
    setGenerationErrorMessage(null);
    try {
      const manifest = await apiClient.generateApprovalPackage(
        bundleRoot,
        { nodes, edges },
        ["01-plan"],
        null,
      );
      await loadPackageDetail(manifest.package_id);
    } catch (error) {
      const details = error instanceof Error ? error.message : "Unknown error";
      setGenerationErrorMessage(
        `Plan package generation failed. Verify the generation service is running and retry. (${details})`,
      );
    }
  };

  const handleGenerateScaffoldPackage = async () => {
    setGenerationErrorMessage(null);
    try {
      const stageStatuses = packageDetail?.approval_state.stage_statuses;
      const hasApprovedPlan = stageStatuses?.["01-plan"] === "approved";
      const stages: Array<"01-plan" | "02-scaffold"> =
        hasApprovedPlan ? ["02-scaffold"] : ["01-plan", "02-scaffold"];
      const manifest = await apiClient.generateApprovalPackage(bundleRoot, { nodes, edges }, stages, null);
      await loadPackageDetail(manifest.package_id);
    } catch (error) {
      const details = error instanceof Error ? error.message : "Unknown error";
      setGenerationErrorMessage(
        `Scaffold package generation failed. Verify the generation service is running and retry. (${details})`,
      );
    }
  };

  const handleApproveProposal = async (proposalId: string) => {
    if (!packageDetail) {
      return;
    }
    try {
      await apiClient.updateApprovalState(
        bundleRoot,
        packageDetail.manifest.package_id,
        "proposal",
        proposalId,
        "approved",
        "Reviewer",
      );
      await loadPackageDetail(packageDetail.manifest.package_id, { preservePreviewState: true });
    } catch {
      // Keep UI responsive when approval endpoint fails.
    }
  };

  const handlePreviewProposal = async (proposalId: string) => {
    if (!packageDetail) {
      return;
    }
    try {
      const response = await apiClient.previewProposal(
        bundleRoot,
        packageDetail.manifest.package_id,
        proposalId,
      );
      setProposalPreviewIds((current) => ({ ...current, [proposalId]: response.preview_id }));
      const responseDiff = response.diff ?? response.diff_body ?? response.diff_content;
      if (responseDiff) {
        setProposalPreviewDiffs((current) => ({ ...current, [proposalId]: responseDiff }));
      }
    } catch {
      setProposalPreviewIds((current) => {
        const next = { ...current };
        delete next[proposalId];
        return next;
      });
      setProposalPreviewDiffs((current) => {
        const next = { ...current };
        delete next[proposalId];
        return next;
      });
    }
  };

  const handleApplyProposal = async (proposalId: string, nextPreviewId: string) => {
    if (!packageDetail) {
      return;
    }
    const expectedPreviewId = proposalPreviewIds[proposalId];
    const proposal = packageDetail.proposals.find((item) => item.proposal_id === proposalId);
    const proposalStatus = getProposalReviewStatus(packageDetail, proposalId);
    if (
      selectedProposalId !== proposalId ||
      expectedPreviewId == null ||
      expectedPreviewId !== nextPreviewId ||
      !proposal?.apply_eligible ||
      proposalStatus !== "approved"
    ) {
      return;
    }
    try {
      setGenerationErrorMessage(null);
      await apiClient.applyProposalPreview(
        bundleRoot,
        packageDetail.manifest.package_id,
        proposalId,
        nextPreviewId,
      );
      await loadPackageDetail(packageDetail.manifest.package_id);
    } catch (error) {
      const details = error instanceof Error ? error.message : "Unknown error";
      setGenerationErrorMessage(`Proposal apply failed. Review the preview and retry. (${details})`);
    }
  };

  return (
    <CopilotKit runtimeUrl={COPILOT_RUNTIME_URL} useSingleEndpoint>
      <div className="studio-root">
        <CopilotStudioContext
          bundleRoot={bundleRoot}
          nodes={nodes}
          edges={edges}
          selectedNodeId={selectedNode?.id ?? null}
          visualState={graphVisualState}
          contextSourceCategories={contextSourceCategories}
          packageDetail={packageDetail}
          selectedProposalId={selectedProposalId}
          onSelectNodeId={setSelectedNodeId}
          onSetVisualState={setGraphVisualState}
        />
        <header className="studio-header">
          <div>
            <p className="eyebrow">UiPath Builder Agent</p>
            <h1>UiPlan Studio</h1>
          </div>
          <p>Visualize, build, and review UiPath plans with Copilot-guided context.</p>
        </header>
        <div className="studio-layout">
          <aside className="studio-rail">
            <div className="studio-card">
              <BundleNavigator
                selectedDocument={selectedDocument}
                onSelectDocument={setSelectedDocument}
              />
            </div>
            <div className="studio-card">
              <LifecyclePanel readiness={readiness} />
            </div>
            <div className="studio-card">
              <FindingsPanel findings={findings} onSelectFinding={handleFindingSelect} />
            </div>
          </aside>
          <main className="studio-main">
            <DiagramCanvas
              nodes={nodes}
              edges={edges}
              selectedNodeId={selectedNode?.id ?? null}
              visualState={graphVisualState}
              edgeTargetId={edgeTargetId}
              edgeLabel={edgeLabel}
              canDeleteSelectedNode={canDeleteSelectedNode}
              packageDetail={packageDetail}
              selectedProposalId={selectedProposalId}
              proposalPreviewId={proposalPreviewId}
              onSelectNodeId={setSelectedNodeId}
              onMoveNode={handleMoveNode}
              onAddNode={handleAddNode}
              onDeleteSelectedNode={handleDeleteSelectedNode}
              onChangeEdgeTargetId={setEdgeTargetId}
              onChangeEdgeLabel={setEdgeLabel}
              onCreateEdge={handleCreateEdge}
            />
            <div className="workspace-panels">
              <div className="studio-card">
                <GraphExplorerPanel
                  nodes={nodes}
                  selectedNodeId={selectedNode?.id ?? null}
                  onSelectNodeId={setSelectedNodeId}
                />
              </div>
              <div className="studio-card">
                <GraphBuilderInspector selectedNode={selectedNode} />
              </div>
            </div>
            <div className="studio-card editor-card">
              <SectionEditor
                documentName={selectedDocument}
                content={documents[selectedDocument]}
                onChangeContent={(nextContent) =>
                  setDocuments((current) => ({ ...current, [selectedDocument]: nextContent }))
                }
              />
            </div>
            <div className="studio-card studio-actions action-bar">
              <StageControls
                packageDetail={packageDetail}
                onGeneratePlan={handleGeneratePlanPackage}
                onGenerateScaffold={handleGenerateScaffoldPackage}
              />
              <button type="button" onClick={handleSaveDocument}>
                Preview document changes
              </button>
              <button type="button" onClick={handleSaveDiagram}>
                Save diagram
              </button>
              <button type="button" onClick={handleLoadStarterTemplate}>
                Load starter ProjectGraph
              </button>
              <button type="button" onClick={handleRunReview}>
                Run review
              </button>
              <button type="button" onClick={handleDiagramPreviewClick}>
                Preview diagram into document
              </button>
              <button type="button" onClick={handleApplyPreview} disabled={previewId == null}>
                Apply preview
              </button>
            </div>
            {generationErrorMessage ? (
              <div className="studio-card generation-status-banner" role="alert">
                {generationErrorMessage}
              </div>
            ) : null}
            {packageDetail ? (
              <div className="studio-card">
                <ApprovalPackagePanel
                  packageDetail={packageDetail}
                  selectedProposalId={selectedProposalId}
                  proposalPreviewId={proposalPreviewId}
                  proposalPreviewDiff={proposalPreviewDiff}
                  onSelectProposal={setSelectedProposalId}
                  onApproveProposal={handleApproveProposal}
                  onPreviewProposal={handlePreviewProposal}
                  onApplyProposal={handleApplyProposal}
                />
              </div>
            ) : null}
            <p className="muted">
              Document edits and diagram generation are preview-only. Apply preview writes the
              reviewed diff.
            </p>
            {previewContextSource ? (
              <div className="studio-card">
                <p>Generated with context from {previewContextSource}</p>
              </div>
            ) : null}
            {previewDiff ? (
              <div className="studio-card">
                <DiffPanel diff={previewDiff} />
              </div>
            ) : null}
          </main>
          <aside className="studio-sidebar">
            <div className="studio-card">
              <AgentPanel
                selectedFinding={selectedFinding}
                selectedNode={selectedNode}
                messages={messages}
                onGenerateSection={handleDiagramPreviewClick}
                onDraftPlanPackageRequest={handleDraftPlanPackageRequest}
                onDraftScaffoldPackageRequest={handleDraftScaffoldPackageRequest}
                onFixSelectedFinding={handleFixSelectedFinding}
                onSendMessage={handleSendMessage}
              />
            </div>
            <div className="studio-card">
              <ContextInspector
                selectedNode={selectedNode}
                libraryContext={libraryContext}
                selectedFinding={selectedFinding}
                onUpdateNode={handleUpdateNode}
              />
            </div>
            <div className="studio-card">
              <ContextSourcesPanel
                categories={contextSourceCategories}
                onAddSource={handleAddContextSource}
              />
            </div>
            <div className="studio-card">
              <LibraryContextPanel
                items={libraryContext}
                onSearch={handleSearchLibrary}
                onInsertCitation={handleInsertCitation}
              />
            </div>
          </aside>
        </div>
      </div>
    </CopilotKit>
  );
}
