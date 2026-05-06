import { normalizeProjectGraph, type ProjectGraph, type ProjectGraphInput } from "./types";

export interface ProjectGraphTemplateMetadata {
  id: string;
  title: string;
  description: string;
  tags: string[];
  nodeCount: number;
  recommendedLayout: {
    direction: "LR" | "TB";
    style: string;
    layers: string[];
    layerMetadata: Record<string, { label: string; rank: number }>;
  };
  iconHints: Record<string, string>;
}

const templateSource = "projectGraph.starterTemplate";

export const starterProjectGraphTemplateMetadata: ProjectGraphTemplateMetadata = {
  id: "visual-template",
  title: "Starter Agent Canvas",
  description:
    "Compact trigger-to-agent starter canvas with context helpers and a readiness branch.",
  tags: ["starter", "agent", "n8n-like", "visual-builder"],
  nodeCount: 8,
  recommendedLayout: {
    direction: "LR",
    style: "compact-card-workflow",
    layers: ["trigger", "agent", "context", "decision", "outcome"],
    layerMetadata: {
      trigger: { label: "Trigger", rank: 1 },
      agent: { label: "Agent", rank: 2 },
      context: { label: "Helper Context", rank: 3 },
      decision: { label: "Decision", rank: 4 },
      outcome: { label: "Outcome", rank: 5 },
    },
  },
  iconHints: {
    chat_trigger: "trigger",
    planning_agent: "agent",
    context_library: "library",
    skills: "skill",
    tools: "tool",
    if_ready: "decision",
    success_package: "package",
    needs_context: "context-warning",
  },
};

const starterTemplateInput: ProjectGraphInput = {
  projectType: "solution",
  nodes: [
    {
      id: "chat_trigger",
      label: "Chat Trigger",
      kind: "process_step",
      layer: "trigger",
      metadata: {
        source: templateSource,
        visualRole: "trigger",
        iconHint: "trigger",
        cardDensity: "compact",
        positionHint: { x: 0, y: 0 },
      },
    },
    {
      id: "planning_agent",
      label: "Planning Agent",
      kind: "project_component",
      layer: "agent",
      metadata: {
        source: templateSource,
        visualRole: "central_action",
        iconHint: "agent",
        cardDensity: "compact",
        positionHint: { x: 280, y: 0 },
      },
    },
    {
      id: "context_library",
      label: "Context Library",
      kind: "docs_context",
      layer: "context",
      metadata: {
        source: templateSource,
        visualRole: "helper_context",
        iconHint: "library",
        cardDensity: "compact",
        positionHint: { x: 200, y: 170 },
      },
    },
    {
      id: "skills",
      label: "Skills",
      kind: "skill",
      layer: "context",
      metadata: {
        source: templateSource,
        visualRole: "helper_context",
        iconHint: "skill",
        cardDensity: "compact",
        positionHint: { x: 360, y: 170 },
      },
    },
    {
      id: "tools",
      label: "Tools",
      kind: "tool",
      layer: "context",
      metadata: {
        source: templateSource,
        visualRole: "helper_context",
        iconHint: "tool",
        cardDensity: "compact",
        positionHint: { x: 520, y: 170 },
      },
    },
    {
      id: "if_ready",
      label: "Ready?",
      kind: "review_gate",
      layer: "decision",
      metadata: {
        source: templateSource,
        visualRole: "decision_branch",
        iconHint: "decision",
        cardDensity: "compact",
        positionHint: { x: 620, y: 0 },
      },
    },
    {
      id: "success_package",
      label: "Success Package",
      kind: "generated_artifact",
      layer: "outcome",
      metadata: {
        source: templateSource,
        visualRole: "success_branch",
        iconHint: "package",
        cardDensity: "compact",
        positionHint: { x: 900, y: -80 },
      },
    },
    {
      id: "needs_context",
      label: "Needs Context",
      kind: "docs_context",
      layer: "outcome",
      metadata: {
        source: templateSource,
        visualRole: "fallback_branch",
        iconHint: "context-warning",
        cardDensity: "compact",
        positionHint: { x: 900, y: 100 },
      },
    },
  ],
  edges: [
    {
      id: "chat_trigger:drives:planning_agent",
      source: "chat_trigger",
      target: "planning_agent",
      kind: "drives",
      metadata: { source: templateSource },
    },
    {
      id: "planning_agent:uses_context:context_library",
      source: "planning_agent",
      target: "context_library",
      kind: "uses_context",
      metadata: { source: templateSource, helperPlacement: "below" },
    },
    {
      id: "planning_agent:uses_skill:skills",
      source: "planning_agent",
      target: "skills",
      kind: "uses_skill",
      metadata: { source: templateSource, helperPlacement: "below" },
    },
    {
      id: "planning_agent:depends_on:tools",
      source: "planning_agent",
      target: "tools",
      kind: "depends_on",
      metadata: { source: templateSource, helperPlacement: "below" },
    },
    {
      id: "planning_agent:drives:if_ready",
      source: "planning_agent",
      target: "if_ready",
      kind: "drives",
      metadata: { source: templateSource },
    },
    {
      id: "if_ready:validates:success_package",
      source: "if_ready",
      target: "success_package",
      kind: "validates",
      label: "ready",
      metadata: { source: templateSource, branch: "success" },
    },
    {
      id: "if_ready:blocks:needs_context",
      source: "if_ready",
      target: "needs_context",
      kind: "blocks",
      label: "needs context",
      metadata: { source: templateSource, branch: "fallback" },
    },
  ],
  clusters: [
    {
      id: "starter-template:helpers",
      label: "Helper Context",
      nodeIds: ["context_library", "skills", "tools"],
      kind: "helper_context",
      metadata: { source: templateSource, layoutLayer: "context" },
    },
    {
      id: "starter-template:branches",
      label: "Readiness Branches",
      nodeIds: ["if_ready", "success_package", "needs_context"],
      kind: "decision_branch",
      metadata: { source: templateSource, layoutLayer: "outcome" },
    },
  ],
};

export function createStarterProjectGraphTemplate(): ProjectGraph {
  return normalizeProjectGraph(starterTemplateInput);
}
