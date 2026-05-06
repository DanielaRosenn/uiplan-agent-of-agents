import { describe, expect, test } from "vitest";

import type {
  ApprovalPackageDetail,
  ApprovalStatus,
  ProjectType,
  StageId,
} from "../generationTypes";
import { toGenerationGraphPayload } from "../generationGraphAdapter";
import { projectGraphToDiagramData } from "../projectGraph/diagramAdapter";
import { createStarterProjectGraphTemplate } from "../projectGraph/templates";

describe("generationTypes", () => {
  test("allows phase-0 stage ids and statuses", () => {
    const stage: StageId = "01-plan";
    const status: ApprovalStatus = "ready_for_review";
    const projectType: ProjectType = "coded-agent";

    expect(stage).toBe("01-plan");
    expect(status).toBe("ready_for_review");
    expect(projectType).toBe("coded-agent");
  });

  test("supports approval package detail fixtures", () => {
    const detail: ApprovalPackageDetail = {
      manifest: {
        schema_id: "https://uipath.local/uiplan/approval-package.v1",
        schema_version: "v1",
        package_id: "pkg-1",
        graph_id: "graph-1",
        bundle_root: ".cursor/plans/example",
        generated_stages: ["01-plan"],
        generator_version: "uiplan-studio-generation-graph-phase-0",
        created_at: "2026-05-05T00:00:00Z",
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
        reviewer_notes: [],
        applied_preview_ids: [],
        superseded_preview_ids: [],
        updated_at: "2026-05-05T00:00:00Z",
      },
      stages: [],
      proposals: [],
    };

    expect(detail.manifest.package_id).toBe("pkg-1");
    expect(detail.approval_state.current_stage).toBe("01-plan");
  });

  test("maps default canvas graph to generation-contract payload", () => {
    const payload = toGenerationGraphPayload(".cursor/plans/example", {
      nodes: [
        {
          id: "plan",
          title: "Workflow Plan",
          kind: "workflow",
          description: "Build steps.",
          x: 100,
          y: 120,
        },
        {
          id: "review",
          title: "Review Gates",
          kind: "review",
          description: "Approval checks.",
          x: 140,
          y: 200,
        },
      ],
      edges: [{ id: "plan-review", from: "plan", to: "review", label: "validated by" }],
    });

    expect(payload.graph_id).toMatch(/^graph-[a-f0-9]{8}$/);
    expect(payload.nodes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "plan",
          role: "process_step",
          output_type: "project_scaffold",
          project_types: ["docs"],
        }),
        expect.objectContaining({
          id: "review",
          role: "review_gate",
          output_type: "approval_gate",
        }),
      ]),
    );
    expect(payload.edges).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "plan-review",
          edge_type: "validates",
        }),
      ]),
    );
  });

  test("preserves typed ProjectGraph edge semantics over display labels", () => {
    const diagram = projectGraphToDiagramData(createStarterProjectGraphTemplate());
    const payload = toGenerationGraphPayload(".cursor/plans/example", diagram);

    expect(payload.edges).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "if_ready:validates:success_package",
          label: "ready",
          edge_type: "validates",
        }),
        expect.objectContaining({
          id: "if_ready:blocks:needs_context",
          label: "needs context",
          edge_type: "blocks",
        }),
      ]),
    );
  });

  test("emits deterministic context attachments for strict citation nodes", () => {
    const payload = toGenerationGraphPayload(".cursor/plans/example", {
      nodes: [
        {
          id: "library",
          title: "Library Context",
          kind: "library",
          description: "Grounding section.",
          x: 100,
          y: 120,
          source: "uipath-docs/orchestrator/assets",
          context_policy: "strict",
          strict_citation: "[uipath-docs/orchestrator/assets]",
        },
      ],
      edges: [],
    });

    expect(payload.context_attachments).toEqual([
      expect.objectContaining({
        source_kind: "library_book",
        source_id: "uipath-docs/orchestrator/assets",
        citation: "[uipath-docs/orchestrator/assets]",
        policy: "strict",
      }),
    ]);
    expect(payload.context_attachments[0]).not.toHaveProperty("id");
    expect(payload.context_attachments[0]).not.toHaveProperty("node_id");
    expect(payload.nodes[0].context_attachment_ids).toEqual([
      "uipath-docs/orchestrator/assets",
      "[uipath-docs/orchestrator/assets]",
    ]);
  });
});
