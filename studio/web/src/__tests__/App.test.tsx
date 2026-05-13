import React from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import App from "../App";

beforeEach(() => {
  window.history.pushState(null, "", "/");
  vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("offline"));
});

describe("UiPath workflow planning app", () => {
  test("opens directly on the UiPlan project planning kanban", async () => {
    render(<App />);

    await screen.findByText("PROJECT PLANNING KANBAN");
    expect(screen.getAllByText(/WORKFLOW BUILDER/i).length).toBeGreaterThan(0);
    expect(screen.getByText("PRE-BUILD PLAN")).toBeInTheDocument();
    expect(screen.getByText("DEFINE")).toBeInTheDocument();
    expect(screen.getByText("DESIGN")).toBeInTheDocument();
    expect(screen.getByText("BUILD")).toBeInTheDocument();

    const tabBar = screen.getByLabelText("UiPlan view mode");
    fireEvent.click(within(tabBar).getByRole("button", { name: /TO-BE UIPATH FLOW/i }));
    expect(screen.getByRole("button", { name: /Slack request received TRIGGER/i })).toBeInTheDocument();
  });

  test("does not expose project-map or source-code chrome in the active planning UI", async () => {
    render(<App />);

    await screen.findByText("PROJECT PLANNING KANBAN");
    expect(screen.queryByRole("button", { name: /project map/i })).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/source folder path/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/OPEN CODE/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/\.xaml/i)).not.toBeInTheDocument();
  });

  test("keeps UiPlan files visible as project planning template artifacts", async () => {
    render(<App />);
    await screen.findAllByText("TO-BE UIPATH FLOW");

    const tabBar = screen.getByLabelText("UiPlan view mode");
    fireEvent.click(within(tabBar).getByRole("button", { name: /PROJECT PLAN/i }));

    expect(screen.getByText("PROJECT PLANNING KANBAN")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /spec\.md PROJECT BRIEF/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /plan\.md SOLUTION DESIGN/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /tasks\.md BUILD BACKLOG/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /TO-BE diagram UIPATH TARGET/i })).toBeInTheDocument();
    expect(screen.queryByText(/OPEN CODE/i)).not.toBeInTheDocument();
  });

  test("keeps AS-IS and TO-BE available as diagram modes", async () => {
    render(<App />);
    await screen.findAllByText("TO-BE UIPATH FLOW");

    const tabBar = screen.getByLabelText("UiPlan view mode");
    fireEvent.click(within(tabBar).getByRole("button", { name: /AS-IS MANUAL FLOW/i }));
    expect(screen.getAllByText("AS-IS MANUAL FLOW").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /Manual account lookup LOOKUP/i })).toBeInTheDocument();

    fireEvent.click(within(tabBar).getByRole("button", { name: /TO-BE UIPATH FLOW/i }));
    expect(screen.getAllByText("TO-BE UIPATH FLOW").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /Create approval task HITL/i })).toBeInTheDocument();
  });
});
