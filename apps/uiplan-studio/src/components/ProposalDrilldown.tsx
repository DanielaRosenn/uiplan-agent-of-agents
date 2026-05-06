import React from "react";

import type { ApprovalStatus, FileProposal } from "../generationTypes";

interface ProposalDrilldownProps {
  proposal: FileProposal | null;
  previewId: string | null;
  previewDiff: string | null;
  proposalStatus: ApprovalStatus | null;
  onApproveProposal: (proposalId: string) => void;
  onPreviewProposal: (proposalId: string) => void;
  onApplyProposal: (proposalId: string, previewId: string) => void;
}

export default function ProposalDrilldown({
  proposal,
  previewId,
  previewDiff,
  proposalStatus,
  onApproveProposal,
  onPreviewProposal,
  onApplyProposal,
}: ProposalDrilldownProps) {
  if (!proposal) {
    return <p className="muted">Select a proposal to review metadata and apply controls.</p>;
  }

  const diffBody = previewDiff ?? proposal.diff_body ?? proposal.diff_content ?? proposal.diff ?? null;
  const canApplyProposal = Boolean(
    previewId && proposal.apply_eligible && proposalStatus === "approved",
  );

  return (
    <div className="proposal-drilldown">
      <h3>Proposal target</h3>
      <p>{proposal.target_path}</p>
      <p className="muted">Proposal id: {proposal.proposal_id}</p>
      <p>File kind: {proposal.file_kind}</p>
      <p>Proposed hash: {proposal.proposed_content_hash}</p>
      <p>Base hash: {proposal.base_hash ?? "none"}</p>
      <p>Owning nodes: {proposal.owning_node_ids.join(", ") || "none"}</p>
      <p>Project types: {proposal.project_type_ids.join(", ") || "none"}</p>
      <p>Review status: {proposalStatus ?? "not_started"}</p>
      <p>Apply eligible: {proposal.apply_eligible ? "yes" : "no"}</p>
      <div className="proposal-section">
        <h4>Diff</h4>
        {diffBody ? (
          <pre aria-label="Proposal diff">{diffBody}</pre>
        ) : (
          <>
            <p>Diff path: {proposal.diff_path}</p>
            <p>Proposal path: {proposal.proposal_path}</p>
          </>
        )}
      </div>
      <div className="proposal-section">
        <h4>Citations</h4>
        {proposal.citations.length === 0 ? (
          <p className="muted">No citations available.</p>
        ) : (
          <ul>
            {proposal.citations.map((citation) => (
              <li key={citation}>{citation}</li>
            ))}
          </ul>
        )}
      </div>
      <div className="proposal-section">
        <h4>Findings</h4>
        {proposal.findings.length === 0 ? (
          <p className="muted">No findings.</p>
        ) : (
          <ul>
            {proposal.findings.map((finding, idx) => (
              <li key={`${proposal.proposal_id}-${idx}`}>
                [{finding.severity}] {finding.message}
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="studio-actions">
        <button
          type="button"
          onClick={() => onApproveProposal(proposal.proposal_id)}
          disabled={!proposal.apply_eligible}
        >
          Approve proposal
        </button>
        <button type="button" onClick={() => onPreviewProposal(proposal.proposal_id)}>
          Preview proposal
        </button>
        <button
          type="button"
          onClick={() => previewId && onApplyProposal(proposal.proposal_id, previewId)}
          disabled={!canApplyProposal}
        >
          Apply proposal
        </button>
      </div>
    </div>
  );
}
