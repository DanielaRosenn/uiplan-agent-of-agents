import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import App from "../App";

beforeEach(() => {
  window.history.pushState(null, "", "/");
  vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("offline"));
});

describe("UiPath workflow planning app", () => {
  const openBuilderFlow = async () => {
    const builderToggle = await screen.findByTitle("AgentOps Orchestrator flow");
    fireEvent.click(builderToggle);
    await screen.findByText("PRE-BUILD PLAN");
  };

  test("opens directly on the UiPlan project planning kanban", async () => {
    render(<App />);

    await openBuilderFlow();
    expect(screen.getAllByText(/AGENTOPS ORCHESTRATOR/i).length).toBeGreaterThan(0);
    expect(screen.getByText("PRE-BUILD PLAN")).toBeInTheDocument();
    expect(screen.getByText("DEFINE")).toBeInTheDocument();
    expect(screen.getByText("DESIGN")).toBeInTheDocument();
    expect(screen.getByText("BUILD")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /^TO BE$/i }));
    expect(screen.getByRole("button", { name: /Slack request received TRIGGER/i })).toBeInTheDocument();
  });

  test("does not expose project-map or source-code chrome in the active planning UI", async () => {
    render(<App />);

    await openBuilderFlow();
    expect(screen.queryByRole("button", { name: /project map/i })).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/source folder path/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/OPEN CODE/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/\.xaml/i)).not.toBeInTheDocument();
  });

  test("keeps UiPlan files visible as project planning template artifacts", async () => {
    render(<App />);
    await openBuilderFlow();

    expect(screen.getByText("AGENTOPS ORCHESTRATOR KANBAN")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /spec\.md PROJECT BRIEF/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /plan\.md SOLUTION DESIGN/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /tasks\.md BUILD BACKLOG/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /TO-BE diagram UIPATH TARGET/i })).toBeInTheDocument();
    expect(screen.queryByText(/OPEN CODE/i)).not.toBeInTheDocument();
  });

  test("keeps AS-IS and TO-BE available as diagram modes", async () => {
    render(<App />);
    await openBuilderFlow();

    fireEvent.click(screen.getByRole("button", { name: /^AS IS$/i }));
    expect(screen.getAllByText("AS-IS MANUAL FLOW").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /Manual account lookup LOOKUP/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /^TO BE$/i }));
    expect(screen.getAllByText("TO-BE UIPATH FLOW").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /Create approval task HITL/i })).toBeInTheDocument();
  });
});
