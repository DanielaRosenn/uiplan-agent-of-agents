import React from "react";

import type { DiagramNode, Finding, LibraryContextItem } from "../types";

interface ContextInspectorProps {
  selectedNode: DiagramNode | null;
  libraryContext: LibraryContextItem[];
  selectedFinding: Finding | null;
  onUpdateNode: (nodeId: string, updates: Partial<DiagramNode>) => void;
}

export default function ContextInspector({
  selectedNode,
  libraryContext,
  selectedFinding,
  onUpdateNode,
}: ContextInspectorProps) {
  const handleRequiredTextChange = (
    field: "title" | "description",
    value: string,
  ) => {
    if (!selectedNode) {
      return;
    }
    const trimmedValue = value.trim();
    if (!trimmedValue) {
      return;
    }
    onUpdateNode(selectedNode.id, { [field]: trimmedValue });
  };

  return (
    <section aria-label="Context Inspector">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Context</p>
          <h2>Selected builder context</h2>
        </div>
      </div>
      {selectedNode ? (
        <div className="context-block inspector-form">
          <p className="context-label">{selectedNode.kind}</p>
          {selectedNode.source ? <p className="muted">Source: {selectedNode.source}</p> : null}
          <div className="drilldown-card" aria-label="Selected node drilldown">
            <div>
              <span className="drilldown-label">Layer</span>
              <strong>{selectedNode.layer ?? "unassigned"}</strong>
            </div>
            <div>
              <span className="drilldown-label">Visual role</span>
              <strong>{selectedNode.visual_role ?? "custom"}</strong>
            </div>
            <div>
              <span className="drilldown-label">Status</span>
              <strong>{selectedNode.status ?? "draft"}</strong>
            </div>
          </div>
          {selectedNode.metadata?.projectGraphNodeId ? (
            <p className="muted">
              ProjectGraph node: {String(selectedNode.metadata.projectGraphNodeId)}
            </p>
          ) : null}
          <label>
            Node title
            <input
              value={selectedNode.title}
              onChange={(event) => handleRequiredTextChange("title", event.target.value)}
            />
          </label>
          <label>
            Node kind
            <select
              value={selectedNode.kind}
              onChange={(event) =>
                onUpdateNode(selectedNode.id, {
                  kind: event.target.value as DiagramNode["kind"],
                })
              }
            >
              <option value="document">document</option>
              <option value="workflow">workflow</option>
              <option value="skill">skill</option>
              <option value="library">library</option>
              <option value="review">review</option>
            </select>
          </label>
          <label>
            Node description
            <textarea
              value={selectedNode.description}
              onChange={(event) =>
                handleRequiredTextChange("description", event.target.value)
              }
              rows={3}
            />
          </label>
          <label>
            Node role
            <select
              value={selectedNode.role ?? "process_step"}
              onChange={(event) =>
                onUpdateNode(selectedNode.id, {
                  role: event.target.value as DiagramNode["role"],
                })
              }
            >
              <option value="process_step">process_step</option>
              <option value="project_component">project_component</option>
              <option value="generated_artifact">generated_artifact</option>
              <option value="test">test</option>
              <option value="tool">tool</option>
              <option value="asset">asset</option>
              <option value="queue">queue</option>
              <option value="docs_context">docs_context</option>
              <option value="skill">skill</option>
              <option value="deployment_gate">deployment_gate</option>
              <option value="review_gate">review_gate</option>
            </select>
          </label>
          <label>
            Output type
            <select
              value={selectedNode.output_type ?? "none"}
              onChange={(event) =>
                onUpdateNode(selectedNode.id, {
                  output_type: event.target.value as DiagramNode["output_type"],
                })
              }
            >
              <option value="none">none</option>
              <option value="document">document</option>
              <option value="project_scaffold">project_scaffold</option>
              <option value="source_file">source_file</option>
              <option value="test_file">test_file</option>
              <option value="config">config</option>
              <option value="orchestrator_resource">orchestrator_resource</option>
              <option value="validation_report">validation_report</option>
              <option value="approval_gate">approval_gate</option>
            </select>
          </label>
          <label>
            Project types (comma separated)
            <input
              value={(selectedNode.project_types ?? []).join(", ")}
              onChange={(event) =>
                onUpdateNode(selectedNode.id, {
                  project_types: event.target.value
                    .split(",")
                    .map((value) => value.trim())
                    .filter(Boolean) as DiagramNode["project_types"],
                })
              }
            />
          </label>
          <label>
            Context policy
            <select
              value={selectedNode.context_policy ?? "advisory"}
              onChange={(event) =>
                onUpdateNode(selectedNode.id, {
                  context_policy: event.target.value as DiagramNode["context_policy"],
                })
              }
            >
              <option value="advisory">advisory</option>
              <option value="strict">strict</option>
            </select>
          </label>
          <label>
            Strict citation
            <input
              value={selectedNode.strict_citation ?? ""}
              onChange={(event) =>
                onUpdateNode(selectedNode.id, { strict_citation: event.target.value })
              }
            />
          </label>
          <label>
            Node source
            <input
              value={selectedNode.source ?? ""}
              onChange={(event) =>
                onUpdateNode(selectedNode.id, { source: event.target.value })
              }
            />
          </label>
        </div>
      ) : (
        <p className="muted">Select a node to inspect how it maps to docs, skills, or books.</p>
      )}
      <div className="context-block">
        <h3>Library context</h3>
        {libraryContext.length === 0 ? (
          <p className="muted">Search the library to attach book sections to the diagram.</p>
        ) : (
          <ul className="compact-list">
            {libraryContext.slice(0, 3).map((item) => (
              <li key={`${item.book_id}/${item.chapter_id}/${item.section_id}`}>
                {item.book_id}/{item.chapter_id}/{item.section_id}
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="context-block">
        <h3>Review focus</h3>
        {selectedFinding ? (
          <p>
            [{selectedFinding.severity ?? "info"}] {selectedFinding.rule ?? "Uncategorized"}
          </p>
        ) : (
          <p className="muted">Run review and select a finding to anchor fixes in the canvas.</p>
        )}
      </div>
    </section>
  );
}
