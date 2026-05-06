import React from "react";
import type { LifecycleReadinessResponse } from "../types";

interface LifecyclePanelProps {
  readiness: LifecycleReadinessResponse | null;
}

export default function LifecyclePanel({ readiness }: LifecyclePanelProps) {
  return (
    <section aria-label="Lifecycle">
      <h2>Lifecycle</h2>
      {readiness == null ? (
        <p>Readiness unavailable</p>
      ) : (
        <div>
          <p>Status: {readiness.status}</p>
          <p>Acceptance ready: {readiness.acceptance_ready ? "yes" : "no"}</p>
          <p>Error findings: {readiness.error_count}</p>
        </div>
      )}
    </section>
  );
}
