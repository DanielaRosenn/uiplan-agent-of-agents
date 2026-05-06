import React from "react";
import type { DocumentName } from "../types";

interface BundleNavigatorProps {
  selectedDocument: DocumentName;
  onSelectDocument: (documentName: DocumentName) => void;
}

const DOCUMENTS: DocumentName[] = ["spec.md", "plan.md", "tasks.md"];

export default function BundleNavigator({
  selectedDocument,
  onSelectDocument,
}: BundleNavigatorProps) {
  return (
    <section aria-label="Documents">
      <h2>Documents</h2>
      <ul>
        {DOCUMENTS.map((documentName) => (
          <li key={documentName}>
            <button
              type="button"
              onClick={() => onSelectDocument(documentName)}
              aria-pressed={selectedDocument === documentName}
            >
              {documentName}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
