import { expect, test } from "@playwright/test";

test("loads studio and searches library context", async ({ page }) => {
  await page.route("**/bundle/load**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: {
          "spec.md": "# Spec\n",
          "plan.md": "# Plan\n",
          "tasks.md": "# Tasks\n",
        },
      }),
    });
  });

  await page.route("**/agent/library-context", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        query: "deploy",
        items: [
          {
            book_id: "uipath-cli",
            chapter_id: "03-agent",
            section_id: "deploy",
            score: 9,
            snippet: "Deploy package guidance",
            full_text: "Use uipath deploy",
          },
        ],
      }),
    });
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "UiPlan Studio" })).toBeVisible();

  await page.getByLabel("Library query").fill("deploy");
  await page.getByRole("button", { name: "Search library" }).click();

  await expect(page.getByText("uipath-cli/03-agent/deploy").first()).toBeVisible();
});

test("runs plan package review flow with deferred stages", async ({ page }) => {
  await page.route("**/bundle/load**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        slug: "example",
        status: "draft",
        root: ".cursor/plans/example",
        documents: {
          "spec.md": "# Spec\n",
          "plan.md": "# Plan\n",
          "tasks.md": "# Tasks\n",
        },
      }),
    });
  });

  await page.route("**/generation/packages", async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        package_id: "pkg-e2e-1",
        graph_id: "graph-e2e-1",
        bundle_root: ".cursor/plans/example",
        generated_stages: ["01-plan"],
        created_at: "2026-05-05T00:00:00Z",
        schema_id: "https://uipath.local/uiplan/approval-package.v1",
        schema_version: "v1",
        generator_version: "uiplan-studio-generation-graph-phase-0",
        safety_policy: { direct_writes: false, external_mutation: false },
      }),
    });
  });

  await page.route("**/generation/packages/pkg-e2e-1**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        manifest: {
          package_id: "pkg-e2e-1",
          graph_id: "graph-e2e-1",
          bundle_root: ".cursor/plans/example",
          generated_stages: ["01-plan"],
          created_at: "2026-05-05T00:00:00Z",
          schema_id: "https://uipath.local/uiplan/approval-package.v1",
          schema_version: "v1",
          generator_version: "uiplan-studio-generation-graph-phase-0",
          safety_policy: { direct_writes: false, external_mutation: false },
        },
        approval_state: {
          package_id: "pkg-e2e-1",
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
        stages: [
          {
            stage_id: "01-plan",
            status: "ready_for_review",
            input_graph_hash: "graph-hash",
            input_context_hash: "context-hash",
            generated_files: ["docs/uiplan-generation-plan.md"],
            required_approvals: ["proposal"],
            blocking_findings: [
              {
                severity: "warning",
                message: "Review citations before apply.",
                blocks_apply: false,
              },
            ],
            validation_commands: ["plan.markdown.readiness"],
            apply_eligible: true,
          },
        ],
        proposals: [
          {
            proposal_id: "01-plan:uiplan-generation-plan",
            stage_id: "01-plan",
            target_path: "docs/uiplan-generation-plan.md",
            file_kind: "document",
            owning_node_ids: ["plan-node"],
            project_type_ids: ["docs"],
            proposed_content_hash: "proposal-hash",
            base_hash: null,
            diff_path: "stages/01-plan/diffs/uiplan-generation-plan.md.diff",
            proposal_path: "stages/01-plan/proposals/uiplan-generation-plan.md",
            citations: ["docs/PDD.md"],
            findings: [
              {
                severity: "warning",
                message: "Review before apply.",
                blocks_apply: false,
              },
            ],
            apply_eligible: true,
          },
        ],
      }),
    });
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "UiPlan Studio" })).toBeVisible();
  await page.getByRole("button", { name: "Generate Plan Package" }).click();

  await expect(page.getByText("Approval Package")).toBeVisible();
  await expect(page.getByRole("tab", { name: "Code deferred" })).toBeDisabled();
  await expect(page.getByRole("tab", { name: "Tests deferred" })).toBeDisabled();
  await expect(page.getByRole("tab", { name: "Validation deferred" })).toBeDisabled();
  await expect(page.getByRole("button", { name: /Deploy/i })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Publish/i })).toHaveCount(0);

  await page.getByRole("button", { name: "Proposal: docs/uiplan-generation-plan.md" }).click();
  const approvalPanel = page.getByLabel("Approval Package");
  await expect(approvalPanel.getByRole("heading", { name: "Citations" })).toBeVisible();
  await expect(approvalPanel.getByRole("heading", { name: "Findings" })).toBeVisible();
  await expect(approvalPanel.getByText("docs/PDD.md")).toBeVisible();
});
