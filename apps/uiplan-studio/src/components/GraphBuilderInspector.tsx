import React from "react";

import type { DiagramNode } from "../types";

interface GraphBuilderInspectorProps {
  selectedNode: DiagramNode | null;
}

export default function GraphBuilderInspector({ selectedNode }: GraphBuilderInspectorProps) {
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
            <dd>{selectedNode.description}</dd>
          </div>
        </dl>
      )}
    </section>
  );
}
