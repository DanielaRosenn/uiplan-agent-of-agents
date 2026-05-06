import React from "react";

import type { DiagramNode } from "../types";

interface GraphExplorerPanelProps {
  nodes: DiagramNode[];
  selectedNodeId: string | null;
  onSelectNodeId: (nodeId: string) => void;
}

export default function GraphExplorerPanel({
  nodes,
  selectedNodeId,
  onSelectNodeId,
}: GraphExplorerPanelProps) {
  return (
    <section aria-label="Graph Explorer">
      <h2>Graph Explorer</h2>
      {nodes.length === 0 ? (
        <p className="muted">No graph nodes available.</p>
      ) : (
        <ul className="graph-explorer-list">
          {nodes.map((node) => (
            <li key={node.id} className="graph-explorer-item">
              <div>
                <strong>{node.title}</strong>
                <p className="muted">{node.id}</p>
              </div>
              <button
                type="button"
                aria-pressed={selectedNodeId === node.id}
                onClick={() => onSelectNodeId(node.id)}
              >
                Select
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
