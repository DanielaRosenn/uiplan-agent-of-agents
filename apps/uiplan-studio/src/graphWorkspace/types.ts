export interface GraphNodeV2 {
  id: string;
  type: string;
  title: string;
  summary?: string;
  code?: {
    path: string;
    lines: string;
    snippet: string;
    language: string;
  } | null;
  concept?: string | null;
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
