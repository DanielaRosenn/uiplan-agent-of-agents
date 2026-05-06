import React from "react";

import type { DiagramNode } from "../types";

interface ResolvedContextCitation {
  source_type: string;
  source_id: string;
  snippet: string;
  strict: boolean;
}

interface GraphBuilderInspectorProps {
  selectedNode: DiagramNode | null;
  resolvedCitations: ResolvedContextCitation[];
  isResolvingContext: boolean;
  onResolveContext: () => void;
}

export default function GraphBuilderInspector({
  selectedNode,
  resolvedCitations,
  isResolvingContext,
  onResolveContext,
}: GraphBuilderInspectorProps) {
  const summary =
    selectedNode == null || selectedNode.description.trim().length === 0
      ? "No summary available."
      : selectedNode.description;

  return (
    <section aria-label="Builder Inspector">
      <h2>Builder Inspector</h2>
      {selectedNode == null ? (
        <p className="muted">Select a graph node to inspect its builder summary.</p>
      ) : (
        <dl className="graph-builder-summary">
          <div>
            <dt>Node</dt>
            <dd>{selectedNode.title}</dd>
          </div>
          <div>
            <dt>Id</dt>
            <dd>{selectedNode.id}</dd>
          </div>
          <div>
            <dt>Kind</dt>
            <dd>{selectedNode.kind}</dd>
          </div>
          <div>
            <dt>Description</dt>
            <dd>{summary}</dd>
          </div>
        </dl>
      )}
      <div className="studio-actions">
        <button
          type="button"
          onClick={onResolveContext}
          disabled={selectedNode == null || isResolvingContext}
        >
          {isResolvingContext ? "Resolving context..." : "Resolve context"}
        </button>
      </div>
      <section aria-label="Resolved context citations">
        <h3>Resolved citations</h3>
        {resolvedCitations.length === 0 ? (
          <p className="muted">No citations resolved yet.</p>
        ) : (
          <ul>
            {resolvedCitations.map((citation) => (
              <li key={`${citation.source_type}:${citation.source_id}:${citation.snippet}`}>
                <strong>{citation.source_id}</strong>
                <p>{citation.snippet}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}
