import React from "react";

import type { ApprovalPackageDetail, StageId } from "../generationTypes";
import type { DiagramEdge, DiagramNode } from "../types";

interface DiagramCanvasProps {
  nodes: DiagramNode[];
  edges: DiagramEdge[];
  selectedNodeId: string | null;
  visualState: {
    focusedNodeId: string | null;
    highlightedNodeIds: string[];
    highlightedEdgeIds: string[];
    mode: string;
    summary: string | null;
  };
  edgeTargetId: string;
  edgeLabel: string;
  canDeleteSelectedNode: boolean;
  packageDetail: ApprovalPackageDetail | null;
  selectedProposalId: string | null;
  proposalPreviewId: string | null;
  onSelectNodeId: (nodeId: string) => void;
  onMoveNode: (nodeId: string, x: number, y: number) => void;
  onAddNode: (kind: DiagramNode["kind"]) => void;
  onDeleteSelectedNode: () => void;
  onChangeEdgeTargetId: (nodeId: string) => void;
  onChangeEdgeLabel: (label: string) => void;
  onCreateEdge: () => void;
}

const NODE_WIDTH = 204;
const NODE_HEIGHT = 104;
const STAGE_LABELS: Record<StageId, string> = {
  "01-plan": "Plan",
  "02-scaffold": "Scaffold",
  "03-code": "Code",
  "04-tests": "Tests",
  "05-validation": "Validation",
};

function nodeCenter(node: DiagramNode) {
  return {
    x: node.x + NODE_WIDTH / 2,
    y: node.y + NODE_HEIGHT / 2,
  };
}

function getNodeIcon(node: DiagramNode) {
  const hint = node.icon_hint ?? node.visual_role ?? node.role ?? node.kind;
  if (hint.includes("trigger")) return "T";
  if (hint.includes("agent") || node.id === "plan") return "A";
  if (hint.includes("library")) return "L";
  if (hint.includes("skill")) return "S";
  if (hint.includes("tool")) return "W";
  if (hint.includes("decision") || node.kind === "review") return "IF";
  if (hint.includes("package") || hint.includes("success")) return "OK";
  if (hint.includes("warning") || hint.includes("fallback")) return "!";
  return node.kind.slice(0, 1).toUpperCase();
}

function getNodeTypeLabel(node: DiagramNode) {
  if (node.visual_role === "trigger") return "Trigger";
  if (node.visual_role === "central_action") return "Agent action";
  if (node.visual_role === "helper_context") return "Helper";
  if (node.visual_role === "decision_branch") return "Decision";
  if (node.visual_role === "success_branch") return "Success output";
  if (node.visual_role === "fallback_branch") return "Fallback output";
  return node.role ?? node.kind;
}

function getEdgeClassName(edge: DiagramEdge, highlightedEdgeIds: Set<string>, hasHighlights: boolean) {
  return [
    "diagram-edge",
    edge.branch ? `diagram-edge-${edge.branch}` : null,
    `diagram-edge-${edge.edge_type ?? "drives"}`,
    highlightedEdgeIds.has(edge.id) ? "diagram-edge-highlighted" : null,
    hasHighlights && !highlightedEdgeIds.has(edge.id) ? "diagram-edge-muted" : null,
  ]
    .filter(Boolean)
    .join(" ");
}

function getNodeClassName(
  node: DiagramNode,
  selectedNodeId: string | null,
  highlightedNodeIds: Set<string>,
  hasHighlights: boolean,
  focusedNodeId: string | null,
) {
  return [
    "diagram-node",
    `diagram-node-${node.kind}`,
    node.layer ? `diagram-node-layer-${node.layer}` : null,
    node.visual_role ? `diagram-node-role-${node.visual_role}` : null,
    node.status ? `diagram-node-status-${node.status}` : null,
    selectedNodeId === node.id ? "diagram-node-selected" : null,
    focusedNodeId === node.id ? "diagram-node-focused" : null,
    highlightedNodeIds.has(node.id) ? "diagram-node-highlighted" : null,
    hasHighlights && !highlightedNodeIds.has(node.id) ? "diagram-node-muted" : null,
  ]
    .filter(Boolean)
    .join(" ");
}

export default function DiagramCanvas({
  nodes,
  edges,
  selectedNodeId,
  visualState,
  edgeTargetId,
  edgeLabel,
  canDeleteSelectedNode,
  packageDetail,
  selectedProposalId,
  proposalPreviewId,
  onSelectNodeId,
  onMoveNode,
  onAddNode,
  onDeleteSelectedNode,
  onChangeEdgeTargetId,
  onChangeEdgeLabel,
  onCreateEdge,
}: DiagramCanvasProps) {
  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const edgeTargets = nodes.filter((node) => node.id !== selectedNodeId);
  const highlightedNodeIds = new Set(visualState.highlightedNodeIds);
  const highlightedEdgeIds = new Set(visualState.highlightedEdgeIds);
  const hasHighlights = highlightedNodeIds.size > 0 || highlightedEdgeIds.size > 0;
  const selectedProposal =
    packageDetail?.proposals.find((proposal) => proposal.proposal_id === selectedProposalId) ?? null;

  const getReadinessBadges = (node: DiagramNode) => {
    if (!packageDetail) {
      return [] as string[];
    }

    const badges: string[] = [];
    if (node.layer) {
      badges.push(node.layer);
    }
    if (node.status) {
      badges.push(node.status.replace("_", " "));
    }
    const stageStatuses = packageDetail.approval_state.stage_statuses;
    const generatedStages = packageDetail.manifest.generated_stages;
    const stageIdsForNode = new Set<StageId>();
    for (const proposal of packageDetail.proposals) {
      if (proposal.owning_node_ids.includes(node.id)) {
        stageIdsForNode.add(proposal.stage_id);
      }
    }

    if (node.id === "plan" && generatedStages.includes("01-plan")) {
      badges.push(`Plan: ${stageStatuses["01-plan"]}`);
    }
    if (
      (node.id === "tasks" || node.id === "success_package") &&
      generatedStages.includes("02-scaffold") &&
      stageIdsForNode.size === 0
    ) {
      badges.push(`Scaffold: ${stageStatuses["02-scaffold"]}`);
    }
    for (const stageId of stageIdsForNode) {
      badges.push(`${STAGE_LABELS[stageId]}: ${stageStatuses[stageId]}`);
    }

    if (node.id === "review") {
      badges.push(
        `Package: ${packageDetail.manifest.package_id}`,
        `Current: ${STAGE_LABELS[packageDetail.approval_state.current_stage]}`,
      );
      if (selectedProposal) {
        badges.push(
          selectedProposal.apply_eligible
            ? proposalPreviewId
              ? "Apply ready"
              : "Preview required"
            : "Apply blocked",
        );
      }
    }

    return badges;
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const nodeId = event.dataTransfer.getData("text/plain");
    const bounds = event.currentTarget.getBoundingClientRect();
    onMoveNode(
      nodeId,
      Math.max(16, event.clientX - bounds.left - NODE_WIDTH / 2),
      Math.max(16, event.clientY - bounds.top - NODE_HEIGHT / 2),
    );
  };

  return (
    <section className="diagram-card" aria-label="UiPath diagram builder">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Visual Builder</p>
          <h2>ProjectGraph canvas</h2>
        </div>
        <div className="canvas-summary" aria-label="Canvas overview">
          <span>{nodes.length} nodes</span>
          <span>{edges.length} edges</span>
          <span>Phase 0 safe apply</span>
        </div>
      </div>
      {visualState.summary ? (
        <div className={`trace-summary trace-summary-${visualState.mode}`} aria-live="polite">
          {visualState.summary}
        </div>
      ) : null}
      <div className="canvas-legend" aria-label="Canvas legend">
        <span><i className="legend-dot legend-dot-success" />success</span>
        <span><i className="legend-dot legend-dot-fallback" />fallback</span>
        <span><i className="legend-dot legend-dot-context" />context</span>
        <span><i className="legend-dot legend-dot-dependency" />dependency</span>
      </div>
      <div className="builder-toolbar" aria-label="Canvas builder controls">
        <div className="builder-toolbar-group" aria-label="Add nodes">
          <span className="toolbar-label">Add node</span>
          {(["workflow", "skill", "library", "review"] as const).map((kind) => (
            <button key={kind} type="button" onClick={() => onAddNode(kind)}>
              Add {kind} node
            </button>
          ))}
        </div>
        <div className="builder-toolbar-group" aria-label="Create edge">
          <label>
            Edge target
            <select
              value={edgeTargetId}
              onChange={(event) => onChangeEdgeTargetId(event.target.value)}
              disabled={!selectedNodeId || edgeTargets.length === 0}
            >
              {edgeTargets.map((node) => (
                <option key={node.id} value={node.id}>
                  {node.title} ({node.id})
                </option>
              ))}
            </select>
          </label>
          <label>
            Edge label
            <input
              value={edgeLabel}
              onChange={(event) => onChangeEdgeLabel(event.target.value)}
              placeholder="connects to"
            />
          </label>
          <button
            type="button"
            onClick={onCreateEdge}
            disabled={!selectedNodeId || !edgeTargetId || !edgeLabel.trim()}
          >
            Create edge
          </button>
        </div>
        <div className="builder-toolbar-group" aria-label="Delete selected node">
          <button type="button" onClick={onDeleteSelectedNode} disabled={!canDeleteSelectedNode}>
            Delete selected node
          </button>
          {selectedNodeId && !canDeleteSelectedNode ? (
            <span className="muted">Core default nodes cannot be deleted.</span>
          ) : null}
        </div>
      </div>
      <div
        className="diagram-canvas"
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
      >
        <svg className="diagram-edges" aria-hidden="true">
          {edges.map((edge) => {
            const from = nodeById.get(edge.from);
            const to = nodeById.get(edge.to);
            if (!from || !to) {
              return null;
            }
            const start = nodeCenter(from);
            const end = nodeCenter(to);
            const midX = (start.x + end.x) / 2;
            const midY = (start.y + end.y) / 2;
            const curved = Math.abs(start.y - end.y) > 100;
            const controlOffset = edge.branch === "fallback" ? 90 : 48;
            const path = curved
              ? `M ${start.x} ${start.y} C ${start.x + controlOffset} ${start.y}, ${end.x - controlOffset} ${end.y}, ${end.x} ${end.y}`
              : `M ${start.x} ${start.y} L ${end.x} ${end.y}`;
            return (
              <g key={edge.id} className={getEdgeClassName(edge, highlightedEdgeIds, hasHighlights)}>
                <path d={path} />
                <text x={midX} y={midY - 8} className="edge-label">
                  {edge.label}
                </text>
              </g>
            );
          })}
        </svg>
        {nodes.map((node) => (
          <button
            key={node.id}
            type="button"
            className={getNodeClassName(
              node,
              selectedNodeId,
              highlightedNodeIds,
              hasHighlights,
              visualState.focusedNodeId,
            )}
            style={{ left: node.x, top: node.y }}
            draggable
            onClick={() => onSelectNodeId(node.id)}
            onDragStart={(event) => event.dataTransfer.setData("text/plain", node.id)}
            aria-pressed={selectedNodeId === node.id}
          >
            <span className="node-card-header">
              <span className="node-icon" aria-hidden="true">{getNodeIcon(node)}</span>
              <span>
                <span className="node-kind">{getNodeTypeLabel(node)}</span>
                <strong>{node.title}</strong>
              </span>
              {node.status ? <span className={`node-status node-status-${node.status}`} /> : null}
            </span>
            <span className="node-description">{node.description}</span>
            <div className="node-badges">
              {getReadinessBadges(node).map((badge, badgeIndex) => (
                <span key={`${node.id}-${badge}-${badgeIndex}`} className="node-badge">
                  {badge}
                </span>
              ))}
            </div>
            <span className="node-meta-row">
              {node.role ? <span className="node-meta">role: {node.role}</span> : null}
              {node.output_type ? <span className="node-meta">output: {node.output_type}</span> : null}
            </span>
            {node.project_types && node.project_types.length > 0 ? (
              <span className="node-meta">projects: {node.project_types.join(", ")}</span>
            ) : null}
            {node.context_policy ? (
              <span className="node-meta">
                context: {node.context_policy}
                {node.strict_citation ? ` (${node.strict_citation})` : ""}
              </span>
            ) : null}
          </button>
        ))}
        <div className="canvas-minimap" aria-label="Mini overview">
          {nodes.map((node) => (
            <span
              key={`mini-${node.id}`}
              className={[
                "minimap-node",
                selectedNodeId === node.id ? "minimap-node-selected" : null,
                highlightedNodeIds.has(node.id) ? "minimap-node-highlighted" : null,
              ]
                .filter(Boolean)
                .join(" ")}
              style={{ left: `${Math.max(4, node.x / 9)}px`, top: `${Math.max(4, node.y / 7)}px` }}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
