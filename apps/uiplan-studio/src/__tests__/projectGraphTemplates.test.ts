import { describe, expect, test } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import {
  createStarterProjectGraphTemplate,
  starterProjectGraphTemplateMetadata,
} from "../projectGraph/templates";

interface StarterTemplateContract {
  metadata: {
    id: string;
    nodeCount: number;
    tags: string[];
    layoutDirection: string;
    layers: string[];
    iconHints: Record<string, string>;
  };
  nodeIds: string[];
  nodeKinds: Record<string, string>;
  edgeSignatures: Array<[string, string, string, string | null]>;
}

const starterTemplateContract = JSON.parse(
  readFileSync(
    resolve(process.cwd(), "../../test-fixtures/project-graph/starter-template-contract.json"),
    "utf8",
  ),
) as StarterTemplateContract;

describe("projectGraph starter template", () => {
  test("describes the starter canvas metadata", () => {
    expect(starterProjectGraphTemplateMetadata).toMatchObject({
      id: "visual-template",
      title: "Starter Agent Canvas",
      nodeCount: starterTemplateContract.metadata.nodeCount,
      tags: expect.arrayContaining(starterTemplateContract.metadata.tags),
      recommendedLayout: expect.objectContaining({
        direction: starterTemplateContract.metadata.layoutDirection,
        layers: expect.arrayContaining(starterTemplateContract.metadata.layers),
      }),
      iconHints: expect.objectContaining(starterTemplateContract.metadata.iconHints),
    });
  });

  test("creates a normalized ProjectGraph with required nodes and branches", () => {
    const graph = createStarterProjectGraphTemplate();
    const nodesById = new Map(graph.nodes.map((node) => [node.id, node]));

    expect(graph.projectType).toBe("solution");
    expect(graph.errors).toEqual([]);
    expect([...nodesById.keys()]).toEqual(starterTemplateContract.nodeIds);
    expect(graph.nodes.every((node) => node.metadata.source === "projectGraph.starterTemplate")).toBe(
      true,
    );
    expect(nodesById.get("planning_agent")).toMatchObject({
      kind: "project_component",
      layer: "agent",
      metadata: expect.objectContaining({ visualRole: "central_action", cardDensity: "compact" }),
    });
    expect(nodesById.get("context_library")).toMatchObject({
      kind: "docs_context",
      layer: "context",
    });
    expect(nodesById.get("skills")).toMatchObject({ kind: "skill", layer: "context" });
    expect(nodesById.get("tools")).toMatchObject({ kind: "tool", layer: "context" });
    expect(nodesById.get("if_ready")).toMatchObject({
      kind: "review_gate",
      layer: "decision",
      metadata: expect.objectContaining({ visualRole: "decision_branch" }),
    });

    const edgeSignatures = graph.edges.map((edge) => [
      edge.source,
      edge.target,
      edge.kind,
      edge.label ?? null,
    ]);
    expect(edgeSignatures).toEqual(starterTemplateContract.edgeSignatures);
  });

  test("matches the shared starter template parity contract", () => {
    const graph = createStarterProjectGraphTemplate();
    const nodeKinds = Object.fromEntries(
      graph.nodes
        .filter((node) => node.id in starterTemplateContract.nodeKinds)
        .map((node) => [node.id, node.kind]),
    );

    expect(starterProjectGraphTemplateMetadata.id).toBe(starterTemplateContract.metadata.id);
    expect(starterProjectGraphTemplateMetadata.nodeCount).toBe(
      starterTemplateContract.metadata.nodeCount,
    );
    expect(nodeKinds).toEqual(starterTemplateContract.nodeKinds);
  });
});
