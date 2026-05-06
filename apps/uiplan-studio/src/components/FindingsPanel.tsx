import React from "react";
import type { Finding } from "../types";

interface FindingsPanelProps {
  findings: Finding[];
  onSelectFinding?: (finding: Finding) => void;
}

export default function FindingsPanel({ findings, onSelectFinding }: FindingsPanelProps) {
  return (
    <section aria-label="Findings">
      <h2>Findings</h2>
      {findings.length === 0 ? (
        <p>No findings</p>
      ) : (
        <ul>
          {findings.map((finding, index) => (
            <li key={`${finding.rule ?? "finding"}-${index}`}>
              <button type="button" onClick={() => onSelectFinding?.(finding)}>
                [{finding.severity ?? "info"}] {finding.rule ?? "Uncategorized"} -{" "}
                {finding.document ?? "unknown"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
