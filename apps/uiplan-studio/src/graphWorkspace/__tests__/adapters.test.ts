import { describe, expect, test } from "vitest";

import { toDiagramData } from "../adapters";
import type { GraphWorkspaceV2 } from "../types";

describe("graphWorkspace adapters", () => {
  test("toDiagramData maps GraphWorkspaceV2 node to diagram node id/title", () => {
    const workspace: GraphWorkspaceV2 = {
      version: "uiplan_graph.v2",
      nodes: [{ id: "spec", type: "core", title: "Spec", summary: "Specification doc" }],
      edges: [],
    };

    const diagram = toDiagramData(workspace);

    expect(diagram.nodes).toEqual([
      expect.objectContaining({
        id: "spec",
        title: "Spec",
      }),
    ]);
  });
});
