import {
  Bot,
  Box,
  CheckSquare,
  Cloud,
  Code2,
  Cog,
  CornerDownRight,
  Database,
  FileCode,
  FileText,
  GitBranch,
  Layers,
  LayoutGrid,
  ListChecks,
  ListTree,
  Notebook,
  Server,
  ShieldCheck,
  Sparkles,
  TestTube,
  Workflow,
  Zap,
} from "lucide-react";
import type { ComponentType } from "react";
import type {
  BusinessStatus,
  EdgeKind,
  LayerKey,
  NodeStatus,
  PathClass,
} from "./projectGraph/types";

export const PALETTE = {
  bg: "#fafaf7",
  panel: "#ffffff",
  panelAlt: "#f5f5f0",
  rule: "#e5e5e0",
  ruleSoft: "#f0f0eb",
  text: "#1a1a1a",
  textDim: "#6b6b6b",
  textMute: "#757575",
  ink: "#0a0a0a",
};

type IconCmp = ComponentType<{ size?: number; color?: string; strokeWidth?: number }>;

export interface LayerInfo {
  name: string;
  color: string;
  soft: string;
  short: string;
  Icon: IconCmp;
}

export const LAYERS: Record<LayerKey, LayerInfo> = {
  ui:           { name: "ui",           color: "#d97706", soft: "#fef3c7", short: "UI",  Icon: Code2 },
  api:          { name: "api",          color: "#2563eb", soft: "#dbeafe", short: "API", Icon: Zap },
  agent:        { name: "agent",        color: "#7c3aed", soft: "#ede9fe", short: "AGT", Icon: Bot },
  rpa:          { name: "rpa",          color: "#059669", soft: "#d1fae5", short: "RPA", Icon: Workflow },
  maestro:      { name: "maestro",      color: "#0891b2", soft: "#cffafe", short: "MAE", Icon: GitBranch },
  app:          { name: "app",          color: "#db2777", soft: "#fce7f3", short: "APP", Icon: LayoutGrid },
  orchestrator: { name: "orchestrator", color: "#475569", soft: "#e2e8f0", short: "ORC", Icon: Server },
  test:         { name: "test",         color: "#65a30d", soft: "#ecfccb", short: "TST", Icon: TestTube },
  external:     { name: "external",     color: "#dc2626", soft: "#fee2e2", short: "EXT", Icon: Cloud },
  skills:       { name: "skills",       color: "#8b5cf6", soft: "#f3e8ff", short: "SKL", Icon: Sparkles },
  uiplan:       { name: "uiplan",       color: "#0f766e", soft: "#ccfbf1", short: "PLN", Icon: Notebook },
};

export function getLayer(layer: string | undefined): LayerInfo {
  if (layer && (layer in LAYERS)) return LAYERS[layer as LayerKey];
  return LAYERS.external;
}

export const KIND_ICONS: Record<string, IconCmp> = {
  file: FileCode,
  endpoint: Zap,
  module: Box,
  agent_node: Bot,
  tool: Cog,
  workflow: Workflow,
  activity: Layers,
  function: CornerDownRight,
  flow: GitBranch,
  case: ListTree,
  coded_app: LayoutGrid,
  action_app: LayoutGrid,
  queue: Server,
  asset: ShieldCheck,
  process: Workflow,
  folder: ListTree,
  entity: Database,
  test_case: TestTube,
  test_set: TestTube,
  doc: FileText,
  skill: Sparkles,
  uiplan_bundle: Notebook,
  uiplan_doc: FileText,
  uiplan_tasks: ListChecks,
  uiplan_task: CheckSquare,
  external: Cloud,                    // External integrations
  orchestrator_resource: Server,      // Orchestrator resources (Queue, Asset, etc.)
  task_node: Box,                     // TaskNode containers
  subprocess: GitBranch,              // ProcessDiagram subprocesses
  control_flow: GitBranch,            // If/Switch/ForEach nodes
};

export interface EdgeStyle {
  color: string;
  dash: string;
  width: number;
  label: string;
}

export const EDGE_STYLE: Record<EdgeKind, EdgeStyle> = {
  import:      { color: "#9ca3af", dash: "4 3", width: 1.2, label: "import" },
  call:        { color: "#2563eb", dash: "0",   width: 1.5, label: "call" },
  invokes:     { color: "#7c3aed", dash: "0",   width: 1.8, label: "invoke" },
  transition:  { color: "#525252", dash: "0",   width: 2.0, label: "next" },      // Thicker for main flow
  bridge:      { color: "#dc2626", dash: "6 3", width: 2,   label: "bridge" },
  queue:       { color: "#0891b2", dash: "1 3", width: 1.5, label: "queue" },
  publish:     { color: "#db2777", dash: "0",   width: 1.5, label: "publish" },
  data:        { color: "#10b981", dash: "4 2", width: 1.2, label: "data" },      // Green dashed for data flow
  covers:      { color: "#8b5cf6", dash: "7 4", width: 1.2, label: "covers" },
  uses:        { color: "#ef4444", dash: "2 2", width: 1.3, label: "uses" },      // Lighter gray for integration usage
  conditional: { color: "#f59e0b", dash: "0",   width: 1.8, label: "branch" },    // Orange for conditional branches
};

export function getEdgeStyle(kind: string | undefined): EdgeStyle {
  if (kind && (kind in EDGE_STYLE)) return EDGE_STYLE[kind as EdgeKind];
  return EDGE_STYLE.transition;
}

export const STATUS_COLOR: Record<NodeStatus, string> = {
  ok: "#059669",
  warn: "#d97706",
  error: "#dc2626",
  stale: "#9ca3af",
  draft: "#7c3aed",
};

export const BUSINESS_STATUS_COLOR: Record<BusinessStatus, string> = {
  drafted: "#9ca3af",
  approved: "#2563eb",
  "in-build": "#d97706",
  live: "#059669",
  retired: "#525252",
};

export const PATH_CLASS_COLOR: Record<PathClass, { color: string; label: string }> = {
  happy:     { color: "#059669", label: "happy path" },
  exception: { color: "#dc2626", label: "exception" },
  loopback:  { color: "#d97706", label: "loopback" },
  alt:       { color: "#2563eb", label: "alternative" },
};

export const NODE_W = 240;  // Wider for n8n-style cards
export const NODE_H = 80;   // Taller for better readability
