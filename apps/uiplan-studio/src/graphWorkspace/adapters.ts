import type { DiagramData, DiagramNodeKind } from "../types";

import type { GraphWorkspaceV2 } from "./types";

export function toDiagramData(workspace: GraphWorkspaceV2): DiagramData {
  return {
    nodes: workspace.nodes.map((node, index) => ({
      id: node.id,
      title: node.title,
      kind: toDiagramNodeKind(node.type),
      description: node.summary ?? "",
      code: node.code ?? undefined,
      concept: node.concept ?? undefined,
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

function toDiagramNodeKind(nodeType: string): DiagramNodeKind {
  switch (nodeType) {
    case "doc":
      return "document";
    case "workflow":
      return "workflow";
    case "skill":
      return "skill";
    case "book_section":
      return "library";
    case "review_gate":
      return "review";
    case "source_file":
      return "workflow";
    default:
      return "workflow";
  }
}
