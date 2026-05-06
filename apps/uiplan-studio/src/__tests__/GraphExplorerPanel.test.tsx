import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { expect, test, describe, vi } from "vitest";

import GraphExplorerPanel from "../components/GraphExplorerPanel";
import type { DiagramNode } from "../types";

describe("GraphExplorerPanel", () => {
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

  test("renders empty tree message", () => {
    render(
      <GraphExplorerPanel
        nodes={[]}
        selectedNodeId={null}
        onSelectNodeId={() => {}}
      />,
    );

    expect(screen.getByText("No Graph Nodes")).toBeInTheDocument();
  });

  test("renders flat nodes without hierarchy", () => {
    const nodes: DiagramNode[] = [
      {
        id: "1",
        title: "Main.workflow",
        kind: "workflow",
        description: "Main workflow",
        x: 0,
        y: 0,
        layer: "logic",
      },
      {
        id: "2",
        title: "Helper.library",
        kind: "library",
        description: "Helper library",
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

    expect(screen.getByText("Main.workflow")).toBeInTheDocument();
    expect(screen.getByText("Helper.library")).toBeInTheDocument();
  });

  test("handles deep nesting correctly", () => {
    const nodes: DiagramNode[] = [
      {
        id: "1",
        title: "a/b/c/d/file.ts",
        kind: "document",
        description: "Deep file",
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

    // Root folder should be visible
    expect(screen.getByText("a")).toBeInTheDocument();
    
    // Expand all to see nested content
    const expandAllButton = screen.getByText("Expand All");
    fireEvent.click(expandAllButton);
    
    // After expanding, deep file should be visible
    expect(screen.getByText("file.ts")).toBeInTheDocument();
  });

  test("calls onSelectNodeId when node is clicked", () => {
    const onSelectNodeId = vi.fn();
    const nodes: DiagramNode[] = [
      {
        id: "1",
        title: "test.ts",
        kind: "document",
        description: "Test file",
        x: 0,
        y: 0,
        layer: "logic",
      },
    ];

    render(
      <GraphExplorerPanel
        nodes={nodes}
        selectedNodeId={null}
        onSelectNodeId={onSelectNodeId}
      />,
    );

    const node = screen.getByText("test.ts").closest("div");
    if (node) fireEvent.click(node);

    expect(onSelectNodeId).toHaveBeenCalledWith("1");
  });

  test("highlights selected node", () => {
    const nodes: DiagramNode[] = [
      {
        id: "1",
        title: "selected.ts",
        kind: "document",
        description: "Selected file",
        x: 0,
        y: 0,
        layer: "logic",
      },
    ];

    render(
      <GraphExplorerPanel
        nodes={nodes}
        selectedNodeId="1"
        onSelectNodeId={() => {}}
      />,
    );

    const node = screen.getByText("selected.ts").closest("div");
    expect(node).toHaveClass("selected");
  });

  test("expand all button expands all folders", () => {
    const nodes: DiagramNode[] = [
      {
        id: "1",
        title: "a/b/file1.ts",
        kind: "document",
        description: "File 1",
        x: 0,
        y: 0,
        layer: "logic",
      },
      {
        id: "2",
        title: "a/c/file2.ts",
        kind: "document",
        description: "File 2",
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

    const expandAllButton = screen.getByText("Expand All");
    fireEvent.click(expandAllButton);

    expect(screen.getByText("b")).toBeInTheDocument();
    expect(screen.getByText("c")).toBeInTheDocument();
  });

  test("collapse all button collapses all folders", () => {
    const nodes: DiagramNode[] = [
      {
        id: "1",
        title: "a/b/file.ts",
        kind: "document",
        description: "File",
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

    const collapseAllButton = screen.getByText("Collapse All");
    fireEvent.click(collapseAllButton);

    expect(screen.queryByText("b")).not.toBeInTheDocument();
  });

  test("keyboard navigation with Enter key", () => {
    const onSelectNodeId = vi.fn();
    const nodes: DiagramNode[] = [
      {
        id: "1",
        title: "keyboard.ts",
        kind: "document",
        description: "Keyboard test",
        x: 0,
        y: 0,
        layer: "logic",
      },
    ];

    render(
      <GraphExplorerPanel
        nodes={nodes}
        selectedNodeId={null}
        onSelectNodeId={onSelectNodeId}
      />,
    );

    const node = screen.getByText("keyboard.ts").closest("div");
    if (node) {
      node.focus();
      fireEvent.keyDown(node, { key: "Enter" });
    }

    expect(onSelectNodeId).toHaveBeenCalledWith("1");
  });

  test("keyboard navigation with Space key", () => {
    const onSelectNodeId = vi.fn();
    const nodes: DiagramNode[] = [
      {
        id: "1",
        title: "space.ts",
        kind: "document",
        description: "Space test",
        x: 0,
        y: 0,
        layer: "logic",
      },
    ];

    render(
      <GraphExplorerPanel
        nodes={nodes}
        selectedNodeId={null}
        onSelectNodeId={onSelectNodeId}
      />,
    );

    const node = screen.getByText("space.ts").closest("div");
    if (node) {
      node.focus();
      fireEvent.keyDown(node, { key: " " });
    }

    expect(onSelectNodeId).toHaveBeenCalledWith("1");
  });

  test("has proper ARIA attributes", () => {
    const nodes: DiagramNode[] = [
      {
        id: "1",
        title: "a/file.ts",
        kind: "document",
        description: "File",
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

    const tree = screen.getByRole("tree");
    expect(tree).toBeInTheDocument();

    const treeItems = screen.getAllByRole("treeitem");
    expect(treeItems.length).toBeGreaterThan(0);
  });
});
