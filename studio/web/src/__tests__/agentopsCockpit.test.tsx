import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import App from "../App";

const demoIntake = {
  businessGoal: "Reduce manual invoice exception handling",
  industry: "Finance operations",
  systems: ["Email inbox", "ERP", "UiPath Action Center"],
  constraints: ["No production deployment"],
  successCriteria: ["Generate AS-IS and TO-BE process views"],
};

const demoRun = {
  orchestrator_state: {
    current_phase: "Verification",
    status: "in_progress",
    active_workflow: "InvoiceExceptionOrchestrator",
    blocked: true,
  },
  specialist_assignments: [
    { agent: "discovery-agent", role: "Intake analysis", status: "done" },
    { agent: "solution-architect-agent", role: "TO-BE design", status: "done" },
    { agent: "builder-orchestrator", role: "Template clone + deltas", status: "in_progress" },
  ],
  as_is_view_model: {
    swimlanes: ["Finance analyst"],
    handoffs: [],
    pain_points: [],
    sources: [],
  },
  to_be_view_model: {
    buckets: [],
    workflows: [],
    integrations: [],
    orchestrator: [],
    hitl: [],
    runtime_sequence: [],
    sources: [],
  },
  build_queue: [{ id: "q1", title: "Apply generated workflows", status: "in_progress", phase: "Build" }],
  verification_checklist: [
    { gate: "AS-IS captured", status: "passed", owner: "discovery-agent" },
    { gate: "TO-BE mapped", status: "pending", owner: "solution-architect-agent" },
  ],
  deployment_readiness_status: {
    status: "blocked",
    deployed: false,
    blocker: "Verification gates are still pending.",
    target: "personal-workspace",
  },
  handoff_summary: {
    summary: "Template clone completed. Generated deltas are ready for verification.",
    next_action: "Complete verification gates and package deployment evidence.",
    owner: "builder-orchestrator",
  },
};

function mockFetchForCockpit(runPayload: unknown) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/fixtures/demo/intake")) {
      return { ok: true, json: async () => demoIntake } as Response;
    }
    if (url.endsWith("/agentops/demo/run")) {
      return { ok: true, json: async () => runPayload } as Response;
    }
    return Promise.reject(new Error("offline"));
  });
}

beforeEach(() => {
  window.history.pushState(null, "", "/");
  vi.restoreAllMocks();
});

describe("agentops cockpit wiring", () => {
  test("renders cockpit sections from demo run payload", async () => {
    mockFetchForCockpit(demoRun);
    render(<App />);

    fireEvent.click(await screen.findByTitle("AgentOps Orchestrator flow"));
    await screen.findByText("PRE-BUILD PLAN");

    expect(await screen.findByText(/AGENT ROSTER · 3 specialists/i)).toBeInTheDocument();
    expect(screen.getByText(/CURRENT PHASE · Verification/i)).toBeInTheDocument();
    expect(screen.getByText(/BUILD QUEUE · 1 queued items/i)).toBeInTheDocument();
    expect(screen.getByText(/VERIFICATION GATES · 1\/2 passed/i)).toBeInTheDocument();
    expect(screen.getByText(/DEPLOYMENT BLOCKER · BLOCKED/i)).toBeInTheDocument();
    expect(screen.getByText(/HANDOFF SUMMARY · Template clone completed/i)).toBeInTheDocument();
  });

  test("falls back to safe demo payload when run response is malformed", async () => {
    mockFetchForCockpit({ malformed: true });
    render(<App />);

    fireEvent.click(await screen.findByTitle("AgentOps Orchestrator flow"));
    await screen.findByText("PRE-BUILD PLAN");

    expect(await screen.findByText(/AGENT ROSTER · 4 specialists/i)).toBeInTheDocument();
    expect(screen.getByText(/BUILD QUEUE · 2 queued items/i)).toBeInTheDocument();
    expect(screen.getByText(/VERIFICATION GATES · 2\/3 passed/i)).toBeInTheDocument();
  });
});
