import React from "react";

import type { ApprovalPackageDetail } from "../generationTypes";

interface StageControlsProps {
  packageDetail: ApprovalPackageDetail | null;
  onGeneratePlan: () => void;
  onGenerateScaffold: () => void;
}

export default function StageControls({
  packageDetail,
  onGeneratePlan,
  onGenerateScaffold,
}: StageControlsProps) {
  const stageStatuses = packageDetail?.approval_state.stage_statuses;
  const hasPlanInCurrentPackage = packageDetail?.manifest.generated_stages.includes("01-plan") === true;
  const hasApprovedPlan = stageStatuses?.["01-plan"] === "approved";
  const scaffoldHint =
    hasApprovedPlan || !hasPlanInCurrentPackage
      ? "Scaffold generates with backend-compatible stages."
      : "Plan exists but is not approved; scaffold will include plan + scaffold stages.";

  return (
    <section aria-label="Stage Controls" className="studio-actions">
      <button type="button" onClick={onGeneratePlan}>
        Generate Plan Package
      </button>
      <button type="button" onClick={onGenerateScaffold}>
        Generate Scaffold Package
      </button>
      <button type="button" disabled>
        Code deferred
      </button>
      <button type="button" disabled>
        Tests deferred
      </button>
      <button type="button" disabled>
        Validation deferred
      </button>
      <p className="muted">Deploy and publish are out of scope for generation packages.</p>
      <p className="muted">{scaffoldHint}</p>
    </section>
  );
}
