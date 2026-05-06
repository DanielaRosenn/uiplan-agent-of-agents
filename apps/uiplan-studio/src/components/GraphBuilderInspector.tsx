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
      {selectedNode == null ? (
        <div className="empty-state">
          <div className="empty-state-icon">🔍</div>
          <h3 className="empty-state-title">No Node Selected</h3>
          <p className="empty-state-description">
            Select a node from the graph explorer to view its details, metadata, and context citations.
          </p>
        </div>
      ) : (
        <>
          <div className="inspector-section">
            <div className="node-header">
              <h3>{selectedNode.title}</h3>
              <span className="kind-badge">{selectedNode.kind}</span>
            </div>
            
            {selectedNode.concept && (
              <div className="concept-explanation">
                <strong>Concept:</strong> {selectedNode.concept}
              </div>
            )}
            
            {summary !== "No summary available." && (
              <div className="concept-explanation">
                {summary}
              </div>
            )}
            
            {selectedNode.code && (
              <CodeSnippetViewer 
                code={selectedNode.code.snippet}
                language={selectedNode.code.language}
                lines={selectedNode.code.lines}
              />
            )}
            
            {!selectedNode.code && selectedNode.description && selectedNode.description.includes("```") && (
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
              {selectedNode.code && (
                <div>
                  <dt>File</dt>
                  <dd>{selectedNode.code.path}</dd>
                </div>
              )}
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
        {isResolvingContext ? (
          <div style={{ padding: "20px", textAlign: "center" }}>
            <div className="loading-spinner" style={{ margin: "0 auto 12px" }}></div>
            <p className="muted">Resolving context citations...</p>
          </div>
        ) : resolvedCitations.length === 0 ? (
          <div style={{ padding: "20px", textAlign: "center" }}>
            <p className="muted">No citations resolved yet. Click "Resolve context" to find relevant citations.</p>
          </div>
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
