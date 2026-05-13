import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Code2, FolderOpen, GitBranch, Loader2, Network, Notebook, RefreshCw, Sparkles } from "lucide-react";

import Canvas, { type CanvasHandle } from "./components/Canvas";
import UiplanCanvas from "./components/UiplanCanvas";
import LeftRail from "./components/LeftRail";
import Inspector from "./components/Inspector";
import Breadcrumb from "./components/Breadcrumb";
import { findFileNodeId } from "./components/UiplanInspector";
import { LAYERS, PALETTE } from "./theme";
import { computeLayout } from "./layout";
import {
  loadRefreshState,
  loadProjectGraph,
  type LoadGraphResult,
} from "./projectGraph/api";
import type { PathClass, ProjectEdge, ProjectGraph, ProjectNode } from "./projectGraph/types";
import { trackUxEvent } from "./telemetry";

import "./styles.css";

const EMPTY_GRAPH: ProjectGraph = { projectType: "—", nodes: [], edges: [], errors: [] };
const PLANNING_NODE_KINDS = new Set(["uiplan_view_as_is", "uiplan_view_to_be", "uiplan_tasks"]);

function buildPlanningProjectGraph(graph: ProjectGraph): ProjectGraph {
  const bundles = graph.nodes.filter((node) => node.kind === "uiplan_bundle");
  if (bundles.length === 0) return graph;

  const nodes = new Map<string, ProjectNode>();
  const edges: ProjectEdge[] = [];
  const skillTargets: Array<{ nodeId: string; tags: string[] }> = [];

  for (const bundle of bundles) {
    nodes.set(bundle.id, {
      ...bundle,
      children: undefined,
      roles: Array.from(new Set([...(bundle.roles ?? []), "entrypoint" as const])),
      desc: bundle.desc ?? "Planning bundle grounded in UiPlan files.",
    });

    for (const child of bundle.children?.nodes ?? []) {
      if (!PLANNING_NODE_KINDS.has(child.kind)) continue;

      nodes.set(child.id, {
        ...child,
        children: child.kind === "uiplan_tasks" ? child.children : undefined,
        layer: "uiplan",
        desc: planningNodeDescription(child),
      });
      edges.push({
        id: `${bundle.id}->${child.id}`,
        source: bundle.id,
        target: child.id,
        kind: "covers",
        label: planningEdgeLabel(child),
        desc: "Planning relationship from the UiPlan bundle.",
      });
      skillTargets.push({ nodeId: child.id, tags: [`kind:${child.kind}`, "uiplan"] });

      if (child.kind === "uiplan_view_to_be") {
        const view = child.meta?.view as any;
        addToBePlanningNodes(child, view, nodes, edges, skillTargets);
      }
    }
    skillTargets.push({ nodeId: bundle.id, tags: ["uiplan", "planning"] });
  }

  for (const node of graph.nodes) {
    if (node.kind === "skill") {
      nodes.set(node.id, node);
      for (const targetId of planningSkillTargets(node, skillTargets)) {
        edges.push({
          id: `${node.id}->${targetId}`,
          source: node.id,
          target: targetId,
          kind: "covers",
          label: "skill",
          desc: `${node.label} provides authoring or review guidance for this planning asset.`,
        });
      }
    }
  }

  return {
    ...graph,
    nodes: Array.from(nodes.values()),
    edges,
    errors: graph.errors ?? [],
  };
}

function addToBePlanningNodes(
  toBeNode: ProjectNode,
  view: any,
  nodes: Map<string, ProjectNode>,
  edges: ProjectEdge[],
  skillTargets: Array<{ nodeId: string; tags: string[] }>,
) {
  if (!view || typeof view !== "object") return;

  const workflows = Array.isArray(view.workflows) ? view.workflows : [];
  const integrations = Array.isArray(view.integrations) ? view.integrations : [];
  const orchestrator = Array.isArray(view.orchestrator) ? view.orchestrator : [];
  const hitl = Array.isArray(view.hitl) ? view.hitl : [];

  const workflowIds = new Map<string, string>();
  for (const workflow of workflows) {
    const id = `${toBeNode.id}::planned-workflow:${workflow.id}`;
    workflowIds.set(String(workflow.id), id);
    nodes.set(id, {
      id,
      label: workflowPlanningLabel(workflow),
      kind: "uipath_design_contract",
      layer: "uiplan",
      desc: `Pre-build workflow contract for ${workflowPlanningLabel(workflow)}. Inputs, outputs, roles, and readiness are validated before generation.`,
      status: "ok",
      roles: ["logic"],
      meta: {
        bucket: String(workflow.bucket ?? ""),
        source_view: toBeNode.id,
        artifact_type: String(workflow.artifact_type ?? "UiPath workflow contract"),
        planned_artifact: String(workflow.planned_artifact ?? workflowPlanningLabel(workflow)),
        inputs: workflow.inputs ?? [],
        outputs: workflow.outputs ?? [],
        contracts: workflow.contracts ?? [],
        readiness: String(workflow.readiness ?? "Needs validation"),
        blockers: workflow.blockers ?? [],
        validator_roles: workflow.validator_roles ?? [
          "Solution architect",
          "UiPath workflow designer",
          "QA/readiness reviewer",
        ],
      },
    });
    edges.push({
      id: `${toBeNode.id}->${id}`,
      source: toBeNode.id,
      target: id,
      kind: "invokes",
      label: "workflow contract",
      desc: "Target-state workflow contract derived from the TO-BE architecture.",
    });
    skillTargets.push({ nodeId: id, tags: ["rpa", "workflow", "uiplan", "contract"] });
  }

  for (const integration of integrations) {
    const id = `${toBeNode.id}::integration:${integration.id}`;
    nodes.set(id, {
      id,
      label: String(integration.label ?? integration.id),
      kind: "integration_contract",
      layer: "uiplan",
      desc: `Pre-build integration contract for ${integration.system ?? integration.label}.`,
      status: "ok",
      meta: {
        system: String(integration.system ?? ""),
        source_view: toBeNode.id,
      },
    });
    skillTargets.push({ nodeId: id, tags: ["integration", "api", "external"] });
    for (const workflowId of integration.used_by_workflow_ids ?? []) {
      const source = workflowIds.get(String(workflowId));
      if (!source) continue;
      edges.push({
        id: `${source}->${id}`,
        source,
        target: id,
        kind: "uses",
        label: "integration contract",
        desc: "Workflow contract depends on this integration contract.",
      });
    }
  }

  for (const resource of orchestrator) {
    const id = `${toBeNode.id}::orchestrator:${resource.id}`;
    nodes.set(id, {
      id,
      label: String(resource.label ?? resource.id),
      kind: "orchestrator_contract",
      layer: "uiplan",
      desc: `Pre-build Orchestrator ${resource.resource_type ?? "resource"} contract for state, data, or evidence.`,
      status: "ok",
      meta: {
        resource_type: String(resource.resource_type ?? ""),
        source_view: toBeNode.id,
      },
    });
    skillTargets.push({ nodeId: id, tags: ["orchestrator", "data", "resource"] });
    for (const workflowId of resource.used_by_workflow_ids ?? []) {
      const source = workflowIds.get(String(workflowId));
      if (!source) continue;
      edges.push({
        id: `${source}->${id}`,
        source,
        target: id,
        kind: "data",
        label: "orchestrator contract",
        desc: "Workflow contract reads or writes this Orchestrator design contract.",
      });
    }
  }

  for (const gate of hitl) {
    const id = `${toBeNode.id}::hitl:${gate.id}`;
    nodes.set(id, {
      id,
      label: String(gate.label ?? gate.id),
      kind: "human_task_contract",
      layer: "uiplan",
      desc: `Pre-build ${gate.channel ?? "human task"} contract for ${gate.actor ?? "business user"}.`,
      status: "ok",
      roles: ["hitl"],
      meta: {
        channel: String(gate.channel ?? ""),
        actor: String(gate.actor ?? ""),
        source_view: toBeNode.id,
      },
    });
    skillTargets.push({ nodeId: id, tags: ["hitl", "human", "app"] });
    edges.push({
      id: `${toBeNode.id}->${id}`,
      source: toBeNode.id,
      target: id,
      kind: "bridge",
      label: "approval task contract",
      desc: "Target-state human review or approval contract.",
    });
  }
}

function planningSkillTargets(
  skill: ProjectNode,
  targets: Array<{ nodeId: string; tags: string[] }>,
): string[] {
  const skillText = `${skill.label} ${skill.desc ?? ""} ${String(skill.meta?.skill_id ?? "")}`.toLowerCase();
  const matched = targets
    .filter((target) => target.tags.some((tag) => skillText.includes(tag)))
    .slice(0, 8)
    .map((target) => target.nodeId);
  return Array.from(new Set(matched));
}

function workflowPlanningLabel(workflow: any): string {
  const bucket = String(workflow.bucket ?? "").toLowerCase();
  const rawLabel = String(workflow.label ?? workflow.id ?? "");
  if (bucket === "intake") return "Intake and routing workflow";
  if (bucket === "processing") {
    const role = workflowRoleLabel(rawLabel);
    return role ? `Approval workflow - ${role}` : "Approval and policy workflow";
  }
  if (bucket === "hitl" || bucket === "review") return "Human review workflow";
  if (bucket === "evidence") return "Evidence and audit workflow";
  return `${titleCase(bucket || "solution")} workflow`;
}

function workflowRoleLabel(label: string): string {
  const cleaned = label
    .replace(/^ApprovalFlow[_\s-]*/i, "")
    .replace(/^Approval[_\s-]*/i, "")
    .replace(/\.xaml$/i, "")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/[_-]+/g, " ")
    .trim();
  return cleaned && cleaned.toLowerCase() !== label.toLowerCase() ? cleaned : "";
}

function titleCase(value: string): string {
  return value
    .split(/\s+|[_-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

function planningNodeDescription(node: ProjectNode): string {
  if (node.kind === "uiplan_view_as_is") {
    const view = node.meta?.view as any;
    const handoffs = Array.isArray(view?.handoffs) ? view.handoffs.length : 0;
    return `Current-state planning view with ${handoffs} manual handoffs.`;
  }
  if (node.kind === "uiplan_view_to_be") {
    const view = node.meta?.view as any;
    const workflows = Array.isArray(view?.workflows) ? view.workflows.length : 0;
    const integrations = Array.isArray(view?.integrations) ? view.integrations.length : 0;
    return `Target-state planning view with ${workflows} workflows and ${integrations} integrations.`;
  }
  if (node.kind === "uiplan_tasks") {
    const total = node.task_summary?.total ?? node.meta?.tasks_total ?? 0;
    const done = node.task_summary?.done ?? node.meta?.tasks_done ?? 0;
    return `Planning task board: ${done}/${total} done.`;
  }
  return node.desc ?? "Planning artifact.";
}

function planningEdgeLabel(node: ProjectNode): string {
  if (node.kind === "uiplan_view_as_is") return "as-is";
  if (node.kind === "uiplan_view_to_be") return "to-be";
  if (node.kind === "uiplan_tasks") return "tasks";
  return "plan";
}

export default function App() {
  // ---- Source folder + mapping state ----
  const [sourcePath, setSourcePath] = useState<string>(() => {
    // Boot URL may carry ?worktree=<path>, set by `uipath-claude explore`.
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const fromUrl = params.get("worktree");
      if (fromUrl) return fromUrl;
    }
    // Default to demo for initial view
    return "demo";
  });
  const [sourcePathInput, setSourcePathInput] = useState<string>("");
  const [mappingInProgress, setMappingInProgress] = useState(false);

  // ---- Graph state ----
  const [rootGraph, setRootGraph] = useState<ProjectGraph>(EMPTY_GRAPH);
  const [graphSource, setGraphSource] = useState<"api" | "sample" | "loading" | "error">("loading");
  const [graphError, setGraphError] = useState<string | undefined>();

  // ---- View state ----
  const [trail, setTrail] = useState<ProjectNode[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [hoveredEdgeId, setHoveredEdgeId] = useState<string | null>(null);
  const [layerFilter, setLayerFilter] = useState<Set<string>>(new Set());
  const [pathFilter] = useState<Set<PathClass>>(new Set());
  const [issuesOnly, setIssuesOnly] = useState(false);
  const [showSkillCoverage, setShowSkillCoverage] = useState(false);
  const [query, setQuery] = useState("");
  const [inspectorCollapsed, setInspectorCollapsed] = useState(false);
  const [selectedSkillId, setSelectedSkillId] = useState<string | null>(null);
  const [autoOpenedUiplan, setAutoOpenedUiplan] = useState(false);
  
  // ---- Collapsed view state ----
  const [viewMode, setViewMode] = useState<"full" | "collapsed">("full");
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [focusedSubgraph, setFocusedSubgraph] = useState<string | null>(null);

  const canvasRef = useRef<CanvasHandle | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const refreshStampRef = useRef<string | null>(null);

  // ---- Auto-load on mount if URL provided path ----
  useEffect(() => {
    if (sourcePath) {
      void loadGraph(sourcePath);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- Load graph for a source path ----
  const loadGraph = useCallback(async (path: string) => {
    setGraphSource("loading");
    setGraphError(undefined);
    setMappingInProgress(true);
    const res: LoadGraphResult = await loadProjectGraph(path);
    setRootGraph(res.graph);
    setGraphSource(res.source);
    setGraphError(res.error);
    setSourcePath(path);
    setTrail([]);
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setHovered(null);
    setHoveredEdgeId(null);
    setSelectedSkillId(null);
    setAutoOpenedUiplan(false);
    setMappingInProgress(false);
  }, []);

  const handleMapFolder = useCallback(() => {
    if (sourcePathInput.trim()) {
      trackUxEvent("map_folder_submit");
      void loadGraph(sourcePathInput.trim());
    }
  }, [sourcePathInput, loadGraph]);

  useEffect(() => {
    refreshStampRef.current = null;
    if (!sourcePath || sourcePath === "demo") return;
    let cancelled = false;
    const check = async () => {
      const res = await loadRefreshState(sourcePath);
      if (cancelled || !res.data?.stamp) return;
      if (refreshStampRef.current === null) {
        refreshStampRef.current = res.data.stamp;
        return;
      }
      if (refreshStampRef.current !== res.data.stamp) {
        refreshStampRef.current = res.data.stamp;
        void loadGraph(sourcePath);
      }
    };
    void check();
    const timer = window.setInterval(check, 2000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [sourcePath, loadGraph]);

  const planningProjectGraph = useMemo(() => buildPlanningProjectGraph(rootGraph), [rootGraph]);

  // ---- Current graph at the active drill-down depth ----
  const currentGraph: ProjectGraph = useMemo(() => {
    if (trail.length === 0) return planningProjectGraph;
    const parent = trail[trail.length - 1];
    return {
      ...planningProjectGraph,
      nodes: parent.children?.nodes ?? [],
      edges: parent.children?.edges ?? [],
      errors: [],
    };
  }, [trail, planningProjectGraph]);

  // Active drill-in bundle, if any. When set, the canvas shows the UiPlan
  // task experience instead of the layered graph.
  const activeBundle: ProjectNode | null = useMemo(() => {
    const head = trail[trail.length - 1];
    return head && head.kind === "uiplan_bundle" ? head : null;
  }, [trail]);

  // Layered-canvas view: for UiPlan projects this is a planning map. It keeps
  // AS-IS / TO-BE / task status visible without pulling implementation code
  // files into the planning surface.
  const layeredGraph: ProjectGraph = useMemo(() => {
    const nodes = currentGraph.nodes.filter((n) => n.kind !== "uiplan_doc");
    const ids = new Set(nodes.map((n) => n.id));
    const edges = currentGraph.edges.filter((e) => ids.has(e.source) && ids.has(e.target));
    return { ...currentGraph, nodes, edges };
  }, [currentGraph]);

  const layout = useMemo(() => {
    // Skip recomputing if layeredGraph is empty (loading state / transient state)
    if (layeredGraph.nodes.length === 0) {
      // Return a minimal empty layout instead of overwriting a good one
      return {
        positions: {},
        buckets: { ui: [], api: [], agent: [], rpa: [], maestro: [], app: [], orchestrator: [], test: [], external: [], skills: [] },
        width: 440,
        height: 180,
        cols: [] as any[],
        colW: 220
      };
    }
    
    return computeLayout(layeredGraph, {
      collapseNonReachable: viewMode === "collapsed",
      expandedIds: expandedNodes,
      maxDepth: 0,  // Show ONLY entry points by default, expand on double-click
      focusedSubgraphId: viewMode === "collapsed" ? focusedSubgraph : null,
    });
  }, [layeredGraph, viewMode, expandedNodes, focusedSubgraph]);

  // Bundles for the pinned left-rail section: top-level uiplan_bundle nodes
  // (and any nested bundles inside the active drill-in).
  const bundles: ProjectNode[] = useMemo(() => {
    const seen = new Map<string, ProjectNode>();
    for (const n of rootGraph.nodes) {
      if (n.kind === "uiplan_bundle") seen.set(n.id, n);
    }
    if (activeBundle && !seen.has(activeBundle.id)) {
      seen.set(activeBundle.id, activeBundle);
    }
    return Array.from(seen.values());
  }, [rootGraph, activeBundle]);

  useEffect(() => {
    if (autoOpenedUiplan || graphSource === "loading" || bundles.length === 0) {
      return;
    }
    // Default to UiPlan flow when bundles exist so users land on planning view.
    if (trail.length === 0) {
      const [bundle] = bundles;
      setTrail([bundle]);
      setSelectedNodeId(bundle.id);
      setSelectedEdgeId(null);
    }
    setAutoOpenedUiplan(true);
  }, [autoOpenedUiplan, graphSource, trail.length, bundles]);

  // ---- Drill-down helpers ----
  const drillInto = useCallback((node: ProjectNode) => {
    // In collapsed mode, double-click focuses on that node's subgraph
    if (viewMode === "collapsed") {
      if (focusedSubgraph === node.id) {
        // Already focused on this node, collapse it
        setFocusedSubgraph(null);
        setExpandedNodes(new Set());
      } else {
        // Focus on this node's subgraph
        setFocusedSubgraph(node.id);
        setExpandedNodes(new Set([node.id]));
      }
      return;
    }
    
    // In full mode, drill into children as before
    setTrail((t) => [...t, node]);
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setHovered(null);
    setHoveredEdgeId(null);
    setQuery("");
  }, [viewMode, focusedSubgraph]);

  const popOne = useCallback(() => {
    setTrail((t) => t.slice(0, -1));
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setHovered(null);
    setHoveredEdgeId(null);
    setQuery("");
  }, []);

  const navigateTo = useCallback((depth: number) => {
    setTrail((t) => t.slice(0, depth));
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setHovered(null);
    setHoveredEdgeId(null);
    setQuery("");
  }, []);

  // ---- Search-driven navigation ----
  const submitSearch = useCallback(() => {
    const q = query.trim().toLowerCase();
    if (!q) return;
    const match = currentGraph.nodes.find((n) =>
      n.label.toLowerCase().includes(q) ||
      n.id.toLowerCase().includes(q) ||
      (n.desc || "").toLowerCase().includes(q));
    if (match) {
      setSelectedNodeId(match.id);
      canvasRef.current?.centerOn(match.id);
      trackUxEvent("search_jump_success");
    }
  }, [query, currentGraph.nodes]);

  // ---- Keyboard navigation ----
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      // ignore typing in inputs/textareas
      const target = e.target as HTMLElement | null;
      const isTyping = target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable);

      if (e.key === "Escape" && !isTyping) {
        if (selectedEdgeId) { setSelectedEdgeId(null); return; }
        if (selectedNodeId) { setSelectedNodeId(null); return; }
        if (trail.length > 0) { popOne(); return; }
      }
      if (e.key === "/" && !isTyping) {
        e.preventDefault();
        searchInputRef.current?.focus();
        searchInputRef.current?.select();
      }
      if (e.key === "Enter" && selectedNodeId && !isTyping) {
        const node = currentGraph.nodes.find((n) => n.id === selectedNodeId);
        if (node?.children && node.children.nodes.length > 0) {
          drillInto(node);
        }
      }
      // Arrow navigation between connected nodes
      if (!isTyping && (e.key === "ArrowRight" || e.key === "ArrowLeft" || e.key === "ArrowUp" || e.key === "ArrowDown") && selectedNodeId) {
        e.preventDefault();
        const outgoing = currentGraph.edges.filter((edge) => edge.source === selectedNodeId);
        const incoming = currentGraph.edges.filter((edge) => edge.target === selectedNodeId);
        let nextId: string | undefined;
        if (e.key === "ArrowRight" && outgoing[0]) nextId = outgoing[0].target;
        else if (e.key === "ArrowLeft" && incoming[0]) nextId = incoming[0].source;
        else if (e.key === "ArrowDown") {
          // move to next node in same column
          const cur = currentGraph.nodes.find((n) => n.id === selectedNodeId);
          if (cur) {
            const col = currentGraph.nodes.filter((n) => n.layer === cur.layer);
            const idx = col.findIndex((n) => n.id === cur.id);
            nextId = col[Math.min(idx + 1, col.length - 1)]?.id;
          }
        } else if (e.key === "ArrowUp") {
          const cur = currentGraph.nodes.find((n) => n.id === selectedNodeId);
          if (cur) {
            const col = currentGraph.nodes.filter((n) => n.layer === cur.layer);
            const idx = col.findIndex((n) => n.id === cur.id);
            nextId = col[Math.max(idx - 1, 0)]?.id;
          }
        }
        if (nextId && nextId !== selectedNodeId) {
          setSelectedNodeId(nextId);
          canvasRef.current?.centerOn(nextId);
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedNodeId, selectedEdgeId, trail.length, popOne, drillInto, currentGraph]);

  // Selecting a node clears edge selection and vice-versa
  const handleSelectNode = (id: string | null) => {
    setSelectedNodeId(id);
    if (id) {
      setSelectedEdgeId(null);
      setSelectedSkillId(null);
      trackUxEvent("node_selected");
    }
  };
  const selectNodeAndCenter = (id: string) => {
    handleSelectNode(id);
    canvasRef.current?.centerOn(id);
  };
  const handleSelectEdge = (id: string | null) => {
    setSelectedEdgeId(id);
    if (id) setSelectedNodeId(null);
  };

  // ---- UiPlan-specific navigation ----
  const onSelectBundle = useCallback((bundleId: string) => {
    const bundle = rootGraph.nodes.find((n) => n.id === bundleId);
    if (!bundle) return;
    setTrail([bundle]);
    setSelectedNodeId(bundleId);
    setSelectedEdgeId(null);
  }, [rootGraph]);

  const onSelectTask = useCallback((taskId: string, bundleId: string) => {
    const bundle = rootGraph.nodes.find((n) => n.id === bundleId);
    if (bundle) setTrail([bundle]);
    setSelectedNodeId(taskId);
    setSelectedEdgeId(null);
  }, [rootGraph]);

  const onJumpToFile = useCallback((path: string) => {
    const id = findFileNodeId(rootGraph, path);
    if (!id) return;
    setTrail([]);
    setSelectedNodeId(id);
    setSelectedEdgeId(null);
    // Defer until the layered canvas mounts.
    setTimeout(() => canvasRef.current?.centerOn(id), 0);
  }, [rootGraph]);

  const toggleLayer = (layer: string) => {
    setLayerFilter((f) => {
      const next = new Set(f);
      if (next.has(layer)) next.delete(layer);
      else next.add(layer);
      return next;
    });
    trackUxEvent("left_rail_layer_toggle", { layer });
  };

  const applyFilterPreset = useCallback((preset: "all" | "core" | "delivery" | "quality") => {
    if (preset === "all") {
      setLayerFilter(new Set());
    } else if (preset === "core") {
      setLayerFilter(new Set(["rpa", "agent", "app", "uiplan"]));
    } else if (preset === "delivery") {
      setLayerFilter(new Set(["uiplan", "orchestrator", "external", "app"]));
    } else if (preset === "quality") {
      setLayerFilter(new Set(["test", "skills", "uiplan"]));
    }
    trackUxEvent("left_rail_filter_preset", { preset });
  }, []);

  const onJumpToSkillNode = useCallback((nodeId: string) => {
    setSelectedSkillId(null);
    setTrail([]);
    setSelectedNodeId(nodeId);
    setSelectedEdgeId(null);
    setTimeout(() => canvasRef.current?.centerOn(nodeId), 0);
  }, []);

  const handleSelectSkill = useCallback((id: string | null) => {
    setSelectedSkillId(id);
    if (id) setSelectedNodeId(null);
  }, []);

  const meta = rootGraph.meta;
  const errorCount = rootGraph.errors?.filter((e) => e.severity === "error").length ?? 0;
  const warnCount = rootGraph.errors?.filter((e) => e.severity === "warn").length ?? 0;
  const activeView = activeBundle ? "uiplan" : "project";
  const openProjectGraph = useCallback(() => {
    trackUxEvent("view_project_map");
    setSelectedSkillId(null);
    setTrail([]);
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
  }, []);
  const openFirstUiplanBundle = useCallback(() => {
    const bundle = bundles[0];
    if (!bundle) return;
    trackUxEvent("view_uiplan_flow");
    setSelectedSkillId(null);
    setTrail([bundle]);
    setSelectedNodeId(bundle.id);
    setSelectedEdgeId(null);
  }, [bundles]);
  return (
    <div style={{
      width: "100%", height: "100dvh",
      background: PALETTE.bg, color: PALETTE.text,
      display: "flex", flexDirection: "column", overflow: "hidden",
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Newsreader:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet" />

      {/* TOP STRIP — real metadata, worktree selector */}
      <div style={{
        minHeight: 56, borderBottom: `1px solid ${PALETTE.rule}`,
        background: PALETTE.panel,
        display: "flex", alignItems: "center", padding: "8px 20px", flexShrink: 0, gap: 16,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ display: "flex", gap: 2 }}>
            {Object.values(LAYERS).slice(0, 4).map((l, i) => (
              <div key={i} style={{ width: 5, height: 14, background: l.color, borderRadius: 1 }} />
            ))}
          </div>
          <div style={{
            fontSize: 12, letterSpacing: "0.32em", fontWeight: 700, color: PALETTE.text,
            fontFamily: "'JetBrains Mono', monospace",
          }}>
            {activeBundle ? "UIPLAN\u00a0\u00b7\u00a0WORKFLOW BUILDER" : "UIPLAN\u00a0\u00b7\u00a0EXPLORER"}
          </div>
        </div>

        {!activeBundle && (
          <>
            <SourceFolderControl
              sourcePath={sourcePath}
              sourcePathInput={sourcePathInput}
              setSourcePathInput={setSourcePathInput}
              mappingInProgress={mappingInProgress}
              onMapFolder={handleMapFolder}
              graphError={graphError}
            />

            <button
              onClick={() => sourcePath && loadGraph(sourcePath)}
              title="Re-map current folder"
              disabled={!sourcePath || mappingInProgress}
              style={{
                background: PALETTE.bg,
                border: `1px solid ${PALETTE.rule}`,
                borderRadius: 8, padding: "8px 12px",
                cursor: sourcePath && !mappingInProgress ? "pointer" : "not-allowed",
                color: PALETTE.text,
                display: "flex", alignItems: "center", gap: 6,
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 12, letterSpacing: "0.1em", fontWeight: 700,
                opacity: sourcePath && !mappingInProgress ? 1 : 0.5,
              }}
            >
              {mappingInProgress
                ? <Loader2 size={11} className="spin" style={{ animation: "spin 1s linear infinite" }} />
                : <RefreshCw size={11} />}
              REFRESH
            </button>
          </>
        )}

        {/* View Mode Toggle */}
        {!activeBundle && <div style={{ display: "flex", gap: 4, border: `1px solid ${PALETTE.rule}`, borderRadius: 4, overflow: "hidden" }}>
          <button
            onClick={() => {
              trackUxEvent("canvas_mode_focus");
              setViewMode("collapsed");
              setExpandedNodes(new Set());
              setFocusedSubgraph(null);
            }}
            style={{
              background: viewMode === "collapsed" ? "#0f766e" : PALETTE.bg,
              border: "none",
              padding: "8px 14px",
              cursor: "pointer",
              color: viewMode === "collapsed" ? "#fff" : PALETTE.text,
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 12,
              letterSpacing: "0.1em",
              fontWeight: 700,
            }}
          >
            FOCUS
          </button>
          <button
            onClick={() => {
              trackUxEvent("canvas_mode_full");
              setViewMode("full");
            }}
            style={{
              background: viewMode === "full" ? "#0f766e" : PALETTE.bg,
              border: "none",
              padding: "8px 14px",
              cursor: "pointer",
              color: viewMode === "full" ? "#fff" : PALETTE.text,
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 12,
              letterSpacing: "0.1em",
              fontWeight: 700,
            }}
          >
            FULL
          </button>
        </div>}

        {!activeBundle && <div style={{
          display: "flex",
          border: `1px solid ${PALETTE.rule}`,
          borderRadius: 5,
          overflow: "hidden",
          flexShrink: 0,
        }}>
          <ViewSwitchButton
            active={activeView === "project"}
            label="PROJECT MAP"
            title="Project map"
            count={layeredGraph.nodes.length}
            Icon={GitBranch}
            onClick={openProjectGraph}
          />
          <ViewSwitchButton
            active={activeView === "uiplan"}
            label="UIPLAN FLOW"
            title="UiPlan flow"
            count={bundles.length}
            Icon={Notebook}
            disabled={bundles.length === 0}
            onClick={openFirstUiplanBundle}
          />
        </div>}

        <div style={{ flex: 1 }} />

        {/* Real metadata strip */}
        <div style={{
          display: "flex", gap: 18, fontSize: 12,
          color: PALETTE.textDim, letterSpacing: "0.12em",
          fontFamily: "'JetBrains Mono', monospace",
          alignItems: "center",
        }}>
          {activeBundle && (
            <span style={{ color: "#0f766e", fontWeight: 800 }}>PRE-BUILD PLAN</span>
          )}
          {!activeBundle && meta?.branch && (
            <span title="Git branch">BRANCH&nbsp;·&nbsp;<span style={{ color: PALETTE.text, fontWeight: 600 }}>{meta.branch}</span></span>
          )}
          {!activeBundle && <span title="Source of the loaded graph" style={{
            color: graphSource === "api" ? "#059669" : graphSource === "sample" ? "#d97706" : PALETTE.textDim,
            fontWeight: 700,
          }}>
            {graphSource === "loading" ? "LOADING" : graphSource === "api" ? "LIVE" : graphSource === "error" ? "ERROR" : "SAMPLE"}
          </span>}
          {!activeBundle && errorCount > 0 && (
            <span style={{ color: "#dc2626", fontWeight: 700 }}>{errorCount} ERR</span>
          )}
          {!activeBundle && warnCount > 0 && (
            <span style={{ color: "#d97706", fontWeight: 700 }}>{warnCount} WARN</span>
          )}
        </div>
      </div>

      {/* MAIN */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden", minHeight: 0 }}>
        <LeftRail
          graph={layeredGraph}
          bundles={bundles}
          selectedNodeId={selectedNodeId}
          query={query} setQuery={setQuery}
          layerFilter={layerFilter} toggleLayer={toggleLayer}
          issuesOnly={issuesOnly} setIssuesOnly={setIssuesOnly}
          showSkillCoverage={showSkillCoverage}
          setShowSkillCoverage={setShowSkillCoverage}
          onSelectNode={selectNodeAndCenter}
          onSelectBundle={onSelectBundle}
          onSelectTask={onSelectTask}
          searchInputRef={searchInputRef}
          onSubmitSearch={submitSearch}
          onApplyFilterPreset={applyFilterPreset}
          isUiplanFlow={!!activeBundle}
        />

        <div style={{ flex: 1, position: "relative", minWidth: 0 }}>
          {graphSource === "loading" && (
            <LoadingOverlay />
          )}
          {graphSource !== "loading" && !activeBundle && layeredGraph.nodes.length === 0 && (
            <EmptyState sourcePath={sourcePath} onRefresh={() => sourcePath && loadGraph(sourcePath)} />
          )}
          {activeBundle && (
            <UiplanCanvas
              key={activeBundle.id}
              bundle={activeBundle}
              selectedNodeId={selectedNodeId}
              onSelectNode={(id) => setSelectedNodeId(id)}
            />
          )}
          {!activeBundle && layeredGraph.nodes.length > 0 && (
            <>
              <Canvas
                ref={canvasRef}
                key={trail.map((t) => t.id).join("/") || sourcePath}
                graph={layeredGraph}
                layout={layout}
                selectedNodeId={selectedNodeId}
                selectedEdgeId={selectedEdgeId}
                hovered={hovered}
                hoveredEdgeId={hoveredEdgeId}
                query={query}
                layerFilter={layerFilter}
                pathFilter={pathFilter}
                issuesOnly={issuesOnly}
                showSkillCoverage={showSkillCoverage}
                expandedIds={expandedNodes}
                focusMode={viewMode === "collapsed"}
                onSelectNode={handleSelectNode}
                onSelectEdge={handleSelectEdge}
                onHoverNode={setHovered}
                onHoverEdge={setHoveredEdgeId}
                onDrillDown={drillInto}
              />
              <ProjectMapGuide
                graph={layeredGraph}
                showSkillCoverage={showSkillCoverage}
                onToggleSkillCoverage={() => setShowSkillCoverage((value) => !value)}
              />
            </>
          )}
          {!activeBundle && <Breadcrumb trail={trail} onNavigate={navigateTo} onBack={popOne} />}
          {graphError && graphSource === "sample" && (
            <div style={{
              position: "absolute", top: 12, right: 12,
              background: "#fffbeb", border: "1px solid #fde68a",
              borderLeft: "3px solid #d97706",
              padding: "8px 12px", borderRadius: 4,
              fontSize: 12, color: "#92400e",
              fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.1em",
              maxWidth: 320,
            }}>
              indexer offline ({graphError}) — showing sample graph
            </div>
          )}
        </div>

        {!activeBundle && (
          <Inspector
            graph={currentGraph}
            rootGraph={rootGraph}
            selectedNodeId={selectedNodeId}
            selectedEdgeId={selectedEdgeId}
            selectedSkillId={selectedSkillId}
            sourcePath={sourcePath}
            collapsed={inspectorCollapsed}
            onToggleCollapsed={() => setInspectorCollapsed((c) => !c)}
            onSelectNode={handleSelectNode}
            onSelectEdge={handleSelectEdge}
            onSelectSkill={handleSelectSkill}
            onJumpToSkillNode={onJumpToSkillNode}
            onDrillDown={drillInto}
            onJumpToFile={onJumpToFile}
          />
        )}
      </div>

      {/* BOTTOM STATUS BAR — actionable signal only */}
      {!activeBundle && <div style={{
        height: 26, borderTop: `1px solid ${PALETTE.rule}`,
        background: PALETTE.panel,
        display: "flex", alignItems: "center", padding: "0 16px",
        fontSize: 12, color: PALETTE.textDim, letterSpacing: "0.14em", flexShrink: 0,
        fontFamily: "'JetBrains Mono', monospace", gap: 18,
      }}>
        {sourcePath && (
          <span>SOURCE&nbsp;·&nbsp;<span style={{ color: PALETTE.text, fontWeight: 600 }}>{shortProjectLabel(sourcePath)}</span></span>
        )}
        {meta?.indexed_at && (
          <span>INDEXED&nbsp;·&nbsp;<span style={{ color: PALETTE.text }}>{formatTimestamp(meta.indexed_at)}</span></span>
        )}
        <span>NODES&nbsp;·&nbsp;<span style={{ color: PALETTE.text }}>
          {viewMode === "collapsed" && layeredGraph.nodes.length !== rootGraph.nodes.length 
            ? `${layeredGraph.nodes.length} / ${rootGraph.nodes.length}` 
            : rootGraph.nodes.length}
        </span></span>
        <span>EDGES&nbsp;·&nbsp;<span style={{ color: PALETTE.text }}>{layeredGraph.edges.length}</span></span>
        {viewMode === "collapsed" && !focusedSubgraph && (
          <span style={{ color: "#0f766e", fontWeight: 700 }}>FOCUS MODE</span>
        )}
        {focusedSubgraph && (
          <span style={{ color: "#0f766e", fontWeight: 700 }}>SUBGRAPH · {focusedSubgraph.split(':').pop()}</span>
        )}
        <span style={{ marginLeft: "auto", color: PALETTE.text, fontWeight: 600 }}>
          {selectedNodeId
            ? `→ ${selectedNodeId}`
            : selectedEdgeId
              ? `~ ${selectedEdgeId}`
              : trail.length > 0
                ? `INSIDE → ${trail[trail.length - 1].id}`
                : "—"}
        </span>
      </div>}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

function SourceFolderControl({
  sourcePath,
  sourcePathInput,
  setSourcePathInput,
  mappingInProgress,
  onMapFolder,
  graphError,
}: {
  sourcePath: string;
  sourcePathInput: string;
  setSourcePathInput: (v: string) => void;
  mappingInProgress: boolean;
  onMapFolder: () => void;
  graphError?: string;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <FolderOpen size={13} color={PALETTE.textDim} />
        <input
          type="text"
          value={sourcePathInput}
          onChange={(e) => setSourcePathInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !mappingInProgress) onMapFolder();
          }}
          placeholder="source folder path..."
          disabled={mappingInProgress}
          style={{
            background: PALETTE.bg,
            border: `1px solid ${PALETTE.rule}`,
            borderRadius: 4,
            padding: "6px 10px",
            fontSize: 12,
            fontFamily: "'JetBrains Mono', monospace",
            color: PALETTE.text,
            fontWeight: 500,
            minWidth: 300,
            outline: "none",
          }}
        />
        <button
          onClick={onMapFolder}
          disabled={!sourcePathInput.trim() || mappingInProgress}
          style={{
            background: "#0f766e",
            border: "none",
            borderRadius: 4,
            padding: "6px 14px",
            cursor: sourcePathInput.trim() && !mappingInProgress ? "pointer" : "not-allowed",
            color: "#fff",
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 12,
            letterSpacing: "0.15em",
            fontWeight: 700,
            opacity: sourcePathInput.trim() && !mappingInProgress ? 1 : 0.5,
          }}
        >
          MAP
        </button>
      </div>
      {sourcePath && (
        <div style={{
          fontSize: 12,
          color: PALETTE.textDim,
          fontFamily: "'JetBrains Mono', monospace",
          maxWidth: 200,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}>
          {shortProjectLabel(sourcePath)}
        </div>
      )}
      {graphError && (
        <div style={{
          fontSize: 12,
          color: "#dc2626",
          fontFamily: "'JetBrains Mono', monospace",
        }}>
          ERROR: {graphError}
        </div>
      )}
    </div>
  );
}

function shortProjectLabel(value: string): string {
  const normalized = value.replace(/\\/g, "/").replace(/\/$/, "");
  return normalized.split("/").filter(Boolean).pop() ?? value;
}

function ViewSwitchButton({
  active, label, title, count, Icon, disabled = false, onClick,
}: {
  active: boolean;
  label: string;
  title: string;
  count: number;
  Icon: React.ComponentType<{ size?: number; strokeWidth?: number }>;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      aria-label={title}
      disabled={disabled}
      style={{
        background: active ? "#ccfbf1" : PALETTE.bg,
        border: "none",
        borderRight: `1px solid ${PALETTE.rule}`,
        padding: "6px 10px",
        cursor: disabled ? "not-allowed" : "pointer",
        color: active ? "#0f766e" : disabled ? PALETTE.textMute : PALETTE.text,
        display: "flex",
        alignItems: "center",
        gap: 6,
        opacity: disabled ? 0.5 : 1,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 12,
        letterSpacing: "0.15em",
        fontWeight: 700,
      }}
    >
      <Icon size={11} strokeWidth={2.1} />
      {label}
      <span style={{
        background: active ? "#0f766e22" : PALETTE.panel,
        color: active ? "#0f766e" : PALETTE.textDim,
        padding: "1px 6px",
        borderRadius: 3,
        fontSize: 12,
        letterSpacing: "0.05em",
      }}>
        {String(count).padStart(2, "0")}
      </span>
    </button>
  );
}

function ProjectMapGuide({
  graph,
  showSkillCoverage,
  onToggleSkillCoverage,
}: {
  graph: ProjectGraph;
  showSkillCoverage: boolean;
  onToggleSkillCoverage: () => void;
}) {
  const solutionNodes = graph.nodes.filter((node) =>
    ["uipath_design_contract", "integration_contract", "orchestrator_contract", "human_task_contract"].includes(node.kind)
    || String(node.layer) === "uiplan",
  ).length;
  const skillNodes = graph.nodes.filter((node) => node.kind === "skill").length;
  const solutionEdges = graph.edges.filter((edge) => edge.kind !== "covers").length;
  const coverageEdges = graph.edges.filter((edge) => edge.kind === "covers").length;

  return (
    <div style={{
      position: "absolute",
      top: 12,
      left: 12,
      zIndex: 6,
      width: 340,
      background: "#fffffff2",
      border: `1px solid ${PALETTE.rule}`,
      borderRadius: 10,
      boxShadow: "0 8px 24px rgba(15, 23, 42, 0.08)",
      padding: 12,
      pointerEvents: "auto",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 9 }}>
        <Network size={15} color="#0f766e" />
        <div style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 12,
          letterSpacing: "0.16em",
          color: "#0f766e",
          fontWeight: 800,
        }}>
          PROJECT MAP EXPLAINER
        </div>
      </div>
      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: 7,
        marginBottom: 10,
      }}>
        <GuideStat Icon={Code2} label="Plan contracts" value={solutionNodes} />
        <GuideStat Icon={GitBranch} label="Contract links" value={solutionEdges} />
        <GuideStat Icon={Sparkles} label="Skills" value={skillNodes} />
        <GuideStat Icon={Network} label="Coverage links" value={coverageEdges} />
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <GuideLegend color={LAYERS.rpa.color} label="Workflows" detail="pre-build UiPath design contracts" />
        <GuideLegend color={LAYERS.external.color} label="APIs" detail="integration contracts to validate before generation" />
        <GuideLegend color={LAYERS.skills.color} label="Skills" detail="assistant guidance that governs the node" />
      </div>
      <button
        onClick={onToggleSkillCoverage}
        style={{
          marginTop: 10,
          width: "100%",
          border: `1px solid ${showSkillCoverage ? "#8b5cf6" : PALETTE.rule}`,
          background: showSkillCoverage ? "#f3e8ff" : PALETTE.bg,
          color: showSkillCoverage ? "#6d28d9" : PALETTE.text,
          borderRadius: 6,
          padding: "8px 10px",
          cursor: "pointer",
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 12,
          letterSpacing: "0.12em",
          fontWeight: 800,
        }}
      >
        {showSkillCoverage ? "HIDE SKILL COVERAGE LINKS" : "SHOW SKILL COVERAGE LINKS"}
      </button>
    </div>
  );
}

function GuideStat({
  Icon,
  label,
  value,
}: {
  Icon: React.ComponentType<{ size?: number; color?: string }>;
  label: string;
  value: number;
}) {
  return (
    <div style={{
      border: `1px solid ${PALETTE.rule}`,
      background: PALETTE.bg,
      borderRadius: 6,
      padding: "7px 8px",
      display: "flex",
      alignItems: "center",
      gap: 7,
    }}>
      <Icon size={12} color="#0f766e" />
      <span style={{ flex: 1, fontSize: 12, color: PALETTE.textDim }}>{label}</span>
      <span style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 12,
        fontWeight: 800,
        color: PALETTE.text,
      }}>
        {value}
      </span>
    </div>
  );
}

function GuideLegend({ color, label, detail }: { color: string; label: string; detail: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ width: 22, height: 3, borderRadius: 999, background: color }} />
      <span style={{ minWidth: 72, fontSize: 12, fontWeight: 700, color: PALETTE.text }}>{label}</span>
      <span style={{ fontSize: 12, color: PALETTE.textDim }}>{detail}</span>
    </div>
  );
}

function LoadingOverlay() {
  return (
    <div style={{
      position: "absolute", inset: 0,
      display: "flex", alignItems: "center", justifyContent: "center",
      background: PALETTE.bg, zIndex: 5,
      flexDirection: "column", gap: 12,
      color: PALETTE.textDim,
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: 12, letterSpacing: "0.18em",
    }}>
      <Loader2 size={20} style={{ animation: "spin 1s linear infinite" }} />
      <span>INDEXING PROJECT…</span>
    </div>
  );
}

function EmptyState({ sourcePath, onRefresh }: { sourcePath: string; onRefresh: () => void }) {
  return (
    <div style={{
      position: "absolute", inset: 0,
      display: "flex", alignItems: "center", justifyContent: "center",
      flexDirection: "column", gap: 16,
      color: PALETTE.textDim, padding: 32,
    }}>
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 12, letterSpacing: "0.22em", fontWeight: 700,
        color: PALETTE.text,
      }}>
        NO NODES IN THIS VIEW
      </div>
      <div style={{
        fontFamily: "'Newsreader', Georgia, serif",
        fontSize: 13, fontStyle: "italic", maxWidth: 360, textAlign: "center", lineHeight: 1.5,
      }}>
        The current source folder (<span style={{ color: PALETTE.text }}>{sourcePath}</span>) returned no graph.
        Either no project files matched the indexer, or the sub-graph has no children.
      </div>
      <button onClick={onRefresh} style={{
        background: PALETTE.panel, border: `1px solid ${PALETTE.rule}`,
        borderRadius: 4, padding: "8px 16px", cursor: "pointer",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 12, letterSpacing: "0.18em", fontWeight: 700,
        color: PALETTE.text,
        display: "flex", alignItems: "center", gap: 8,
      }}>
        <RefreshCw size={11} />
        RE-INDEX
      </button>
    </div>
  );
}

function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso);
    const diffMs = Date.now() - d.getTime();
    const sec = Math.floor(diffMs / 1000);
    if (sec < 5) return "just now";
    if (sec < 60) return `${sec}s ago`;
    if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
    if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
    return d.toLocaleDateString();
  } catch {
    return iso;
  }
}
