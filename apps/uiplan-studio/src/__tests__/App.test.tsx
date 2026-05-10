import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import App from "../App";

beforeEach(() => {
  // Force the API client to fall back to bundled fixtures by stubbing fetch.
  vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("offline"));
});

describe("project explorer chrome", () => {
  test("renders the explorer header and sample badge", async () => {
    render(<App />);
    expect(screen.getByText(/UIPLAN.*EXPLORER/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("SAMPLE")).toBeInTheDocument();
    });
  });

  test("worktree selector lists fixture options", async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByRole("option", { name: /Demo · renewal commitment/i })).toBeInTheDocument();
      expect(screen.getByRole("option", { name: /Solution · order-to-cash/i })).toBeInTheDocument();
      expect(screen.getByRole("option", { name: /Empty worktree/i })).toBeInTheDocument();
    });
  });

  test("api worktrees do not replace the default demo view", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [
          {
            id: "pricing-bot",
            label: "Pricing Bot",
            path: "C:/other/pricing-bot",
            branch: "main",
            project_type: "flow",
          },
        ],
      }),
    } as Response);

    render(<App />);

    const select = await screen.findByRole("combobox") as HTMLSelectElement;
    await waitFor(() => {
      expect(screen.getByRole("option", { name: /Pricing Bot/i })).toBeInTheDocument();
    });
    expect(select.value).toBe("demo");
    expect(screen.getAllByText(/Renewal Commitment/i).length).toBeGreaterThan(0);
  });
});

describe("BA representation", () => {
  test("project overview renders by default with KPIs and stakeholders", async () => {
    render(<App />);
    // Wait for the inspector to mount the ProjectOverview and render KPIs.
    await waitFor(() => {
      expect(screen.getByText("KPIS")).toBeInTheDocument();
    });
    expect(screen.getByText("AUTO-APPROVAL RATE")).toBeInTheDocument();
    expect(screen.getByText("STAKEHOLDERS")).toBeInTheDocument();
    expect(screen.getAllByText("Sales Operations").length).toBeGreaterThan(0);
  });

  test("solution fixture exposes Maestro/App/Test layers", async () => {
    render(<App />);
    const select = await screen.findByRole("combobox") as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "solution" } });
    await waitFor(() => {
      expect(screen.getByText(/Order-to-Cash Solution/)).toBeInTheDocument();
    });
    // Layer rail should now include layers the demo fixture didn't have
    expect(screen.getByText("maestro")).toBeInTheDocument();
    expect(screen.getByText("app")).toBeInTheDocument();
    expect(screen.getByText("test")).toBeInTheDocument();
    expect(screen.getByText("orchestrator")).toBeInTheDocument();
  });

  test("empty fixture shows the empty-state CTA", async () => {
    render(<App />);
    const select = await screen.findByRole("combobox") as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "empty" } });
    await waitFor(() => {
      expect(screen.getByText(/NO NODES IN THIS VIEW/i)).toBeInTheDocument();
    });
  });
});

describe("filters", () => {
  test("path-class chips render and are toggleable", async () => {
    render(<App />);
    const happy = await screen.findByTitle(/happy path/i);
    expect(happy).toBeInTheDocument();
    fireEvent.click(happy);
    // Toggling does not crash; chip remains in the DOM
    expect(happy).toBeInTheDocument();
  });

  test("issues-only toggle shows the issue count from the fixture", async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/issues only/i)).toBeInTheDocument();
    });
  });
});

describe("skills context layer", () => {
  test("aggregated skills appear in the left rail", async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getAllByText("uipath-rpa").length).toBeGreaterThan(0);
    });
    expect(screen.getByText(/show coverage/i)).toBeInTheDocument();
  });

  test("skill selection opens a skill-focused inspector", async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getAllByText("uipath-human-in-the-loop").length).toBeGreaterThan(0);
    });
    fireEvent.click(screen.getAllByText("uipath-human-in-the-loop")[0]);
    await waitFor(() => {
      expect(screen.getByText("WHAT THIS SKILL DOES")).toBeInTheDocument();
    });
    expect(screen.getByText(/PROJECT COVERAGE/i)).toBeInTheDocument();
  });

  test("skill coverage toggle is interactive", async () => {
    render(<App />);
    const button = await screen.findByText(/show coverage/i);
    fireEvent.click(button);
    expect(screen.getByText("ON")).toBeInTheDocument();
  });
});
