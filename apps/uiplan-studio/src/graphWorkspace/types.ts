export interface GraphNodeV2 {
  id: string;
  type: string;
  title: string;
  summary?: string;
}

export interface GraphEdgeV2 {
  id: string;
  type: string;
  source: string;
  target: string;
  label?: string;
}

export interface GraphWorkspaceV2 {
  version: string;
  nodes: GraphNodeV2[];
  edges: GraphEdgeV2[];
}
