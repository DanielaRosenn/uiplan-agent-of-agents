import { describe, expect, test } from "vitest";

import type { ApprovalPackageDetail } from "../generationTypes";
import type { ContextSourceCategory } from "../types";
import {
  adaptApprovalPackage,
  adaptContextSources,
  adaptMermaidFlowcharts,
  adaptUiPlanDocuments,
  composeProjectGraphResults,
  extractMarkdownTodos,
} from "../projectGraph/adapters";

describe("projectGraph adapters", () => {
  test("extracts markdown checkbox todos with done and pending state", () => {
    expect(
      extractMarkdownTodos(["# Tasks", "- [ ] Build adapters", "- [x] Define contract"].join("\n")),
    ).toEqual([
      { label: "Build adapters", done: false, line: 2 },
      { label: "Define contract", done: true, line: 3 },
    ]);
  });

  test("adapts UiPlan documents into document, section, and task graph nodes", () => {
    const result = adaptUiPlanDocuments({
      projectType: "docs",
      source: {
        bundleRoot: ".cursor/plans/example",
        documents: {
          "spec.md": "# Spec\n\n## Scope\n- [ ] Confirm requirements",
          "tasks.md": "# Tasks\n\n- [x] ProjectGraph contract\n- [ ] Mermaid adapters",
        },
      },
    });

    expect(result.graph.nodes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "doc:spec-md",
          kind: "generated_artifact",
          layer: "document",
          metadata: expect.objectContaining({ nodeType: "document" }),
        }),
        expect.objectContaining({
          id: "doc:spec-md:section:2",
          layer: "section",
          label: "Scope",
        }),
        expect.objectContaining({
          id: "doc:tasks-md:task:2",
          layer: "task",
          label: "Mermaid adapters",
          metadata: expect.objectContaining({ done: false, status: "pending" }),
        }),
      ]),
    );
    expect(result.graph.edges).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          source: "doc:tasks-md",
          target: "doc:tasks-md:task:1",
          kind: "documents",
        }),
      ]),
    );
  });

  test("parses simple Mermaid flowchart nodes and transition edges", () => {
    const result = adaptMermaidFlowcharts({
      projectType: "solution",
      source: [
        "flowchart LR",
        "  A[Collect Invoice] --> B{Valid?}",
        "  B -- yes --> C[Post Queue Item]",
        "  classDef ignored fill:#fff",
      ].join("\n"),
    });

    expect(result.graph.nodes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "mermaid:1:a",
          label: "Collect Invoice",
          kind: "process_step",
          layer: "workflow",
        }),
        expect.objectContaining({
          id: "mermaid:1:b",
          label: "Valid?",
          metadata: expect.objectContaining({ mermaidShape: "{" }),
        }),
      ]),
    );
    expect(result.graph.edges).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          source: "mermaid:1:a",
          target: "mermaid:1:b",
          kind: "drives",
          metadata: expect.objectContaining({ nodeType: "transition" }),
        }),
        expect.objectContaining({
          source: "mermaid:1:b",
          target: "mermaid:1:c",
          label: "yes",
        }),
      ]),
    );
    expect(result.issues).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "mermaid:1:unsupported:4",
          severity: "warning",
        }),
      ]),
    );
  });

  test("parses compact and pipe-labeled Mermaid edges with labels", () => {
    const result = adaptMermaidFlowcharts({
      projectType: "solution",
      source: [
        "flowchart LR",
        "A-->B",
        "B --> C",
        "C-->|yes|D",
        "D -->|review| E",
      ].join("\n"),
    });

    expect(result.graph.edges).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ source: "mermaid:1:a", target: "mermaid:1:b" }),
        expect.objectContaining({ source: "mermaid:1:b", target: "mermaid:1:c" }),
        expect.objectContaining({
          source: "mermaid:1:c",
          target: "mermaid:1:d",
          label: "yes",
        }),
        expect.objectContaining({
          source: "mermaid:1:d",
          target: "mermaid:1:e",
          label: "review",
        }),
      ]),
    );
  });

  test("keeps Mermaid node IDs unique across blocks with reused local IDs", () => {
    const result = adaptMermaidFlowcharts({
      projectType: "solution",
      source: {
        blocks: ["flowchart LR\nA[Start]-->B[Done]", "graph TD\nA[Second Start]-->B[Second Done]"],
      },
    });

    expect(result.graph.nodes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "mermaid:1:a",
          label: "Start",
          metadata: expect.objectContaining({ mermaidLocalId: "A", blockIndex: 1 }),
        }),
        expect.objectContaining({
          id: "mermaid:2:a",
          label: "Second Start",
          metadata: expect.objectContaining({ mermaidLocalId: "A", blockIndex: 2 }),
        }),
      ]),
    );
    expect(new Set(result.graph.nodes.map((node) => node.id)).size).toBe(result.graph.nodes.length);
  });

  test("adapts context source categories into context, tool, skill, and library nodes", () => {
    const categories: ContextSourceCategory[] = [
      {
        id: "docs",
        title: "Docs",
        description: "Repo docs",
        sources: [
          {
            id: "docs/spec",
            title: "Spec",
            kind: "document",
            category: "docs",
            description: "Spec doc",
            source: "spec.md",
            available: true,
          },
        ],
      },
      {
        id: "library",
        title: "Library",
        description: "Library books",
        sources: [
          {
            id: "book/uipath",
            title: "UiPath Book",
            kind: "library",
            category: "library-books",
            description: "Book",
            source: "library://uipath",
            available: true,
          },
          {
            id: "skill/uipath-rpa",
            title: "UiPath RPA Skill",
            kind: "skill",
            category: "skills",
            description: "Skill",
            source: "skill://uipath-rpa",
            available: true,
          },
          {
            id: "tool/uipath_library_search",
            title: "Library Search",
            kind: "library",
            category: "mcp-tools",
            description: "Tool",
            source: "tool://uipath_library_search",
            available: false,
          },
        ],
      },
    ];

    const result = adaptContextSources({ projectType: "docs", source: { categories } });

    expect(result.graph.nodes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ id: "context:docs-spec", kind: "docs_context", layer: "context" }),
        expect.objectContaining({ id: "context:book-uipath", kind: "docs_context", layer: "library" }),
        expect.objectContaining({ id: "context:skill-uipath-rpa", kind: "skill", layer: "skill" }),
        expect.objectContaining({
          id: "context:tool-uipath-library-search",
          kind: "tool",
          layer: "tool",
        }),
      ]),
    );
    expect(result.issues).toEqual([
      expect.objectContaining({
        id: "context:tool-uipath-library-search:unavailable",
        severity: "warning",
      }),
    ]);
  });

  test("adapts approval packages into approval stage and proposal nodes", () => {
    const detail: ApprovalPackageDetail = {
      manifest: {
        schema_id: "schema",
        schema_version: "v1",
        package_id: "pkg-1",
        graph_id: "graph-1",
        bundle_root: ".cursor/plans/example",
        generated_stages: ["01-plan"],
        generator_version: "test",
        created_at: "2026-05-05T00:00:00Z",
        safety_policy: {},
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
      stages: [
        {
          stage_id: "01-plan",
          status: "ready_for_review",
          input_graph_hash: "hash",
          input_context_hash: "context",
          generated_files: ["docs/plan.md"],
          required_approvals: [],
          blocking_findings: [],
          validation_commands: [],
          apply_eligible: true,
        },
      ],
      proposals: [
        {
          proposal_id: "01-plan:uiplan-generation-plan",
          stage_id: "01-plan",
          target_path: "docs/plan.md",
          file_kind: "markdown",
          owning_node_ids: ["doc:plan-md"],
          project_type_ids: ["docs"],
          proposed_content_hash: "hash",
          base_hash: null,
          diff_path: "diffs/plan.diff",
          proposal_path: "proposals/plan.md",
          citations: ["spec.md"],
          findings: [],
          apply_eligible: true,
        },
      ],
    };

    const result = adaptApprovalPackage({ projectType: "docs", source: detail });

    expect(result.graph.nodes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ id: "approval-stage:01-plan", kind: "review_gate" }),
        expect.objectContaining({
          id: "proposal:01-plan-uiplan-generation-plan",
          kind: "generated_artifact",
          layer: "proposal",
        }),
      ]),
    );
    expect(result.graph.edges).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          source: "approval-stage:01-plan",
          target: "proposal:01-plan-uiplan-generation-plan",
          kind: "generates",
        }),
      ]),
    );
  });

  test("synthesizes missing approval stage nodes for proposal-only packages", () => {
    const result = adaptApprovalPackage({
      projectType: "docs",
      source: {
        stages: [],
        proposals: [
          {
            proposal_id: "proposal-1",
            stage_id: "01-plan",
            target_path: "docs/plan.md",
            file_kind: "markdown",
            owning_node_ids: [],
            project_type_ids: ["docs"],
            proposed_content_hash: "hash",
            base_hash: null,
            diff_path: "diffs/plan.diff",
            proposal_path: "proposals/plan.md",
            citations: [],
            findings: [],
            apply_eligible: true,
          },
        ],
      },
    });

    expect(result.graph.nodes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "approval-stage:01-plan",
          metadata: expect.objectContaining({ synthesized: true }),
        }),
        expect.objectContaining({ id: "proposal:proposal-1" }),
      ]),
    );
    expect(result.graph.errors).not.toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "edge:approval-stage:01-plan:generates:proposal:proposal-1:missing-source",
        }),
      ]),
    );
  });

  test("emits diagnostics for malformed approval package proposals", () => {
    const result = adaptApprovalPackage({
      projectType: "docs",
      source: {
        stages: [],
        proposals: [null, { proposal_id: "missing-shape" }],
      },
    });

    expect(result.graph.nodes).toEqual([]);
    expect(result.issues).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "approval-package:malformed-proposal:0",
          severity: "warning",
        }),
        expect.objectContaining({
          id: "approval-package:malformed-proposal:1",
          severity: "warning",
        }),
      ]),
    );
  });

  test("composes adapter results with normalization diagnostics", () => {
    const documents = adaptUiPlanDocuments({
      projectType: "docs",
      source: { documents: { "tasks.md": "- [ ] Build adapters" } },
    });
    const approvalPackage = adaptApprovalPackage({
      projectType: "docs",
      source: {
        stages: [],
        proposals: [
          {
            proposal_id: "proposal-1",
            stage_id: "01-plan",
            target_path: "docs/plan.md",
            file_kind: "markdown",
            owning_node_ids: ["missing-owner"],
            project_type_ids: ["docs"],
            proposed_content_hash: "hash",
            base_hash: null,
            diff_path: "diff",
            proposal_path: "proposal",
            citations: [],
            findings: [],
            apply_eligible: true,
          },
        ],
      },
    });

    const result = composeProjectGraphResults("docs", [documents, approvalPackage]);

    expect(result.graph.nodes.map((node) => node.id)).toContain("doc:tasks-md:task:1");
    expect(result.graph.errors).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "edge:missing-owner:generates:proposal:proposal-1:missing-source",
          severity: "warning",
        }),
      ]),
    );
  });
});
