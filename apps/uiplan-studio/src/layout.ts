import type { LayerKey } from "./projectGraph/types";
import type { ProjectGraph, ProjectNode } from "./projectGraph/types";

export interface Layout {
  positions: Record<string, { x: number; y: number }>;
  buckets: Record<LayerKey, ProjectNode[]>;
  width: number;
  height: number;
  cols: LayerKey[];
  colW: number;
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
  "external",
  "skills",
];
const COL_W = 300;
const ROW_H = 110;
const PAD_X = 60;
const PAD_Y = 80;

export function computeLayout(graph: ProjectGraph): Layout {
  const buckets: Record<LayerKey, ProjectNode[]> = {
    ui: [], api: [], agent: [], rpa: [],
    maestro: [], app: [], orchestrator: [], test: [],
    external: [], skills: [],
  };
  graph.nodes.forEach((n) => {
    const layer = (ALL_LAYERS.includes(n.layer as LayerKey) ? n.layer : "external") as LayerKey;
    buckets[layer].push(n);
  });
  const ORDER: LayerKey[] = ALL_LAYERS.filter((l) => buckets[l].length > 0);
  if (ORDER.length === 0) ORDER.push("ui");
  const positions: Record<string, { x: number; y: number }> = {};
  ORDER.forEach((layer, ci) => {
    buckets[layer].forEach((node, ri) => {
      positions[node.id] = { x: PAD_X + ci * COL_W, y: PAD_Y + ri * ROW_H };
    });
  });
  const maxRows = Math.max(0, ...ORDER.map((l) => buckets[l].length));
  return {
    positions,
    buckets,
    width: PAD_X + ORDER.length * COL_W + 80,
    height: PAD_Y + maxRows * ROW_H + 80,
    cols: ORDER,
    colW: COL_W,
  };
}
