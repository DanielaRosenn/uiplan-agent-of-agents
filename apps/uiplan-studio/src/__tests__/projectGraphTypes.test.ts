import { describe, expect, test } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import type { ProjectGraph, ProjectGraphAdapter } from "../projectGraph/types";
import { normalizeProjectGraph } from "../projectGraph/types";

const goldenGraph = JSON.parse(
  readFileSync(resolve(process.cwd(), "../../test-fixtures/project-graph/golden.json"), "utf8"),
) as ProjectGraph;

describe("projectGraph types", () => {
  test("supports a visualization-focused ProjectGraph fixture", () => {
    const graph: ProjectGraph = normalizeProjectGraph({
      projectType: "solution",
      nodes: [
        {
          id: "intake",
          label: "Customer Intake",
          kind: "process_step",
          layer: "process",
          metadata: { owner: "operations" },
        },
      ],
      edges: [
        {
          id: "intake-agent",
          source: "intake",
          target: "agent",
          kind: "drives",
          label: "drives",
        },
      ],
      clusters: [
        {
          id: "automation",
          label: "Automation",
          nodeIds: ["intake"],
          metadata: { projectType: "coded-agent" },
        },
      ],
      errors: [
        {
          id: "missing-target",
          message: "Target node is missing.",
          severity: "warning",
          targetId: "agent",
        },
      ],
    });

    expect(graph.projectType).toBe("solution");
    expect(graph.nodes[0].metadata.owner).toBe("operations");
    expect(graph.edges[0]).toMatchObject({ source: "intake", target: "agent" });
    expect(graph.clusters[0].nodeIds).toEqual(["intake"]);
    expect(graph.errors[0].severity).toBe("warning");
  });

  test("normalizes optional arrays and metadata dictionaries", () => {
    const graph = normalizeProjectGraph({
      projectType: "docs",
      nodes: [
        { id: "plan", label: "Plan", kind: "generated_artifact", layer: "artifact" },
        { id: "review", label: "Review", kind: "review_gate" },
      ],
      edges: [{ id: "plan-review", source: "plan", target: "review", kind: "documents" }],
    });

    expect(graph.nodes[0].metadata).toEqual({});
    expect(graph.edges[0].label).toBeUndefined();
    expect(graph.edges[0].metadata).toEqual({});
    expect(graph.clusters).toEqual([]);
    expect(graph.errors).toEqual([]);
  });

  test("omits optional null fields from the JSON contract", () => {
    const graph = normalizeProjectGraph({
      projectType: "docs",
      nodes: [{ id: "plan", label: "Plan", kind: "generated_artifact", layer: null }],
      edges: [{ id: "plan-review", source: "plan", target: "review", kind: "documents" }],
      clusters: [{ id: "docs", label: "Docs", nodeIds: ["plan"], kind: null }],
      errors: [{ id: "note", message: "Advisory only.", severity: "note", targetId: null }],
    });

    const payload = JSON.parse(JSON.stringify(graph));

    expect(payload.nodes[0]).not.toHaveProperty("layer");
    expect(payload.edges[0]).not.toHaveProperty("label");
    expect(payload.clusters[0]).not.toHaveProperty("kind");
    expect(payload.errors[0]).not.toHaveProperty("targetId");
  });

  test("preserves dangling references with deterministic diagnostics", () => {
    const graph = normalizeProjectGraph({
      projectType: "solution",
      nodes: [{ id: "intake", label: "Customer Intake", kind: "process_step" }],
      edges: [{ id: "intake-agent", source: "intake", target: "agent", kind: "drives" }],
      clusters: [{ id: "automation", label: "Automation", nodeIds: ["intake", "agent"] }],
    });

    expect(graph.errors).toEqual([
      {
        id: "edge:intake-agent:missing-target",
        message: "Edge target references missing node 'agent'.",
        severity: "warning",
        targetId: "intake-agent",
        metadata: { source: "projectGraph.normalize" },
      },
      {
        id: "cluster:automation:missing-member:agent",
        message: "Cluster member references missing node 'agent'.",
        severity: "warning",
        targetId: "automation",
        metadata: { source: "projectGraph.normalize" },
      },
    ]);
  });

  test("matches the shared golden JSON fixture", () => {
    expect(normalizeProjectGraph(goldenGraph)).toEqual(goldenGraph);
  });

  test("defines the adapter boundary without coupling to generation package contracts", () => {
    const adapter: ProjectGraphAdapter = (input) => ({
      graph: normalizeProjectGraph({
        projectType: input.projectType,
        nodes: [],
        edges: [],
      }),
      issues: [],
    });

    expect(adapter({ projectType: "coded-agent", source: { nodes: [] } }).graph.projectType).toBe(
      "coded-agent",
    );
  });
});
