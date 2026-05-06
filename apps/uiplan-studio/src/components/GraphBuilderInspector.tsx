import React from "react";

import type { DiagramNode } from "../types";
import CodeSnippetViewer from "./CodeSnippetViewer";

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
        <>
          <div className="inspector-section">
            <div className="node-header">
              <h3>{selectedNode.title}</h3>
              <span className="kind-badge">{selectedNode.kind}</span>
            </div>
            
            {summary !== "No summary available." && (
              <div className="concept-explanation">
                {summary}
              </div>
            )}
            
            {selectedNode.description && selectedNode.description.includes("```") && (
              <CodeSnippetViewer 
                code={extractCodeFromDescription(selectedNode.description)}
                language="typescript"
                lines={extractLinesFromDescription(selectedNode.description)}
              />
            )}
            
            <dl className="node-metadata">
              <div>
                <dt>ID</dt>
                <dd>{selectedNode.id}</dd>
              </div>
              <div>
                <dt>Layer</dt>
                <dd>{selectedNode.layer}</dd>
              </div>
            </dl>
          </div>
          
          <div className="inspector-section">
            <h3>Related Nodes</h3>
            <p className="muted">No related nodes detected.</p>
          </div>
        </>
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
      <section aria-label="Resolved context citations" className="inspector-section">
        <h3>Context Citations</h3>
        {resolvedCitations.length === 0 ? (
          <p className="muted">No citations resolved yet.</p>
        ) : (
          <ul className="citation-list">
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

function extractCodeFromDescription(description: string): string {
  const codeMatch = description.match(/```[\w]*\n([\s\S]*?)```/);
  return codeMatch ? codeMatch[1].trim() : "";
}

function extractLinesFromDescription(description: string): string | undefined {
  const linesMatch = description.match(/lines?\s+(\d+-\d+)/i);
  return linesMatch ? linesMatch[1] : undefined;
}
