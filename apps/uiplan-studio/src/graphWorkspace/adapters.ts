import type { DiagramData } from "../types";

import type { GraphWorkspaceV2 } from "./types";

export function toDiagramData(workspace: GraphWorkspaceV2): DiagramData {
  return {
    nodes: workspace.nodes.map((node, index) => ({
      id: node.id,
      title: node.title,
      kind: "workflow",
      description: node.summary ?? "",
      x: index * 240,
      y: 80,
    })),
    edges: workspace.edges.map((edge) => ({
      id: edge.id,
      from: edge.source,
      to: edge.target,
      label: edge.label ?? "",
      edge_type: edge.type,
    })),
  };
}
