import type { LayerKey } from "./projectGraph/types";
import type { ProjectGraph, ProjectNode, ProjectEdge } from "./projectGraph/types";

export interface Layout {
  positions: Record<string, { x: number; y: number }>;
  buckets: Record<LayerKey, ProjectNode[]>;
  width: number;
  height: number;
  cols: LayerKey[];
  colW: number;
}

export interface LayoutOptions {
  /** Only show nodes reachable from entry points (collapsed view) */
  collapseNonReachable?: boolean;
  /** Expanded node IDs (show their immediate children) */
  expandedIds?: Set<string>;
  /** Maximum depth from entry points */
  maxDepth?: number;
  /** Focus on a specific node's subgraph (show only that node + children) */
  focusedSubgraphId?: string | null;
}

/**
 * Visual ordering of layers, left-to-right. Includes every layer the model
 * supports; layers with no nodes are dropped from the rendered columns so the
 * canvas stays compact when the project doesn't exercise every surface.
 */
const ALL_LAYERS: LayerKey[] = [
  "ui",
  "api",
  "agent",
  "maestro",
  "app",
  "rpa",
  "orchestrator",
  "test",
  "uiplan",
  "external",
  "skills",
];
const COL_W = 280;  // Horizontal spacing between nodes
const ROW_H = 140;  // Vertical spacing between nodes
const PAD_X = 80;
const PAD_Y = 100;
const SKILLS_ROWS_PER_COLUMN = 8;

export function computeLayout(graph: ProjectGraph, options: LayoutOptions = {}): Layout {
  const { collapseNonReachable = false, expandedIds = new Set(), maxDepth = 2, focusedSubgraphId = null } = options;
  
  // Filter visible nodes
  let visibleNodes = graph.nodes;
  let visibleEdges = graph.edges;
  if (focusedSubgraphId) {
    // Subgraph focus: show only the focused node + its children (no other layers)
    visibleNodes = getSubgraphNodes(graph, focusedSubgraphId);
    visibleEdges = graph.edges.filter(e => 
      visibleNodes.some(n => n.id === e.source) && 
      visibleNodes.some(n => n.id === e.target)
    );
  } else if (collapseNonReachable) {
    // Collapsed view: show entry points + expanded children
    visibleNodes = getVisibleNodesCollapsed(graph, expandedIds, maxDepth);
    visibleEdges = graph.edges.filter(e => 
      visibleNodes.some(n => n.id === e.source) && 
      visibleNodes.some(n => n.id === e.target)
    );
  }
  
  // Detect if this is an RPA workflow (look for business logic properties)
  // First, flatten to check children nodes too
  const allNodesToCheck = [...visibleNodes];
  visibleNodes.forEach(n => {
    if (n.children?.nodes) {
      allNodesToCheck.push(...n.children.nodes);
    }
  });
  
  const isRpaWorkflow = allNodesToCheck.some(n => 
    n.is_container || n.is_activity || n.business_logic_level
  );
  
  // Use hierarchical layout for subgraph, RPA workflows, or collapsed with expandedIds
  if (focusedSubgraphId || isRpaWorkflow || (collapseNonReachable && expandedIds.size > 0)) {
    return computeHierarchicalLayout(visibleNodes, visibleEdges);
  }
  
  // Default layer-based layout for non-RPA projects
  const buckets: Record<LayerKey, ProjectNode[]> = {
    ui: [], api: [], agent: [], rpa: [],
    maestro: [], app: [], orchestrator: [], test: [],
    uiplan: [], external: [], skills: [],
  };
  visibleNodes.forEach((n) => {
    const layer = (ALL_LAYERS.includes(n.layer as LayerKey) ? n.layer : "external") as LayerKey;
    buckets[layer].push(n);
  });
  const ORDER: LayerKey[] = ALL_LAYERS.filter((l) => buckets[l].length > 0);
  if (ORDER.length === 0) ORDER.push("ui");
  const positions: Record<string, { x: number; y: number }> = {};
  let colOffset = 0;
  let totalCols = 0;
  let maxRows = 0;
  ORDER.forEach((layer) => {
    const rowsPerColumn = layer === "skills" ? SKILLS_ROWS_PER_COLUMN : Math.max(buckets[layer].length, 1);
    const colSpan = Math.max(1, Math.ceil(buckets[layer].length / rowsPerColumn));
    buckets[layer].forEach((node, ri) => {
      const localCol = Math.floor(ri / rowsPerColumn);
      const localRow = ri % rowsPerColumn;
      positions[node.id] = {
        x: PAD_X + (colOffset + localCol) * COL_W,
        y: PAD_Y + localRow * ROW_H,
      };
    });
    maxRows = Math.max(maxRows, Math.min(buckets[layer].length, rowsPerColumn));
    colOffset += colSpan;
    totalCols += colSpan;
  });
  return {
    positions,
    buckets,
    width: PAD_X + totalCols * COL_W + 80,
    height: PAD_Y + maxRows * ROW_H + 80,
    cols: ORDER,
    colW: COL_W,
  };
}

/**
 * n8n-style left-to-right sequential flow layout.
 * Uses topological sort to follow actual workflow execution order.
 */
function computeHierarchicalLayout(
  nodes: ProjectNode[],
  edges: ProjectEdge[]
): Layout {
  if (nodes.length === 0) {
    return {
      positions: {},
      buckets: { ui: [], api: [], agent: [], rpa: [], maestro: [], app: [], orchestrator: [], test: [], uiplan: [], external: [], skills: [] },
      width: 800,
      height: 600,
      cols: [],
      colW: COL_W,
    };
  }
  
  // Flatten children nodes into the main list (new structure has nodes with children)
  const allNodes: ProjectNode[] = [];
  nodes.forEach(node => {
    allNodes.push(node);
    if (node.children?.nodes) {
      allNodes.push(...node.children.nodes);
    }
  });
  
  // Separate by business logic level (use new properties)
  const integrationNodes = allNodes.filter(n => n.business_logic_level === "integration");
  const activityNodes = allNodes.filter(n => n.is_activity && n.business_logic_level === "activity");
  const entryNodes = allNodes.filter(n => n.is_entry || n.business_logic_level === "entry");
  const processNodes = allNodes.filter(n => n.is_container || n.business_logic_level === "process");
  const controlNodes = allNodes.filter(n => n.control_flow_type);
  
  
  // Build main flow - start with INPUT nodes (the .xaml files) to ensure they get positioned
  const mainFlow: ProjectNode[] = [];
  const visited = new Set<string>();
  
  // First, add the parent workflow nodes (the input nodes themselves - the .xaml files)
  // These should form the main left-to-right flow
  const parentWorkflows = nodes.filter(n => !n.is_activity && !n.business_logic_level);
  parentWorkflows.forEach(n => {
    mainFlow.push(n);
    visited.add(n.id);
  });
  
  // Then add entry nodes from children (TaskNodes, etc.) 
  entryNodes.forEach(n => {
    if (!visited.has(n.id)) {
      visited.add(n.id);
      // Don't add to mainFlow - they'll be positioned relative to parents
    }
  });
  
  // Build adjacency map
  const nextMap = new Map<string, string[]>();
  edges.forEach(e => {
    if (e.kind === "transition") {
      if (!nextMap.has(e.source)) nextMap.set(e.source, []);
      nextMap.get(e.source)!.push(e.target);
    }
  });
  
  // BFS to follow transition edges
  const queue: string[] = [...entryNodes.map(n => n.id)];
  while (queue.length > 0 && mainFlow.length < 15) {
    const nodeId = queue.shift()!;
    const children = nextMap.get(nodeId) || [];
    
    children.forEach(childId => {
      if (!visited.has(childId)) {
        visited.add(childId);
        const childNode = allNodes.find(n => n.id === childId);
        if (childNode && (childNode.is_container || childNode.business_logic_level === "process")) {
          mainFlow.push(childNode);
          queue.push(childId);
        }
      }
    });
  }
  
  // If no main flow, use process nodes or fallback to all nodes
  if (mainFlow.length === 0) {
    if (processNodes.length > 0) {
      mainFlow.push(...processNodes.slice(0, 10));
    } else {
      // Fallback: show all non-activity nodes
      mainFlow.push(...allNodes.filter(n => !n.is_activity).slice(0, 10));
    }
  }
  
  // Layout (n8n-style: left-to-right main flow)
  const positions: Record<string, {x: number; y: number}> = {};
  const HORIZONTAL_SPACING = 280;
  const VERTICAL_SPACING = 140;
  const PAD_X = 100;
  const PAD_Y = 120;
  let currentX = PAD_X;
  let maxY = PAD_Y;
  
  // Position main flow left-to-right
  mainFlow.forEach((node) => {
    positions[node.id] = { x: currentX, y: PAD_Y };
    currentX += HORIZONTAL_SPACING;
  });
  
  // Position control flow nodes below their parent
  controlNodes.forEach((node) => {
    const incomingEdge = edges.find(e => e.target === node.id);
    const parentPos = incomingEdge ? positions[incomingEdge.source] : null;
    
    if (parentPos) {
      positions[node.id] = {
        x: parentPos.x + 40,
        y: parentPos.y + VERTICAL_SPACING
      };
      maxY = Math.max(maxY, positions[node.id].y + 100);
    }
  });
  
  // Position integrations near usage
  integrationNodes.forEach((node, index) => {
    const usageEdge = edges.find(e => e.target === node.id && e.kind === "uses");
    const userPos = usageEdge ? positions[usageEdge.source] : null;
    
    if (userPos) {
      positions[node.id] = {
        x: userPos.x + HORIZONTAL_SPACING * 0.65,
        y: userPos.y + 110
      };
    } else {
      positions[node.id] = {
        x: PAD_X + index * 220,
        y: maxY + 60
      };
    }
    maxY = Math.max(maxY, positions[node.id].y + 80);
  });
  
  // Position activities near their parent workflow
  activityNodes.forEach((node, index) => {
    // Try to find parent by task_node reference first
    if (node.parent_task_node && positions[node.parent_task_node]) {
      const parentPos = positions[node.parent_task_node];
      positions[node.id] = { x: parentPos.x + 10, y: parentPos.y + 90 };
    } else {
      // Find parent workflow by ID prefix (e.g., "rpa:File.xaml::activity-0" -> "rpa:File.xaml")
      const parentId = node.id.split('::')[0];
      const parentPos = positions[parentId];
      if (parentPos) {
        // Stack activities vertically below parent, with slight horizontal offset per index
        positions[node.id] = { 
          x: parentPos.x + (index % 3) * 30, 
          y: parentPos.y + 80 + Math.floor(index / 3) * 50 
        };
        maxY = Math.max(maxY, positions[node.id].y + 50);
      } else {
        // Fallback: position off-canvas (will expand on demand)
        positions[node.id] = { x: -1000, y: -1000 };
      }
    }
  });
  
  const result = {
    positions,
    buckets: { 
      ui: [], api: [], agent: [], rpa: nodes,
      maestro: [], app: [], orchestrator: [], test: [], uiplan: [], external: [], skills: []
    },
    width: currentX + PAD_X,
    height: maxY + PAD_Y,
    cols: ["rpa"],
    colW: HORIZONTAL_SPACING,
  };
  
  return result;
}

/**
 * Get only the subgraph: the focused node + its immediate children.
 * No skills, no other layers - just the focused subgraph.
 */
function getSubgraphNodes(
  graph: ProjectGraph,
  focusedNodeId: string
): ProjectNode[] {
  const visible = new Set<string>();
  visible.add(focusedNodeId);
  
  // Build adjacency map from edges
  const childrenMap = new Map<string, Set<string>>();
  graph.edges.forEach((e) => {
    if (e.kind === "invokes" || e.kind === "calls" || e.kind === "uses" || e.kind === "imports") {
      if (!childrenMap.has(e.source)) childrenMap.set(e.source, new Set());
      childrenMap.get(e.source)!.add(e.target);
    }
  });
  
  // Add all children of the focused node
  const children = childrenMap.get(focusedNodeId);
  if (children) {
    children.forEach(childId => visible.add(childId));
  }
  
  return graph.nodes.filter(n => visible.has(n.id));
}

/**
 * Get visible nodes in collapsed view: entry points + nodes within maxDepth hops,
 * plus all nodes connected to expanded nodes.
 */
function getVisibleNodesCollapsed(
  graph: ProjectGraph,
  expandedIds: Set<string>,
  maxDepth: number
): ProjectNode[] {
  // Find entry points - ONLY nodes explicitly marked as entry points
  const entryPoints = graph.nodes.filter((n) => 
    n.roles?.includes("entrypoint") || (n as any).is_entry
  );
  
  // If no entry points found, fall back to showing "workflow" kind
  const actualEntryPoints = entryPoints.length > 0 
    ? entryPoints 
    : graph.nodes.filter(n => n.kind === "workflow");
  
  // Build adjacency map from edges
  const childrenMap = new Map<string, Set<string>>();
  graph.edges.forEach((e) => {
    // Only track "invokes", "calls", "uses" edges (not "covers" from skills)
    if (e.kind === "invokes" || e.kind === "calls" || e.kind === "uses" || e.kind === "imports") {
      if (!childrenMap.has(e.source)) childrenMap.set(e.source, new Set());
      childrenMap.get(e.source)!.add(e.target);
    }
  });
  
  // BFS from entry points
  const visible = new Set<string>();
  const queue: Array<{id: string; depth: number}> = actualEntryPoints.map(n => ({id: n.id, depth: 0}));
  const visited = new Set<string>();
  
  while (queue.length > 0) {
    const {id, depth} = queue.shift()!;
    if (visited.has(id)) continue;
    visited.add(id);
    visible.add(id);
    
    // Show children if:
    // 1. This node is explicitly expanded, OR
    // 2. We haven't hit maxDepth yet
    const shouldExpand = expandedIds.has(id) || depth < maxDepth;
    if (shouldExpand) {
      const children = childrenMap.get(id);
      if (children) {
        children.forEach(childId => {
          if (!visited.has(childId)) {
            queue.push({id: childId, depth: depth + 1});
          }
        });
      }
    }
  }
  
  // Always include skills layer for context
  graph.nodes.forEach(n => {
    if (n.layer === "skills") visible.add(n.id);
  });
  
  return graph.nodes.filter(n => visible.has(n.id));
}
