import React from "react";
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import GraphExplorerPanel from "../components/GraphExplorerPanel";
import type { DiagramNode } from "../types";

test("renders hierarchical file tree", () => {
  const nodes: DiagramNode[] = [
    {
      id: "1",
      title: "src/App.tsx",
      kind: "document",
      description: "Main app",
      x: 0,
      y: 0,
      layer: "ui",
    },
    {
      id: "2",
      title: "src/utils/helper.ts",
      kind: "document",
      description: "Helper utils",
      x: 0,
      y: 0,
      layer: "logic",
    },
  ];

  render(
    <GraphExplorerPanel
      nodes={nodes}
      selectedNodeId={null}
      onSelectNodeId={() => {}}
    />,
  );

  expect(screen.getByText("Graph Explorer")).toBeInTheDocument();
  expect(screen.getByText("src")).toBeInTheDocument();
});
