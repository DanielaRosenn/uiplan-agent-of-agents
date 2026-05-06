import { describe, expect, test } from "vitest";

import { toDiagramData } from "../adapters";
import type { GraphWorkspaceV2 } from "../types";

describe("graphWorkspace adapters", () => {
  test("toDiagramData maps GraphWorkspaceV2 node to diagram node id/title", () => {
    const workspace: GraphWorkspaceV2 = {
      version: "uiplan_graph.v2",
      nodes: [{ id: "spec", type: "doc", title: "Spec", summary: "Specification doc" }],
      edges: [],
    };

    const diagram = toDiagramData(workspace);

    expect(diagram.nodes).toEqual([
      expect.objectContaining({
        id: "spec",
        title: "Spec",
        kind: "document",
      }),
    ]);
  });

  test("toDiagramData preserves node type semantics for skill and review gates", () => {
    const workspace: GraphWorkspaceV2 = {
      version: "uiplan_graph.v2",
      nodes: [
        { id: "skills", type: "skill", title: "Skills Context" },
        { id: "review", type: "review_gate", title: "Review Gate" },
      ],
      edges: [],
    };

    const diagram = toDiagramData(workspace);

    expect(diagram.nodes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ id: "skills", kind: "skill" }),
        expect.objectContaining({ id: "review", kind: "review" }),
      ]),
    );
  });
});
