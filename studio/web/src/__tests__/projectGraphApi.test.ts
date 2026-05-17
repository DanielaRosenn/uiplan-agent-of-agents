import { afterEach, describe, expect, test, vi } from "vitest";

import { loadDemoIntake, loadRefreshState, runAgentOpsDemo } from "../projectGraph/api";

describe("project graph API", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test("loads the plan refresh state for a worktree", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ worktree_id: "demo", stamp: "123.4", source_count: 2 }),
    } as Response);

    const result = await loadRefreshState("pricing-bot");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/explorer/refresh-state?worktree=pricing-bot",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
    expect(result).toEqual({
      data: { worktree_id: "demo", stamp: "123.4", source_count: 2 },
      source: "api",
    });
  });

  test("loadDemoIntake falls back on non-200 response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({}),
    } as Response);

    const result = await loadDemoIntake();

    expect(result.source).toBe("fallback");
    expect(result.error).toBe("HTTP 500");
    expect(result.data.businessGoal).toContain("agent-of-agents orchestration flow");
  });

  test("loadDemoIntake falls back on malformed payload", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ industry: "Finance" }),
    } as Response);

    const result = await loadDemoIntake();

    expect(result.source).toBe("fallback");
    expect(result.error).toBe("Malformed response");
    expect(Array.isArray(result.data.systems)).toBe(true);
  });

  test("runAgentOpsDemo falls back on malformed payload", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ orchestrator_state: { current_phase: "Verification" } }),
    } as Response);

    const result = await runAgentOpsDemo({
      businessGoal: "Reduce manual invoice exception handling",
      systems: ["ERP"],
    });

    expect(result.source).toBe("fallback");
    expect(result.error).toBe("Malformed response");
    expect(result.data.deployment_readiness_status.status).toBe("blocked");
  });

  test("runAgentOpsDemo returns api source for valid payload", async () => {
    const validPayload = {
      orchestrator_state: {
        current_phase: "Verification",
        status: "in_progress",
        active_workflow: "InvoiceExceptionOrchestrator",
        blocked: true,
      },
      specialist_assignments: [
        { agent: "discovery-agent", role: "Intake analysis", status: "done" },
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
      build_queue: [{ id: "q1", title: "Build", status: "in_progress", phase: "Build" }],
      verification_checklist: [{ gate: "AS-IS captured", status: "passed", owner: "discovery-agent" }],
      deployment_readiness_status: {
        status: "blocked",
        deployed: false,
        blocker: "Verification gates are still pending.",
        target: "personal-workspace",
      },
      handoff_summary: {
        summary: "Template clone completed.",
        next_action: "Complete verification gates.",
        owner: "builder-orchestrator",
      },
    };
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => validPayload,
    } as Response);

    const result = await runAgentOpsDemo({
      businessGoal: "Reduce manual invoice exception handling",
      industry: "Finance operations",
      systems: ["Email inbox", "ERP"],
      constraints: ["No production deployment"],
      successCriteria: ["Run verification gates"],
    });

    expect(result.source).toBe("api");
    expect(result.error).toBeUndefined();
    expect(result.data.orchestrator_state.current_phase).toBe("Verification");
    expect(result.data.specialist_assignments).toHaveLength(1);
  });
});
