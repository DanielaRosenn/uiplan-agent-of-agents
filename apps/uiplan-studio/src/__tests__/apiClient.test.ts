import { beforeEach, describe, expect, test, vi } from "vitest";

import { createApiClient } from "../api/client";

beforeEach(() => {
  vi.restoreAllMocks();
});

function mockJsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    json: async () => body,
  } as Response);
}

describe("api client", () => {
  test("loads the starter ProjectGraph template endpoint", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse({
        metadata: { id: "visual-template" },
        graph: { projectType: "solution", nodes: [], edges: [], clusters: [], errors: [] },
      }),
    );

    const client = createApiClient({ baseUrl: "http://api.test/" });
    const payload = await client.loadStarterProjectGraphTemplate();

    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/project-graph/templates/starter",
      expect.objectContaining({ headers: { "Content-Type": "application/json" } }),
    );
    expect(payload.metadata.id).toBe("visual-template");
  });

  test("loads the generation command registry endpoint", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse({
        schema_id: "https://uipath.local/uiplan/command-registry.v1",
        schema_version: "v1",
        commands: [
          {
            command_id: "plan.markdown.readiness",
            purpose: "Check generated Plan markdown.",
            owning_stage: "01-plan",
            executable: "python",
            fixed_args: [],
            working_directory_rule: "repo_root",
            allowed_path_inputs: ["docs/**/*.md"],
            mutation_classification: "read-only",
            required_confirmation: false,
            credential_requirements: [],
            output_summary_policy: "Persist pass/fail count.",
          },
        ],
      }),
    );

    const client = createApiClient({ baseUrl: "http://api.test/" });
    const payload = await client.loadCommandRegistry();

    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/generation/command-registry",
      expect.objectContaining({ headers: { "Content-Type": "application/json" } }),
    );
    expect(payload.commands[0].command_id).toBe("plan.markdown.readiness");
  });
});
