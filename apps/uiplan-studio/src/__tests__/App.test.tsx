import React from "react";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import * as copilotCore from "@copilotkit/react-core";

import App from "../App";

beforeEach(() => {
  vi.restoreAllMocks();
});

function getCopilotReadableCalls() {
  return vi.mocked(copilotCore.useCopilotReadable).mock.calls;
}

function getLatestCopilotAction(name: string) {
  return vi
    .mocked(copilotCore.useCopilotAction)
    .mock.calls.map(([payload]) => payload)
    .reverse()
    .find((payload) => payload?.name === name);
}

function getLatestCopilotReadable(description: string) {
  return getCopilotReadableCalls()
    .map(([payload]) => payload)
    .reverse()
    .find((payload) => payload?.description === description);
}

function getDiagramCanvas() {
  return screen.getByLabelText("UiPath diagram builder");
}

function mockJsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    json: async () => body,
  } as Response);
}

test("loads bundle documents from API", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: {
          "spec.md": "# Loaded spec\n",
          "plan.md": "# Loaded plan\n",
          "tasks.md": "# Loaded tasks\n",
        },
      });
    }
    if (url.includes("/diagram/load")) {
      return mockJsonResponse({
        nodes: [
          {
            id: "loaded-diagram",
            title: "Loaded Diagram",
            kind: "workflow",
            description: "Loaded from persisted diagram",
            x: 100,
            y: 100,
            source: "diagram.json",
          },
        ],
        edges: [],
        path: ".cursor/plans/example/diagram.json",
        defaulted: false,
      });
    }
    return mockJsonResponse({});
  });

  render(<App />);
  expect(screen.getByText("UiPlan Studio")).toBeInTheDocument();
  expect(screen.getByTestId("copilot-provider")).toHaveAttribute(
    "data-runtime-url",
    "http://localhost:8000/copilotkit",
  );
  await waitFor(() =>
    expect(screen.getByRole("textbox", { name: "Document content" })).toHaveValue(
      "# Loaded spec\n",
    ),
  );
  expect((await screen.findAllByText("Loaded Diagram")).length).toBeGreaterThan(0);
});

test("renders Graph Explorer and Builder Inspector workspace headings", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: {
          "spec.md": "# Spec\n",
          "plan.md": "# Plan\n",
          "tasks.md": "# Tasks\n",
        },
      });
    }
    return mockJsonResponse({ categories: [] });
  });

  render(<App />);

  expect(await screen.findByRole("heading", { name: "Graph Explorer" })).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: "Builder Inspector" })).toBeInTheDocument();
  expect(await screen.findByRole("button", { name: "Select Workflow Plan" })).toBeInTheDocument();
  expect(await screen.findByRole("button", { name: "Select Ready?" })).toBeInTheDocument();
});

test("shows inspector fallback summary for empty node description", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: {
          "spec.md": "# Spec\n",
          "plan.md": "# Plan\n",
          "tasks.md": "# Tasks\n",
        },
      });
    }
    if (url.includes("/diagram/load")) {
      return mockJsonResponse({
        nodes: [
          {
            id: "plan",
            title: "Workflow Plan",
            kind: "workflow",
            description: "   ",
            x: 120,
            y: 120,
            source: "plan.md",
          },
        ],
        edges: [],
        path: ".cursor/plans/example/diagram.json",
        defaulted: false,
      });
    }
    return mockJsonResponse({ categories: [] });
  });

  render(<App />);

  expect(await screen.findByText("No summary available.")).toBeInTheDocument();
});

test("resolves context for selected node from inspector and shows citations", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: {
          "spec.md": "# Spec\n",
          "plan.md": "# Plan\n",
          "tasks.md": "# Tasks\n",
        },
      });
    }
    if (url.endsWith("/graph/context/resolve")) {
      return mockJsonResponse({
        node_id: "plan",
        query: "Workflow Plan",
        citations: [
          {
            source_type: "library",
            source_id: "uipath-cli/03-agent/deploy",
            snippet: "Use the deploy command with explicit stage checks.",
            strict: true,
          },
        ],
      });
    }
    return mockJsonResponse({ categories: [] });
  });

  render(<App />);
  const resolveButton = await screen.findByRole("button", { name: "Resolve context" });
  fireEvent.click(resolveButton);

  expect(await screen.findByRole("heading", { name: "Resolved citations" })).toBeInTheDocument();
  expect(await screen.findByText("uipath-cli/03-agent/deploy")).toBeInTheDocument();
});

test("publishes typed graph context with semantic node kind", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: {
          "spec.md": "# Spec\n",
          "plan.md": "# Plan\n",
          "tasks.md": "# Tasks\n",
        },
      });
    }
    return mockJsonResponse({ categories: [] });
  });

  render(<App />);
  await screen.findByText("UiPlan Studio");

  const diagramReadableCall = getCopilotReadableCalls().find(
    ([payload]) => payload?.description === "Current UiPlan diagram state",
  );
  expect(diagramReadableCall).toBeDefined();
  expect(diagramReadableCall?.[0]).toEqual(
    expect.objectContaining({
      value: expect.objectContaining({
        typedGraph: expect.objectContaining({
          nodes: expect.arrayContaining([
            expect.objectContaining({
              id: "plan",
              kind: "workflow",
              description: expect.any(String),
            }),
          ]),
        }),
      }),
    }),
  );
});

test("publishes ProjectGraph readable context with selection, visual state, packages, and sources", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: {
          "spec.md": "# Spec\n",
          "plan.md": "# Plan\n",
          "tasks.md": "# Tasks\n",
        },
      });
    }
    if (url.endsWith("/agent/context-sources")) {
      return mockJsonResponse({
        categories: [
          {
            id: "skills",
            title: "Skills",
            description: "Curated UiPath builder skills.",
            sources: [
              {
                id: "uipath-rpa",
                title: "uipath-rpa",
                kind: "skill",
                description: "Build C# and XAML automations.",
                source: ".cursor/skills/uipath-rpa",
                available: true,
              },
            ],
          },
        ],
      });
    }
    return mockJsonResponse({});
  });

  render(<App />);
  await screen.findByText("UiPlan Studio");
  await screen.findByText("Context Sources");

  const graphReadablePayload = getLatestCopilotReadable("Canonical ProjectGraph visual context");
  expect(graphReadablePayload).toEqual(
    expect.objectContaining({
      value: expect.objectContaining({
        canonical_project_graph: expect.objectContaining({
          nodes: expect.arrayContaining([
            expect.objectContaining({ id: "plan", title: "Workflow Plan" }),
          ]),
          edges: expect.arrayContaining([
            expect.objectContaining({ from: "plan", to: "skills" }),
          ]),
        }),
        selected_node: expect.objectContaining({ id: "plan", title: "Workflow Plan" }),
        visible_highlights: {
          focused_node_id: null,
          highlighted_node_ids: [],
          highlighted_edge_ids: [],
          mode: "idle",
          summary: null,
        },
        package_state: expect.objectContaining({
          selected_package_id: null,
          selected_proposal_id: null,
        }),
        context_sources: expect.arrayContaining([
          expect.objectContaining({ id: "skills", source_count: 1 }),
        ]),
      }),
    }),
  );
});

test("Copilot visual actions focus and explain graph nodes without write calls", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: {
          "spec.md": "# Spec\n",
          "plan.md": "# Plan\n",
          "tasks.md": "# Tasks\n",
        },
      });
    }
    return mockJsonResponse({ categories: [] });
  });

  const { container } = render(<App />);
  await screen.findByText("ProjectGraph canvas");

  await act(async () => {
    await getLatestCopilotAction("focusNodes")?.handler({ ids: ["skills", "context_library"] });
  });

  expect(container.querySelectorAll(".diagram-node-highlighted").length).toBe(2);
  expect(screen.getByText("Copilot focus: 2 node(s) highlighted")).toBeInTheDocument();

  await act(async () => {
    await getLatestCopilotAction("tracePath")?.handler({ source: "plan", target: "review" });
  });

  expect(container.querySelectorAll(".diagram-edge-highlighted").length).toBeGreaterThan(0);
  expect(screen.getByText(/Copilot trace:/)).toBeInTheDocument();

  const explanation = await getLatestCopilotAction("explainSelectedNode")?.handler({});
  expect(explanation).toEqual(
    expect.objectContaining({
      id: "plan",
      title: "Workflow Plan",
      connected_edges: expect.any(Array),
      safety: "visual-read-only",
    }),
  );

  const calledUrls = fetchMock.mock.calls.map(([input]) => String(input));
  expect(calledUrls.some((url) => url.includes("/apply"))).toBe(false);
  expect(calledUrls.some((url) => url.includes("/deploy"))).toBe(false);
  expect(calledUrls.some((url) => url.includes("/publish"))).toBe(false);
});

test("Copilot graph actions synchronize readable selection and visible highlights", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: {
          "spec.md": "# Spec\n",
          "plan.md": "# Plan\n",
          "tasks.md": "# Tasks\n",
        },
      });
    }
    return mockJsonResponse({ categories: [] });
  });

  const { container } = render(<App />);
  await screen.findByText("ProjectGraph canvas");

  const actionNames = vi
    .mocked(copilotCore.useCopilotAction)
    .mock.calls.map(([payload]) => payload?.name);
  expect(actionNames).toEqual(
    expect.arrayContaining([
      "focusNodes",
      "tracePath",
      "showDependencies",
      "showContextForNode",
      "renderSubgraph",
      "explainSelectedNode",
    ]),
  );

  fireEvent.click(within(getDiagramCanvas()).getByRole("button", { name: /Ready\?/i }));
  await waitFor(() =>
    expect(getLatestCopilotReadable("Canonical ProjectGraph visual context")?.value).toEqual(
      expect.objectContaining({
        selected_node: expect.objectContaining({ id: "review" }),
        selected_node_id: "review",
      }),
    ),
  );
  await expect(getLatestCopilotAction("explainSelectedNode")?.handler({})).resolves.toEqual(
    expect.objectContaining({ id: "review", title: "Ready?" }),
  );

  await act(async () => {
    await getLatestCopilotAction("showDependencies")?.handler({ nodeId: "plan" });
  });

  expect(container.querySelectorAll(".diagram-edge-highlighted").length).toBe(3);
  expect(screen.getByText("Copilot dependencies: 3 edge(s) around plan")).toBeInTheDocument();

  await act(async () => {
    await getLatestCopilotAction("showContextForNode")?.handler({ nodeId: "plan" });
  });

  expect(container.querySelectorAll(".diagram-node-highlighted").length).toBe(3);
  expect(screen.getByText("Copilot context: 2 context node(s) for plan")).toBeInTheDocument();
  expect(getLatestCopilotReadable("Canonical ProjectGraph visual context")?.value).toEqual(
    expect.objectContaining({
      selected_node: expect.objectContaining({ id: "plan" }),
      visible_highlights: expect.objectContaining({
        focused_node_id: "plan",
        mode: "context",
      }),
    }),
  );

  await act(async () => {
    await getLatestCopilotAction("renderSubgraph")?.handler({
      nodeIds: ["skills"],
      edgeIds: ["planning_agent:uses_skill:skills"],
    });
  });

  expect(container.querySelectorAll(".diagram-node-highlighted").length).toBe(2);
  expect(container.querySelectorAll(".diagram-edge-highlighted").length).toBe(1);
  expect(screen.getByText("Copilot subgraph: 2 node(s), 1 edge(s)")).toBeInTheDocument();
});

test("Copilot visual actions reject invalid node ids and keep path tracing directed", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: {
          "spec.md": "# Spec\n",
          "plan.md": "# Plan\n",
          "tasks.md": "# Tasks\n",
        },
      });
    }
    return mockJsonResponse({ categories: [] });
  });

  const { container } = render(<App />);
  await screen.findByText("ProjectGraph canvas");

  let forwardTrace: unknown;
  await act(async () => {
    forwardTrace = await getLatestCopilotAction("tracePath")?.handler({
      source: "plan",
      target: "review",
    });
  });
  expect(forwardTrace).toEqual(
    expect.objectContaining({
      highlighted_edge_ids: ["planning_agent:drives:if_ready"],
    }),
  );

  await act(async () => {
    await getLatestCopilotAction("tracePath")?.handler({ source: "review", target: "plan" });
  });
  expect(container.querySelectorAll(".diagram-edge-highlighted").length).toBe(0);
  expect(screen.getByText("Copilot trace: no directed path found")).toBeInTheDocument();

  const selectedBeforeInvalidActions = getLatestCopilotReadable(
    "Canonical ProjectGraph visual context",
  )?.value.selected_node_id;

  let invalidTrace: unknown;
  await act(async () => {
    invalidTrace = await getLatestCopilotAction("tracePath")?.handler({
      source: "missing-node",
      target: "review",
    });
  });
  expect(invalidTrace).toEqual(
    expect.objectContaining({
      status: "warning",
      warning: "Unknown node id(s): missing-node",
      highlighted_node_ids: [],
      highlighted_edge_ids: [],
    }),
  );

  for (const [actionName, args] of [
    ["showDependencies", { nodeId: "missing-node" }],
    ["showContextForNode", { nodeId: "missing-node" }],
    ["renderSubgraph", { nodeId: "missing-node", nodeIds: ["skills"] }],
  ] as const) {
    let result: unknown;
    await act(async () => {
      result = await getLatestCopilotAction(actionName)?.handler(args);
    });
    expect(result).toEqual(
      expect.objectContaining({
        status: "warning",
        warning: "Unknown node id(s): missing-node",
      }),
    );
  }

  expect(getLatestCopilotReadable("Canonical ProjectGraph visual context")?.value).toEqual(
    expect.objectContaining({
      selected_node_id: selectedBeforeInvalidActions,
      visible_highlights: expect.objectContaining({
        highlighted_node_ids: [],
        highlighted_edge_ids: [],
      }),
    }),
  );
});

test("renders starter ProjectGraph canvas with branch badges and node drilldown", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: {
          "spec.md": "# Spec\n",
          "plan.md": "# Plan\n",
          "tasks.md": "# Tasks\n",
        },
      });
    }
    return mockJsonResponse({ categories: [] });
  });

  const { container } = render(<App />);
  await screen.findByText("ProjectGraph canvas");

  expect(within(getDiagramCanvas()).getByRole("button", { name: /Chat Trigger/i })).toBeInTheDocument();
  expect(within(getDiagramCanvas()).getByRole("button", { name: /Needs Context/i })).toBeInTheDocument();
  expect(screen.getAllByText("ready").length).toBeGreaterThan(0);
  expect(screen.getAllByText("needs context").length).toBeGreaterThan(0);
  expect(container.querySelector(".diagram-edge-success")).not.toBeNull();
  expect(container.querySelector(".diagram-edge-fallback")).not.toBeNull();

  fireEvent.click(within(getDiagramCanvas()).getByRole("button", { name: /Needs Context/i }));

  const drilldown = screen.getByLabelText("Selected node drilldown");
  expect(within(drilldown).getByText("outcome")).toBeInTheDocument();
  expect(within(drilldown).getByText("fallback_branch")).toBeInTheDocument();
  expect(within(drilldown).getByText("needs_context")).toBeInTheDocument();
  expect(container.querySelector(".diagram-node-role-fallback_branch")).not.toBeNull();
  expect(container.querySelector(".diagram-node-status-needs_context")).not.toBeNull();
});

test("saves, reviews, previews, applies, and shows readiness", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: {
          "spec.md": "# Spec\n",
          "plan.md": "# Plan\n",
          "tasks.md": "# Tasks\n",
        },
      });
    }
    if (url.includes("/diagram/load")) {
      return mockJsonResponse({
        nodes: [
          {
            id: "plan",
            title: "Plan",
            kind: "workflow",
            description: "Diagram plan",
            x: 292,
            y: 180,
            source: "plan.md",
          },
          {
            id: "tasks",
            title: "Tasks",
            kind: "document",
            description: "Diagram tasks",
            x: 48,
            y: 300,
            source: "tasks.md",
          },
        ],
        edges: [{ id: "tasks-plan", from: "tasks", to: "plan", label: "tracks" }],
        defaulted: false,
      });
    }
    if (url.endsWith("/diagram/save")) {
      return mockJsonResponse({
        path: ".cursor/plans/example/diagram.json",
        bytes_written: 10,
        nodes: [],
        edges: [],
      });
    }
    if (url.endsWith("/review/run")) {
      return mockJsonResponse({
        findings: [
          {
            rule: "RULE_SPEC_DETAIL",
            severity: "error",
            message: "Spec is missing detail",
            document: "spec.md",
          },
        ],
        acceptance_ready: false,
      });
    }
    if (url.endsWith("/lifecycle/readiness")) {
      return mockJsonResponse({
        status: "blocked",
        acceptance_ready: false,
        error_count: 1,
      });
    }
    if (url.endsWith("/generate/section-preview")) {
      return mockJsonResponse({
        preview_id: "preview-manual",
        proposed_content: "# Updated spec\n",
        diff: "--- spec.md\n+++ spec.md\n-# Spec\n+# Updated spec\n",
      });
    }
    if (url.endsWith("/generate/diagram-preview")) {
      return mockJsonResponse({
        preview_id: "preview-1",
        proposed_content: "# Spec\n\n<!-- uiplan-diagram-generated:start -->",
        diff: "--- spec.md\n+++ spec.md\n+<!-- uiplan-diagram-generated:start -->",
      });
    }
    if (url.endsWith("/generate/apply")) {
      return mockJsonResponse({
        path: ".cursor/plans/example/spec.md",
        backup_path: ".cursor/plans/example/spec.md.bak",
        bytes_written: 18,
      });
    }
    throw new Error(`Unexpected fetch call: ${url}`);
  });

  render(<App />);
  await waitFor(() =>
    expect(screen.getByRole("textbox", { name: "Document content" })).toHaveValue("# Spec\n"),
  );
  expect(await screen.findByText("Diagram tasks")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Apply preview" })).toBeDisabled();

  fireEvent.change(screen.getByRole("textbox", { name: "Document content" }), {
    target: { value: "# Updated spec\n" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Preview document changes" }));

  await waitFor(() =>
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/generate/section-preview",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"document_name":"spec.md"'),
      }),
    ),
  );

  fireEvent.click(screen.getByRole("button", { name: "Save diagram" }));

  await waitFor(() =>
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/diagram/save",
      expect.objectContaining({
        method: "POST",
      }),
    ),
  );
  const diagramSaveCall = fetchMock.mock.calls.find(
    ([input]) => String(input) === "http://localhost:8000/diagram/save",
  );
  expect(diagramSaveCall).toBeDefined();
  const diagramSaveBody = JSON.parse(String(diagramSaveCall?.[1]?.body));
  expect(diagramSaveBody).toEqual({
    bundle_root: ".cursor/plans/example",
    nodes: [
      {
        id: "plan",
        title: "Plan",
        kind: "workflow",
        description: "Diagram plan",
        x: 292,
        y: 180,
        source: "plan.md",
      },
      {
        id: "tasks",
        title: "Tasks",
        kind: "document",
        description: "Diagram tasks",
        x: 48,
        y: 300,
        source: "tasks.md",
      },
    ],
    edges: [{ id: "tasks-plan", from: "tasks", to: "plan", label: "tracks" }],
  });

  fireEvent.click(screen.getByRole("button", { name: "Run review" }));
  expect(await screen.findByRole("button", { name: "[error] RULE_SPEC_DETAIL - spec.md" }))
    .toBeInTheDocument();
  expect(screen.getByText("Status: blocked")).toBeInTheDocument();
  expect(screen.getByText("Error findings: 1")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Preview diagram into document" }));
  expect(await screen.findByText("Diff Preview")).toBeInTheDocument();
  expect(screen.getByText(/Document edits and diagram generation are preview-only/))
    .toBeInTheDocument();

  const diagramPreviewCall = fetchMock.mock.calls.find(
    ([input]) => String(input) === "http://localhost:8000/generate/diagram-preview",
  );
  expect(diagramPreviewCall).toBeDefined();
  const diagramPreviewBody = JSON.parse(String(diagramPreviewCall?.[1]?.body));
  expect(diagramPreviewBody).toEqual({
    bundle_root: ".cursor/plans/example",
    document_name: "spec.md",
    nodes: [
      {
        id: "plan",
        title: "Plan",
        kind: "workflow",
        description: "Diagram plan",
        x: 292,
        y: 180,
        source: "plan.md",
      },
      {
        id: "tasks",
        title: "Tasks",
        kind: "document",
        description: "Diagram tasks",
        x: 48,
        y: 300,
        source: "tasks.md",
      },
    ],
    edges: [{ id: "tasks-plan", from: "tasks", to: "plan", label: "tracks" }],
    focus: "plan",
    context: [],
  });

  const applyButton = screen.getByRole("button", { name: "Apply preview" });
  expect(applyButton).toBeEnabled();
  fireEvent.click(applyButton);

  await waitFor(() =>
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/generate/apply",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ preview_id: "preview-1" }),
      }),
    ),
  );
});

test("searches library context and includes source in generation", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: {
          "spec.md": "# Spec\n",
          "plan.md": "# Plan\n",
          "tasks.md": "# Tasks\n",
        },
      });
    }
    if (url.endsWith("/agent/library-context")) {
      return mockJsonResponse({
        query: "deploy",
        items: [
          {
            book_id: "uipath-cli",
            chapter_id: "03-agent",
            section_id: "deploy",
            score: 8,
            snippet: "Deploy docs",
            full_text: "Deploy full text",
          },
        ],
      });
    }
    if (url.endsWith("/generate/diagram-preview")) {
      return mockJsonResponse({
        preview_id: "preview-ctx",
        proposed_content: "# Spec\nWith context\n",
        diff: "--- spec.md\n+++ spec.md\n+<!-- generated_with_library_context -->",
      });
    }
    if (url.endsWith("/generate/apply")) {
      return mockJsonResponse({
        path: ".cursor/plans/example/spec.md",
        backup_path: ".cursor/plans/example/spec.md.bak",
        bytes_written: 18,
      });
    }
    return mockJsonResponse({});
  });

  render(<App />);
  await waitFor(() =>
    expect(screen.getByRole("textbox", { name: "Document content" })).toHaveValue("# Spec\n"),
  );

  fireEvent.change(screen.getByRole("textbox", { name: "Library query" }), {
    target: { value: "deploy" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Search library" }));
  expect((await screen.findAllByText("uipath-cli/03-agent/deploy")).length).toBeGreaterThan(0);

  fireEvent.click(screen.getByRole("button", { name: "Preview diagram into document" }));
  expect(await screen.findByText("Generated with context from uipath-cli/03-agent/deploy"))
    .toBeInTheDocument();
});

test("renders context source cards and adds or focuses source nodes", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: {
          "spec.md": "# Spec\n",
          "plan.md": "# Plan\n",
          "tasks.md": "# Tasks\n",
        },
      });
    }
    if (url.endsWith("/agent/context-sources")) {
      return mockJsonResponse({
        categories: [
          {
            id: "skills",
            title: "Skills",
            description: "Curated UiPath builder skills.",
            sources: [
              {
                id: "uipath-rpa",
                title: "uipath-rpa",
                kind: "skill",
                description: "Build C# and XAML automations.",
                source: ".cursor/skills/uipath-rpa",
                available: true,
              },
              {
                id: "uipath-missing",
                title: "uipath-missing",
                kind: "skill",
                description: "Missing local skill.",
                source: ".cursor/skills/uipath-missing",
                available: false,
              },
            ],
          },
          {
            id: "library",
            title: "Library Books",
            description: "Lightweight book identifiers.",
            sources: [
              {
                id: "uipath-cli",
                title: "UiPath CLI docs",
                kind: "library",
                description: "CLI commands and workflow references.",
                source: "uipath-cli",
                available: true,
              },
            ],
          },
        ],
      });
    }
    return mockJsonResponse({});
  });

  render(<App />);
  await waitFor(() =>
    expect(screen.getByRole("textbox", { name: "Document content" })).toHaveValue("# Spec\n"),
  );

  expect(await screen.findByText("Context Sources")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Add uipath-rpa source" }));
  expect(screen.getByLabelText("Node title")).toHaveValue("uipath-rpa");

  fireEvent.change(screen.getByLabelText("Node description"), {
    target: { value: "Edited RPA skill card" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Add uipath-rpa source" }));
  expect(screen.getByLabelText("Node description")).toHaveValue("Edited RPA skill card");

  expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(0);
  const unavailableButton = screen.getByRole("button", {
    name: "Unavailable: uipath-missing source",
  });
  expect(unavailableButton).toBeDisabled();
  fireEvent.click(unavailableButton);
  expect(screen.getByLabelText("Node title")).toHaveValue("uipath-rpa");

  fireEvent.click(screen.getByRole("button", { name: "Add UiPath CLI docs source" }));
  expect(screen.getByLabelText("Node title")).toHaveValue("UiPath CLI docs");
});

test("sends assistant message and renders suggested diagram nodes", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: {
          "spec.md": "# Spec\n",
          "plan.md": "# Plan\n",
          "tasks.md": "# Tasks\n",
        },
      });
    }
    if (url.endsWith("/agent/chat")) {
      expect(init?.body).toContain("Show me the skill context");
      return mockJsonResponse({
        message: "I added suggested diagram context focused on Implementation Plan.",
        suggested_nodes: [
          {
            id: "skill-uipath-platform",
            title: "uipath-platform",
            kind: "skill",
            description: "Use for Orchestrator and solution lifecycle.",
            x: 760,
            y: 92,
            source: ".cursor/skills/uipath-platform",
          },
        ],
      });
    }
    return mockJsonResponse({});
  });

  render(<App />);
  await screen.findByText("Build with UiPath context");
  expect(
    screen.getByText(/Copilot can list context sources, search library context/i),
  ).toBeInTheDocument();

  fireEvent.change(screen.getByRole("textbox", { name: "Copilot message" }), {
    target: { value: "Show me the skill context" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));

  expect(await screen.findByText("I added suggested diagram context focused on Implementation Plan."))
    .toBeInTheDocument();
  expect((await screen.findAllByText("uipath-platform")).length).toBeGreaterThan(0);
});

test("drafts plan and scaffold package requests from Copilot controls", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: { "spec.md": "# Spec\n", "plan.md": "# Plan\n", "tasks.md": "# Tasks\n" },
      });
    }
    return mockJsonResponse({});
  });

  render(<App />);
  await screen.findByText("Build with UiPath context");

  fireEvent.click(screen.getByRole("button", { name: "Draft Plan package request" }));
  expect(await screen.findByText(/Drafted Plan package request/i)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Draft Scaffold package request" }));
  expect(await screen.findByText(/Drafted Scaffold package request/i)).toBeInTheDocument();

  const calledUrls = fetchMock.mock.calls.map(([input]) => String(input));
  expect(calledUrls.some((url) => url.includes("/generation/packages"))).toBe(false);
  expect(calledUrls.some((url) => url.includes("/apply"))).toBe(false);
});

test("applies copilot add-node action and updates graph selection", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: {
          "spec.md": "# Spec\n",
          "plan.md": "# Plan\n",
          "tasks.md": "# Tasks\n",
        },
      });
    }
    if (url.endsWith("/graph/actions/execute")) {
      const requestBody = typeof init?.body === "string" ? JSON.parse(init.body) : {};
      expect(requestBody).toEqual(
        expect.objectContaining({
          action: "add_node",
          payload: expect.objectContaining({
            id: expect.stringMatching(/^copilot-node-/),
            title: "Copilot Added Node",
            kind: "workflow",
          }),
          workspace: expect.objectContaining({
            nodes: expect.any(Array),
            edges: expect.any(Array),
          }),
        }),
      );
      const addedNode = {
        id: requestBody.payload.id,
        title: requestBody.payload.title,
        kind: requestBody.payload.kind,
        description: requestBody.payload.description,
        x: requestBody.payload.x,
        y: requestBody.payload.y,
        source: requestBody.payload.source,
      };
      return mockJsonResponse({
        message: "Node added",
        workspace: {
          nodes: [...requestBody.workspace.nodes, addedNode],
          edges: requestBody.workspace.edges,
        },
      });
    }
    return mockJsonResponse({ categories: [] });
  });

  render(<App />);
  await screen.findByText("Build with UiPath context");
  fireEvent.click(screen.getByRole("button", { name: "Apply Copilot add node" }));

  await waitFor(() =>
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/graph/actions/execute",
      expect.objectContaining({ method: "POST" }),
    ),
  );
  expect(await screen.findByText("Focused on: Copilot Added Node")).toBeInTheDocument();
  expect(
    await within(getDiagramCanvas()).findByRole("button", { name: /Copilot Added Node/i }),
  ).toBeInTheDocument();
});

test("adds, edits, connects, and deletes a non-core node", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: {
          "spec.md": "# Spec\n",
          "plan.md": "# Plan\n",
          "tasks.md": "# Tasks\n",
        },
      });
    }
    if (url.endsWith("/diagram/save")) {
      return mockJsonResponse({
        path: ".cursor/plans/example/diagram.json",
        bytes_written: 10,
        nodes: [],
        edges: [],
      });
    }
    return mockJsonResponse({});
  });

  render(<App />);
  await waitFor(() =>
    expect(screen.getByRole("textbox", { name: "Document content" })).toHaveValue("# Spec\n"),
  );

  fireEvent.click(screen.getByRole("button", { name: "Add workflow node" }));
  fireEvent.change(screen.getByLabelText("Node title"), {
    target: { value: "Invoice workflow" },
  });
  fireEvent.change(screen.getByLabelText("Node description"), {
    target: { value: "Routes invoice approvals" },
  });
  fireEvent.change(screen.getByLabelText("Node source"), {
    target: { value: "invoice.flow" },
  });

  expect(
    within(getDiagramCanvas()).getByRole("button", { name: /Invoice workflow/i }),
  ).toBeInTheDocument();
  expect(screen.getAllByText("Routes invoice approvals").length).toBeGreaterThan(0);

  fireEvent.change(screen.getByLabelText("Edge target"), {
    target: { value: "plan" },
  });
  fireEvent.change(screen.getByLabelText("Edge label"), {
    target: { value: "feeds" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Create edge" }));

  fireEvent.click(screen.getByRole("button", { name: "Save diagram" }));
  await waitFor(() =>
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/diagram/save",
      expect.objectContaining({ method: "POST" }),
    ),
  );
  const saveBody = JSON.parse(
    String(
      fetchMock.mock.calls.find(
        ([input]) => String(input) === "http://localhost:8000/diagram/save",
      )?.[1]?.body,
    ),
  );
  expect(saveBody.nodes).toEqual(
    expect.arrayContaining([
      expect.objectContaining({
        title: "Invoice workflow",
        description: "Routes invoice approvals",
        source: "invoice.flow",
      }),
    ]),
  );
  expect(saveBody.edges).toEqual(
    expect.arrayContaining([
      expect.objectContaining({
        from: expect.stringMatching(/^workflow-/),
        to: "plan",
        label: "feeds",
      }),
    ]),
  );

  fireEvent.click(screen.getByRole("button", { name: "Delete selected node" }));
  expect(
    within(getDiagramCanvas()).queryByRole("button", { name: /Invoice workflow/i }),
  ).not.toBeInTheDocument();
});

test("prevents deleting core default nodes", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: {
          "spec.md": "# Spec\n",
          "plan.md": "# Plan\n",
          "tasks.md": "# Tasks\n",
        },
      });
    }
    return mockJsonResponse({});
  });

  render(<App />);
  await waitFor(() =>
    expect(screen.getByRole("textbox", { name: "Document content" })).toHaveValue("# Spec\n"),
  );

  fireEvent.click(within(getDiagramCanvas()).getByRole("button", { name: /Workflow Plan/i }));
  expect(screen.getByRole("button", { name: "Delete selected node" })).toBeDisabled();
  expect(screen.getByText("Core default nodes cannot be deleted.")).toBeInTheDocument();
});

test("normalizes selection after loading a diagram without the default node", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: {
          "spec.md": "# Spec\n",
          "plan.md": "# Plan\n",
          "tasks.md": "# Tasks\n",
        },
      });
    }
    if (url.includes("/diagram/load")) {
      return mockJsonResponse({
        nodes: [
          {
            id: "alpha",
            title: "Alpha Node",
            kind: "workflow",
            description: "Loaded workflow node",
            x: 100,
            y: 100,
            source: "alpha.flow",
          },
          {
            id: "beta",
            title: "Beta Node",
            kind: "skill",
            description: "Loaded skill node",
            x: 340,
            y: 100,
            source: "beta.skill",
          },
        ],
        edges: [],
        defaulted: false,
      });
    }
    if (url.endsWith("/diagram/save")) {
      return mockJsonResponse({
        path: ".cursor/plans/example/diagram.json",
        bytes_written: 10,
        nodes: [],
        edges: [],
      });
    }
    return mockJsonResponse({});
  });

  render(<App />);
  await within(getDiagramCanvas()).findByRole("button", { name: /Alpha Node/i });
  expect(screen.getByLabelText("Node title")).toHaveValue("Alpha Node");

  fireEvent.change(screen.getByLabelText("Edge target"), {
    target: { value: "beta" },
  });
  fireEvent.change(screen.getByLabelText("Edge label"), {
    target: { value: "links" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Create edge" }));
  fireEvent.click(screen.getByRole("button", { name: "Save diagram" }));

  await waitFor(() =>
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/diagram/save",
      expect.objectContaining({ method: "POST" }),
    ),
  );
  const saveBody = JSON.parse(
    String(
      fetchMock.mock.calls.find(
        ([input]) => String(input) === "http://localhost:8000/diagram/save",
      )?.[1]?.body,
    ),
  );
  expect(saveBody.edges).toEqual([
    expect.objectContaining({ from: "alpha", to: "beta", label: "links" }),
  ]);
  expect(saveBody.edges).not.toEqual([
    expect.objectContaining({ from: "plan" }),
  ]);
});

test("generates Plan and Scaffold approval packages with stage gating and no deploy actions", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: { "spec.md": "# Spec\n", "plan.md": "# Plan\n", "tasks.md": "# Tasks\n" },
      });
    }
    if (url.endsWith("/generation/packages") && !url.includes("?")) {
      const requestBody = typeof init?.body === "string" ? JSON.parse(init.body) : {};
      const requestedStages = Array.isArray(requestBody.stages) ? requestBody.stages : [];
      const scaffoldRequested = requestedStages.includes("02-scaffold");
      return mockJsonResponse({
        package_id: scaffoldRequested ? "pkg-2" : "pkg-1",
        graph_id: "graph-1",
        bundle_root: ".cursor/plans/example",
        generated_stages: scaffoldRequested ? ["01-plan", "02-scaffold"] : ["01-plan"],
        created_at: "2026-05-05T00:00:00Z",
        schema_id: "https://uipath.local/uiplan/approval-package.v1",
        schema_version: "v1",
        generator_version: "uiplan-studio-generation-graph-phase-0",
        safety_policy: { direct_writes: false, external_mutation: false },
      });
    }
    if (url.includes("/generation/packages/pkg-1")) {
      return mockJsonResponse({
        manifest: {
          package_id: "pkg-1",
          graph_id: "graph-1",
          bundle_root: ".cursor/plans/example",
          generated_stages: ["01-plan"],
          created_at: "2026-05-05T00:00:00Z",
          schema_id: "https://uipath.local/uiplan/approval-package.v1",
          schema_version: "v1",
          generator_version: "uiplan-studio-generation-graph-phase-0",
          safety_policy: { direct_writes: false, external_mutation: false },
        },
        approval_state: {
          package_id: "pkg-1",
          current_stage: "01-plan",
          stage_statuses: {
            "01-plan": "ready_for_review",
            "02-scaffold": "not_started",
            "03-code": "not_started",
            "04-tests": "not_started",
            "05-validation": "not_started",
          },
          proposals: {},
          applied_preview_ids: [],
          superseded_preview_ids: [],
          reviewer_notes: [],
          updated_at: "2026-05-05T00:00:00Z",
        },
        stages: [],
        proposals: [],
      });
    }
    if (url.includes("/generation/packages/pkg-2")) {
      return mockJsonResponse({
        manifest: {
          package_id: "pkg-2",
          graph_id: "graph-1",
          bundle_root: ".cursor/plans/example",
          generated_stages: ["01-plan", "02-scaffold"],
          created_at: "2026-05-05T00:00:00Z",
          schema_id: "https://uipath.local/uiplan/approval-package.v1",
          schema_version: "v1",
          generator_version: "uiplan-studio-generation-graph-phase-0",
          safety_policy: { direct_writes: false, external_mutation: false },
        },
        approval_state: {
          package_id: "pkg-2",
          current_stage: "02-scaffold",
          stage_statuses: {
            "01-plan": "approved",
            "02-scaffold": "ready_for_review",
            "03-code": "not_started",
            "04-tests": "not_started",
            "05-validation": "not_started",
          },
          proposals: {},
          applied_preview_ids: [],
          superseded_preview_ids: [],
          reviewer_notes: [],
          updated_at: "2026-05-05T00:00:00Z",
        },
        stages: [],
        proposals: [],
      });
    }
    return mockJsonResponse({ categories: [] });
  });

  render(<App />);
  await screen.findByText("UiPlan Studio");
  fireEvent.click(await screen.findByRole("button", { name: "Generate Plan Package" }));

  await waitFor(() =>
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/generation/packages",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"stages":["01-plan"]'),
      }),
    ),
  );
  expect(await screen.findByText("Approval Package")).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Plan ready_for_review" })).toBeInTheDocument();
  expect(screen.getByText("Plan: ready_for_review")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Deploy/i })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Publish/i })).not.toBeInTheDocument();
  expect(screen.getByText(/Plan exists but is not approved/)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Generate Scaffold Package" }));
  await waitFor(() =>
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/generation/packages",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"stages":["01-plan","02-scaffold"]'),
      }),
    ),
  );
  const packageCalls = fetchMock.mock.calls.filter(
    ([input]) => String(input) === "http://localhost:8000/generation/packages",
  );
  const scaffoldRequestBody = JSON.parse(String(packageCalls.at(-1)?.[1]?.body));
  expect(scaffoldRequestBody.graph.nodes[0]).toEqual(
    expect.objectContaining({
      role: expect.any(String),
      output_type: expect.any(String),
      project_types: expect.any(Array),
    }),
  );
  expect(scaffoldRequestBody.graph.edges[0]).toEqual(
    expect.objectContaining({
      edge_type: expect.any(String),
    }),
  );
  expect(await screen.findByRole("tab", { name: "Scaffold ready_for_review" })).toBeInTheDocument();
  expect(screen.getByText("Scaffold: ready_for_review")).toBeInTheDocument();
});

test("shows actionable error when package generation endpoint fails", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: { "spec.md": "# Spec\n", "plan.md": "# Plan\n", "tasks.md": "# Tasks\n" },
      });
    }
    if (url.endsWith("/generation/packages")) {
      return Promise.resolve({
        ok: false,
        status: 503,
        json: async () => ({ detail: "generation unavailable" }),
      } as Response);
    }
    return mockJsonResponse({ categories: [] });
  });

  render(<App />);
  await screen.findByText("UiPlan Studio");
  fireEvent.click(await screen.findByRole("button", { name: "Generate Plan Package" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Plan package generation failed. Verify the generation service is running and retry. (Request failed: 503)",
  );
});

test("renders repeated readiness badges without duplicate-key warnings", async () => {
  const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: { "spec.md": "# Spec\n", "plan.md": "# Plan\n", "tasks.md": "# Tasks\n" },
      });
    }
    if (url.endsWith("/generation/packages") && !url.includes("?")) {
      return mockJsonResponse({
        package_id: "pkg-duplicate-badges",
        graph_id: "graph-1",
        bundle_root: ".cursor/plans/example",
        generated_stages: ["01-plan"],
        created_at: "2026-05-05T00:00:00Z",
        schema_id: "https://uipath.local/uiplan/approval-package.v1",
        schema_version: "v1",
        generator_version: "uiplan-studio-generation-graph-phase-0",
        safety_policy: { direct_writes: false, external_mutation: false },
      });
    }
    if (url.includes("/generation/packages/pkg-duplicate-badges")) {
      return mockJsonResponse({
        manifest: {
          package_id: "pkg-duplicate-badges",
          graph_id: "graph-1",
          bundle_root: ".cursor/plans/example",
          generated_stages: ["01-plan"],
          created_at: "2026-05-05T00:00:00Z",
          schema_id: "https://uipath.local/uiplan/approval-package.v1",
          schema_version: "v1",
          generator_version: "uiplan-studio-generation-graph-phase-0",
          safety_policy: { direct_writes: false, external_mutation: false },
        },
        approval_state: {
          package_id: "pkg-duplicate-badges",
          current_stage: "01-plan",
          stage_statuses: {
            "01-plan": "ready_for_review",
            "02-scaffold": "not_started",
            "03-code": "not_started",
            "04-tests": "not_started",
            "05-validation": "not_started",
          },
          proposals: {},
          applied_preview_ids: [],
          superseded_preview_ids: [],
          reviewer_notes: [],
          updated_at: "2026-05-05T00:00:00Z",
        },
        stages: [],
        proposals: [
          {
            proposal_id: "01-plan:proposal-a",
            stage_id: "01-plan",
            target_path: "docs/proposal-a.md",
            file_kind: "document",
            owning_node_ids: ["plan"],
            project_type_ids: ["docs"],
            proposed_content_hash: "hash-a",
            base_hash: null,
            diff_path: "stages/01-plan/diffs/proposal-a.diff",
            proposal_path: "stages/01-plan/proposals/proposal-a.md",
            citations: [],
            findings: [],
            apply_eligible: true,
          },
          {
            proposal_id: "01-plan:proposal-b",
            stage_id: "01-plan",
            target_path: "docs/proposal-b.md",
            file_kind: "document",
            owning_node_ids: ["plan"],
            project_type_ids: ["docs"],
            proposed_content_hash: "hash-b",
            base_hash: null,
            diff_path: "stages/01-plan/diffs/proposal-b.diff",
            proposal_path: "stages/01-plan/proposals/proposal-b.md",
            citations: [],
            findings: [],
            apply_eligible: true,
          },
        ],
      });
    }
    return mockJsonResponse({ categories: [] });
  });

  render(<App />);
  await screen.findByText("UiPlan Studio");
  fireEvent.click(await screen.findByRole("button", { name: "Generate Plan Package" }));
  const duplicatedBadges = await screen.findAllByText("Plan: ready_for_review");
  expect(duplicatedBadges.length).toBeGreaterThan(1);

  expect(
    consoleErrorSpy.mock.calls.some(([msg]) =>
      String(msg).includes("Encountered two children with the same key"),
    ),
  ).toBe(false);
});

test("requires proposal preview for currently selected proposal before apply", async () => {
  const approvedProposalIds = new Set<string>();
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: { "spec.md": "# Spec\n", "plan.md": "# Plan\n", "tasks.md": "# Tasks\n" },
      });
    }
    if (url.endsWith("/generation/packages") && !url.includes("?")) {
      return mockJsonResponse({
        package_id: "pkg-1",
        graph_id: "graph-1",
        bundle_root: ".cursor/plans/example",
        generated_stages: ["01-plan"],
        created_at: "2026-05-05T00:00:00Z",
        schema_id: "https://uipath.local/uiplan/approval-package.v1",
        schema_version: "v1",
        generator_version: "uiplan-studio-generation-graph-phase-0",
        safety_policy: { direct_writes: false, external_mutation: false },
      });
    }
    if (url.includes("/generation/packages/pkg-1?")) {
      return mockJsonResponse({
        manifest: {
          package_id: "pkg-1",
          graph_id: "graph-1",
          bundle_root: ".cursor/plans/example",
          generated_stages: ["01-plan"],
          created_at: "2026-05-05T00:00:00Z",
          schema_id: "https://uipath.local/uiplan/approval-package.v1",
          schema_version: "v1",
          generator_version: "uiplan-studio-generation-graph-phase-0",
          safety_policy: { direct_writes: false, external_mutation: false },
        },
        approval_state: {
          package_id: "pkg-1",
          current_stage: "01-plan",
          stage_statuses: {
            "01-plan": "ready_for_review",
            "02-scaffold": "not_started",
            "03-code": "not_started",
            "04-tests": "not_started",
            "05-validation": "not_started",
          },
          proposals: {
            "01-plan:proposal-a": {
              proposal_id: "01-plan:proposal-a",
              stage_id: "01-plan",
              review_status: approvedProposalIds.has("01-plan:proposal-a")
                ? "approved"
                : "ready_for_review",
              apply_status: "not_started",
              source_graph_hash: "graph-hash",
              context_manifest_hash: "context-hash",
              proposal_hash: "hash-a",
              updated_at: "2026-05-05T00:00:00Z",
            },
            "01-plan:proposal-b": {
              proposal_id: "01-plan:proposal-b",
              stage_id: "01-plan",
              review_status: approvedProposalIds.has("01-plan:proposal-b")
                ? "approved"
                : "ready_for_review",
              apply_status: "not_started",
              source_graph_hash: "graph-hash",
              context_manifest_hash: "context-hash",
              proposal_hash: "hash-b",
              updated_at: "2026-05-05T00:00:00Z",
            },
          },
          applied_preview_ids: [],
          superseded_preview_ids: [],
          reviewer_notes: [],
          updated_at: "2026-05-05T00:00:00Z",
        },
        stages: [],
        proposals: [
          {
            proposal_id: "01-plan:proposal-a",
            stage_id: "01-plan",
            target_path: "docs/proposal-a.md",
            file_kind: "document",
            owning_node_ids: ["plan"],
            project_type_ids: ["docs"],
            proposed_content_hash: "hash-a",
            base_hash: null,
            diff_path: "stages/01-plan/diffs/proposal-a.diff",
            proposal_path: "stages/01-plan/proposals/proposal-a.md",
            citations: [],
            findings: [],
            apply_eligible: true,
          },
          {
            proposal_id: "01-plan:proposal-b",
            stage_id: "01-plan",
            target_path: "docs/proposal-b.md",
            file_kind: "document",
            owning_node_ids: ["plan"],
            project_type_ids: ["docs"],
            proposed_content_hash: "hash-b",
            base_hash: null,
            diff_path: "stages/01-plan/diffs/proposal-b.diff",
            proposal_path: "stages/01-plan/proposals/proposal-b.md",
            citations: [],
            findings: [],
            apply_eligible: true,
          },
        ],
      });
    }
    if (url.includes("/proposals/01-plan%3Aproposal-a/preview")) {
      return mockJsonResponse({
        preview_id: "preview-a",
        proposal_id: "01-plan:proposal-a",
        target_path: "docs/proposal-a.md",
        diff: "--- docs/proposal-a.md\n+++ docs/proposal-a.md\n+# Proposal A\n",
      });
    }
    if (url.includes("/proposals/01-plan%3Aproposal-b/preview")) {
      return mockJsonResponse({
        preview_id: "preview-b",
        proposal_id: "01-plan:proposal-b",
        target_path: "docs/proposal-b.md",
        diff: "--- docs/proposal-b.md\n+++ docs/proposal-b.md\n+# Proposal B\n",
      });
    }
    if (url.includes("/generation/packages/pkg-1/approval")) {
      const body = typeof init?.body === "string" ? JSON.parse(init.body) : {};
      if (body.target === "proposal" && body.next_status === "approved") {
        approvedProposalIds.add(body.target_id);
      }
      return mockJsonResponse({ approval_state: { proposals: {} } });
    }
    if (url.includes("/proposals/01-plan%3Aproposal-b/apply")) {
      const body = typeof init?.body === "string" ? JSON.parse(init.body) : {};
      expect(body.preview_id).toBe("preview-b");
      return mockJsonResponse({
        approval_state: {
          package_id: "pkg-1",
          current_stage: "01-plan",
          stage_statuses: {
            "01-plan": "ready_for_review",
            "02-scaffold": "not_started",
            "03-code": "not_started",
            "04-tests": "not_started",
            "05-validation": "not_started",
          },
          proposals: {},
          applied_preview_ids: ["preview-b"],
          superseded_preview_ids: [],
          reviewer_notes: [],
          updated_at: "2026-05-05T00:00:00Z",
        },
      });
    }
    return mockJsonResponse({ categories: [] });
  });

  render(<App />);
  await screen.findByText("UiPlan Studio");
  fireEvent.click(await screen.findByRole("button", { name: "Generate Plan Package" }));
  await screen.findByText("Approval Package");

  fireEvent.click(screen.getByRole("button", { name: "Preview proposal" }));
  await waitFor(() =>
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/proposals/01-plan%3Aproposal-a/preview"),
      expect.objectContaining({ method: "POST" }),
    ),
  );

  fireEvent.click(screen.getByRole("button", { name: "Proposal: docs/proposal-b.md" }));
  expect(screen.getByRole("button", { name: "Apply proposal" })).toBeDisabled();

  fireEvent.click(screen.getByRole("button", { name: "Preview proposal" }));
  await waitFor(() =>
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/proposals/01-plan%3Aproposal-b/preview"),
      expect.objectContaining({ method: "POST" }),
    ),
  );
  expect(screen.getByLabelText("Proposal diff")).toHaveTextContent("+# Proposal B");

  const applyProposalButton = screen.getByRole("button", { name: "Apply proposal" });
  expect(applyProposalButton).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Approve proposal" }));
  await waitFor(() =>
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/generation/packages/pkg-1/approval"),
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"target_id":"01-plan:proposal-b"'),
      }),
    ),
  );
  const approvedApplyProposalButton = await screen.findByRole("button", { name: "Apply proposal" });
  expect(approvedApplyProposalButton).toBeEnabled();
  fireEvent.click(approvedApplyProposalButton);

  await waitFor(() =>
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/proposals/01-plan%3Aproposal-b/apply"),
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"preview_id":"preview-b"'),
      }),
    ),
  );
});

test("surfaces backend errors when applying an approved proposal fails", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.includes("/bundle/load")) {
      return mockJsonResponse({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: { "spec.md": "# Spec\n", "plan.md": "# Plan\n", "tasks.md": "# Tasks\n" },
      });
    }
    if (url.endsWith("/generation/packages") && !url.includes("?")) {
      return mockJsonResponse({
        package_id: "pkg-apply-fails",
        graph_id: "graph-1",
        bundle_root: ".cursor/plans/example",
        generated_stages: ["01-plan"],
        created_at: "2026-05-05T00:00:00Z",
        schema_id: "https://uipath.local/uiplan/approval-package.v1",
        schema_version: "v1",
        generator_version: "uiplan-studio-generation-graph-phase-0",
        safety_policy: { direct_writes: false, external_mutation: false },
      });
    }
    if (url.includes("/generation/packages/pkg-apply-fails?")) {
      return mockJsonResponse({
        manifest: {
          package_id: "pkg-apply-fails",
          graph_id: "graph-1",
          bundle_root: ".cursor/plans/example",
          generated_stages: ["01-plan"],
          created_at: "2026-05-05T00:00:00Z",
          schema_id: "https://uipath.local/uiplan/approval-package.v1",
          schema_version: "v1",
          generator_version: "uiplan-studio-generation-graph-phase-0",
          safety_policy: { direct_writes: false, external_mutation: false },
        },
        approval_state: {
          package_id: "pkg-apply-fails",
          current_stage: "01-plan",
          stage_statuses: {
            "01-plan": "ready_for_review",
            "02-scaffold": "not_started",
            "03-code": "not_started",
            "04-tests": "not_started",
            "05-validation": "not_started",
          },
          proposals: {
            "01-plan:proposal-a": {
              proposal_id: "01-plan:proposal-a",
              stage_id: "01-plan",
              review_status: "approved",
              apply_status: "not_started",
              source_graph_hash: "graph-hash",
              context_manifest_hash: "context-hash",
              proposal_hash: "hash-a",
              updated_at: "2026-05-05T00:00:00Z",
            },
          },
          applied_preview_ids: [],
          superseded_preview_ids: [],
          reviewer_notes: [],
          updated_at: "2026-05-05T00:00:00Z",
        },
        stages: [],
        proposals: [
          {
            proposal_id: "01-plan:proposal-a",
            stage_id: "01-plan",
            target_path: "docs/proposal-a.md",
            file_kind: "document",
            owning_node_ids: ["plan"],
            project_type_ids: ["docs"],
            proposed_content_hash: "hash-a",
            base_hash: null,
            diff_path: "stages/01-plan/diffs/proposal-a.diff",
            proposal_path: "stages/01-plan/proposals/proposal-a.md",
            citations: [],
            findings: [],
            apply_eligible: true,
          },
        ],
      });
    }
    if (url.includes("/proposals/01-plan%3Aproposal-a/preview")) {
      return mockJsonResponse({
        preview_id: "preview-a",
        proposal_id: "01-plan:proposal-a",
        target_path: "docs/proposal-a.md",
        diff: "--- docs/proposal-a.md\n+++ docs/proposal-a.md\n+# Proposal A\n",
      });
    }
    if (url.includes("/proposals/01-plan%3Aproposal-a/apply")) {
      return Promise.resolve({
        ok: false,
        status: 409,
        json: async () => ({ detail: "stale preview" }),
      } as Response);
    }
    return mockJsonResponse({ categories: [] });
  });

  render(<App />);
  await screen.findByText("UiPlan Studio");
  fireEvent.click(await screen.findByRole("button", { name: "Generate Plan Package" }));
  await screen.findByText("Approval Package");
  fireEvent.click(screen.getByRole("button", { name: "Preview proposal" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Apply proposal" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Apply proposal" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Proposal apply failed. Review the preview and retry. (Request failed: 409)",
  );
});
