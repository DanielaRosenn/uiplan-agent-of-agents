import React, { useMemo, useState } from "react";

import type { ApprovalPackageDetail, ApprovalStatus, StageId } from "../generationTypes";
import ProposalDrilldown from "./ProposalDrilldown";

interface ApprovalPackagePanelProps {
  packageDetail: ApprovalPackageDetail;
  selectedProposalId: string | null;
  proposalPreviewId: string | null;
  proposalPreviewDiff: string | null;
  onSelectProposal: (proposalId: string) => void;
  onApproveProposal: (proposalId: string) => void;
  onPreviewProposal: (proposalId: string) => void;
  onApplyProposal: (proposalId: string, previewId: string) => void;
}

const STAGES: Array<{ id: StageId; label: string }> = [
  { id: "01-plan", label: "Plan" },
  { id: "02-scaffold", label: "Scaffold" },
  { id: "03-code", label: "Code" },
  { id: "04-tests", label: "Tests" },
  { id: "05-validation", label: "Validation" },
];

function getProposalStatus(
  packageDetail: ApprovalPackageDetail,
  proposalId: string | null,
): ApprovalStatus | null {
  if (!proposalId) {
    return null;
  }
  const proposalState = packageDetail.approval_state.proposals[proposalId];
  if (typeof proposalState === "string") {
    return proposalState as ApprovalStatus;
  }
  if (
    typeof proposalState === "object" &&
    proposalState !== null &&
    "review_status" in proposalState &&
    typeof proposalState.review_status === "string"
  ) {
    return proposalState.review_status as ApprovalStatus;
  }
  if (
    typeof proposalState === "object" &&
    proposalState !== null &&
    "status" in proposalState &&
    typeof proposalState.status === "string"
  ) {
    return proposalState.status as ApprovalStatus;
  }
  return null;
}

export default function ApprovalPackagePanel({
  packageDetail,
  selectedProposalId,
  proposalPreviewId,
  proposalPreviewDiff,
  onSelectProposal,
  onApproveProposal,
  onPreviewProposal,
  onApplyProposal,
}: ApprovalPackagePanelProps) {
  const [activeStage, setActiveStage] = useState<StageId>("01-plan");
  const selectedProposal = useMemo(
    () => packageDetail.proposals.find((proposal) => proposal.proposal_id === selectedProposalId) ?? null,
    [packageDetail.proposals, selectedProposalId],
  );
  const activeProposals = packageDetail.proposals.filter((proposal) => proposal.stage_id === activeStage);
  const selectedProposalStatus = getProposalStatus(packageDetail, selectedProposalId);

  const stageStatus = packageDetail.approval_state.stage_statuses;
  const generated = new Set(packageDetail.manifest.generated_stages);

  return (
    <section aria-label="Approval Package">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Generation</p>
          <h2>Approval Package</h2>
        </div>
        <p className="muted">Package: {packageDetail.manifest.package_id}</p>
      </div>
      <div className="stage-tabs" role="tablist" aria-label="Approval stages">
        {STAGES.map((stage) => {
          if (!generated.has(stage.id) && stage.id !== "03-code" && stage.id !== "04-tests" && stage.id !== "05-validation") {
            return null;
          }
          const deferred = stage.id === "03-code" || stage.id === "04-tests" || stage.id === "05-validation";
          const tabLabel = deferred ? `${stage.label} deferred` : `${stage.label} ${stageStatus[stage.id]}`;
          return (
            <button
              key={stage.id}
              role="tab"
              type="button"
              aria-selected={activeStage === stage.id}
              onClick={() => setActiveStage(stage.id)}
              disabled={deferred}
            >
              {tabLabel}
            </button>
          );
        })}
      </div>
      <div className="package-proposals">
        <h3>Stage proposals</h3>
        {activeProposals.length === 0 ? (
          <p className="muted">No proposals for this stage.</p>
        ) : (
          <ul className="compact-list">
            {activeProposals.map((proposal) => (
              <li key={proposal.proposal_id}>
                <button type="button" onClick={() => onSelectProposal(proposal.proposal_id)}>
                  Proposal: {proposal.target_path}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <ProposalDrilldown
        proposal={selectedProposal}
        previewId={proposalPreviewId}
        previewDiff={proposalPreviewDiff}
        proposalStatus={selectedProposalStatus}
        onApproveProposal={onApproveProposal}
        onPreviewProposal={onPreviewProposal}
        onApplyProposal={onApplyProposal}
      />
    </section>
  );
}
