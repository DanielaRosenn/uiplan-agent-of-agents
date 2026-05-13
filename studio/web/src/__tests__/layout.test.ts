import { describe, expect, test } from "vitest";

import { computeLayout } from "../layout";
import type { ProjectGraph, ProjectNode } from "../projectGraph/types";

function skillNode(index: number): ProjectNode {
  return {
    id: `skill-${index}`,
    label: `skill ${index}`,
    kind: "skill",
    layer: "skills",
  };
}

describe("computeLayout", () => {
  test("wraps large skills layers into a compact grid", () => {
    const graph: ProjectGraph = {
      projectType: "test",
      nodes: Array.from({ length: 20 }, (_, index) => skillNode(index)),
      edges: [],
      errors: [],
    };

    const layout = computeLayout(graph);
    const positions = graph.nodes.map((node) => layout.positions[node.id]);
    const distinctX = new Set(positions.map((position) => position.x));
    const distinctY = new Set(positions.map((position) => position.y));

    expect(distinctX.size).toBeGreaterThan(1);
    expect(distinctY.size).toBeLessThan(20);
  });
});
