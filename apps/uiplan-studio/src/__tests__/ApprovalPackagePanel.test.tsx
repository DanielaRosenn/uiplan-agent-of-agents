import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import ApprovalPackagePanel from "../components/ApprovalPackagePanel";
import type { ApprovalPackageDetail } from "../generationTypes";

const packageDetail: ApprovalPackageDetail = {
  manifest: {
    package_id: "pkg-1",
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
    package_id: "pkg-1",
    current_stage: "01-plan",
    stage_statuses: {
      "01-plan": "ready_for_review",
      "02-scaffold": "ready_for_review",
      "03-code": "not_started",
      "04-tests": "not_started",
      "05-validation": "not_started",
    },
    proposals: {
      "01-plan:uiplan-generation-plan": {
        proposal_id: "01-plan:uiplan-generation-plan",
        stage_id: "01-plan",
        review_status: "ready_for_review",
        apply_status: "not_started",
        source_graph_hash: "graph-hash",
        context_manifest_hash: "context-hash",
        proposal_hash: "proposal-hash",
        updated_at: "2026-05-05T00:00:00Z",
      },
    },
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
      blocking_findings: [],
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
      owning_node_ids: ["intake"],
      project_type_ids: ["docs"],
      proposed_content_hash: "proposal-hash",
      base_hash: null,
      diff_path: "stages/01-plan/diffs/uiplan-generation-plan.md.diff",
      proposal_path: "stages/01-plan/proposals/uiplan-generation-plan.md",
      diff_body: "--- docs/uiplan-generation-plan.md\n+++ docs/uiplan-generation-plan.md\n+# Plan\n",
      citations: ["docs/PDD.md"],
      findings: [],
      apply_eligible: true,
    },
  ],
};

test("renders package stages, proposal drilldown, citations, and disabled future stages", () => {
  const onApproveProposal = vi.fn();
  const onPreviewProposal = vi.fn();
  const onApplyProposal = vi.fn();

  const { rerender } = render(
    <ApprovalPackagePanel
      packageDetail={packageDetail}
      selectedProposalId="01-plan:uiplan-generation-plan"
      onSelectProposal={() => undefined}
      onApproveProposal={onApproveProposal}
      onPreviewProposal={onPreviewProposal}
      onApplyProposal={onApplyProposal}
      proposalPreviewId={null}
      proposalPreviewDiff={null}
    />,
  );

  expect(screen.getByText("Approval Package")).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Plan ready_for_review" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Scaffold ready_for_review" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Code deferred" })).toBeDisabled();
  expect(screen.getByText("docs/uiplan-generation-plan.md")).toBeInTheDocument();
  expect(screen.getByText("docs/PDD.md")).toBeInTheDocument();
  expect(screen.getByLabelText("Proposal diff")).toHaveTextContent("+# Plan");

  fireEvent.click(screen.getByRole("button", { name: "Approve proposal" }));
  expect(onApproveProposal).toHaveBeenCalledWith("01-plan:uiplan-generation-plan");
  const applyProposalButton = screen.getByRole("button", { name: "Apply proposal" });
  expect(applyProposalButton).toBeDisabled();

  const approvedPackageDetail: ApprovalPackageDetail = {
    ...packageDetail,
    approval_state: {
      ...packageDetail.approval_state,
      proposals: {
        "01-plan:uiplan-generation-plan": {
          proposal_id: "01-plan:uiplan-generation-plan",
          stage_id: "01-plan",
          review_status: "approved",
          apply_status: "not_started",
          source_graph_hash: "graph-hash",
          context_manifest_hash: "context-hash",
          proposal_hash: "proposal-hash",
          preview_id: "preview-1",
          updated_at: "2026-05-05T00:00:00Z",
        },
      },
    },
  };

  rerender(
    <ApprovalPackagePanel
      packageDetail={approvedPackageDetail}
      selectedProposalId="01-plan:uiplan-generation-plan"
      onSelectProposal={() => undefined}
      onApproveProposal={onApproveProposal}
      onPreviewProposal={onPreviewProposal}
      onApplyProposal={onApplyProposal}
      proposalPreviewId="preview-1"
      proposalPreviewDiff="--- docs/uiplan-generation-plan.md\n+++ docs/uiplan-generation-plan.md\n+# Previewed\n"
    />,
  );
  expect(screen.getByLabelText("Proposal diff")).toHaveTextContent("+# Previewed");
  const enabledApplyButton = screen.getByRole("button", { name: "Apply proposal" });
  expect(enabledApplyButton).toBeEnabled();
  fireEvent.click(enabledApplyButton);
  expect(onApplyProposal).toHaveBeenCalledWith("01-plan:uiplan-generation-plan", "preview-1");
});
