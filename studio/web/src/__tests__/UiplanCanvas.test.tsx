import React from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import UiplanCanvas from "../components/UiplanCanvas";
import { sampleGraph } from "../__fixtures__/sample";
import type { ProjectNode } from "../projectGraph/types";

function sampleBundle(): ProjectNode {
  const bundle = sampleGraph.nodes.find((node) => node.kind === "uiplan_bundle");
  if (!bundle) {
    throw new Error("sample fixture is missing a UiPlan bundle");
  }
  return bundle;
}

describe("UiplanCanvas workflow planning surface", () => {
  test("reflects UiPlan files as a project planning kanban with drill-downs", () => {
    const onSelectNode = vi.fn();
    render(
      <UiplanCanvas
        bundle={sampleBundle()}
        selectedNodeId={null}
        onSelectNode={onSelectNode}
      />,
    );

    const tabBar = screen.getByLabelText("UiPlan view mode");
    fireEvent.click(within(tabBar).getByRole("button", { name: /project plan/i }));

    expect(screen.getByText("PROJECT PLANNING KANBAN")).toBeInTheDocument();
    expect(screen.getByText("DEFINE")).toBeInTheDocument();
    expect(screen.getByText("DESIGN")).toBeInTheDocument();
    expect(screen.getByText("BUILD")).toBeInTheDocument();
    expect(screen.getByText("VALIDATE")).toBeInTheDocument();
    expect(screen.getByText("TEMPLATE")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /spec\.md PROJECT BRIEF/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /plan\.md SOLUTION DESIGN/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /tasks\.md BUILD BACKLOG/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /AS-IS diagram CURRENT STATE/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /TO-BE diagram UIPATH TARGET/i })).toBeInTheDocument();
    expect(screen.getByText(/SPEC\.MD CARD DETAIL/i)).toBeInTheDocument();
    expect(screen.getByText(/Current process/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /plan\.md SOLUTION DESIGN/i }));
    expect(onSelectNode).toHaveBeenCalledWith(expect.stringMatching(/plan\.md/i));
    expect(screen.getByText(/PLAN\.MD CARD DETAIL/i)).toBeInTheDocument();
    expect(screen.getByText(/Runtime flow/i)).toBeInTheDocument();
    expect(screen.getByText(/flowchart/i)).toBeInTheDocument();
    expect(screen.queryByText(/OPEN CODE/i)).not.toBeInTheDocument();
  });

  test("opens on the TO-BE UiPath flow as a staged L0 diagram", () => {
    render(
      <UiplanCanvas
        bundle={sampleBundle()}
        selectedNodeId={null}
        onSelectNode={vi.fn()}
      />,
    );

    const tabBar = screen.getByLabelText("UiPlan view mode");
    fireEvent.click(within(tabBar).getByRole("button", { name: /to-be/i }));

    expect(screen.getAllByText("TO-BE UIPATH FLOW").length).toBeGreaterThan(0);
    expect(screen.getByText(/High-level architecture first/i)).toBeInTheDocument();
    expect(screen.getAllByText("Trigger").length).toBeGreaterThan(0);
    expect(screen.getByText("Ingress")).toBeInTheDocument();
    expect(screen.getByText("Reason")).toBeInTheDocument();
    expect(screen.getByText("Act")).toBeInTheDocument();
    expect(screen.getByText("Reply")).toBeInTheDocument();
    expect(screen.getByText("Observe")).toBeInTheDocument();
    expect(screen.getByText("End")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Slack request received TRIGGER/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Normalize renewal request ACTIVITY/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sales Rep approval workflow DRILL-DOWN/i })).toBeInTheDocument();
    expect(screen.queryByText(/IMPLEMENTATION HEALTH/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/\.xaml/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reset clean view/i })).toBeInTheDocument();
  });

  test("renders AS-IS as a manual flow diagram with drill-down", () => {
    render(
      <UiplanCanvas
        bundle={sampleBundle()}
        selectedNodeId={null}
        onSelectNode={vi.fn()}
      />,
    );

    const tabBar = screen.getByLabelText("UiPlan view mode");
    fireEvent.click(within(tabBar).getByRole("button", { name: /as-is/i }));
    expect(screen.getAllByText("AS-IS MANUAL FLOW").length).toBeGreaterThan(0);
    expect(screen.getByText(/How work happens today/i)).toBeInTheDocument();
    expect(screen.getAllByText("Trigger").length).toBeGreaterThan(0);
    expect(screen.getByText("Ingress")).toBeInTheDocument();
    expect(screen.getByText("Reason")).toBeInTheDocument();
    expect(screen.getByText("Act")).toBeInTheDocument();
    expect(screen.getByText("Reply")).toBeInTheDocument();
    expect(screen.getByText("Observe")).toBeInTheDocument();
    expect(screen.getByText("End")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Sales Ops reads request HANDOFF/i }));
    expect(screen.getByText(/L0 AS-IS FLOW \/ L1 DRILL-DOWN/i)).toBeInTheDocument();
    expect(screen.getByText(/AS-IS DRILL-DOWN: Sales Ops reads request/i)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /BACK TO L0 FLOW/i }).length).toBeGreaterThan(0);
    expect(screen.queryByText(/\.xaml/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/OPEN CODE/i)).not.toBeInTheDocument();
  });

  test("supports compare and TO-BE node drill-down", () => {
    render(
      <UiplanCanvas
        bundle={sampleBundle()}
        selectedNodeId={null}
        onSelectNode={vi.fn()}
      />,
    );

    const tabBar = screen.getByLabelText("UiPlan view mode");
    fireEvent.click(within(tabBar).getByRole("button", { name: /compare/i }));
    expect(screen.getByText(/Delta summary: manual handoffs/i)).toBeInTheDocument();

    fireEvent.click(within(tabBar).getByRole("button", { name: /to-be/i }));
    fireEvent.click(screen.getByRole("button", { name: /Sales Rep approval workflow DRILL-DOWN/i }));
    expect(screen.getByText(/L0 TO-BE UIPATH FLOW \/ L1 SUB-WORKFLOW/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Sales Rep approval workflow/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Readiness:/i)).toBeInTheDocument();
  });
});
