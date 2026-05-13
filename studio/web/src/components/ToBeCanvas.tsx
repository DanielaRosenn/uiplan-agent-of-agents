import React, { useMemo, useState } from "react";
import {
  CheckCircle2,
  Cloud,
  Database,
  GitBranch,
  ListChecks,
  Radio,
  Route,
  UserCheck,
  Workflow,
} from "lucide-react";

import { LAYERS, PALETTE } from "../theme";
import type { ToBeView, ToBeWorkflow } from "../projectGraph/types";

interface ToBeCanvasProps {
  toBeView: ToBeView;
  onSelectNode?: (nodeId: string) => void;
  selectedNodeId?: string | null;
  selectedBucketType?: string | null;
  selectedPlayer?: string | null;
}

type IconComponent = React.ComponentType<{ size?: number; color?: string; strokeWidth?: number }>;
type StageId = "trigger" | "ingress" | "reason" | "act" | "reply" | "observe" | "end";

interface FlowStage {
  id: StageId;
  label: string;
  y: number;
  height: number;
}

interface FlowNode {
  id: string;
  step: string;
  label: string;
  kind: string;
  stage: StageId;
  x: number;
  y: number;
  w: number;
  h: number;
  color: string;
  soft: string;
  icon: IconComponent;
  summary: string;
  input: string;
  output: string;
  owner: string;
  readiness: string;
  validators: string[];
  blocker: string;
  workflow?: ToBeWorkflow;
}

interface FlowEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  dashed?: boolean;
  color?: string;
}

interface DrillStep {
  id: string;
  type: string;
  label: string;
  detail: string;
  color: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

interface FlowModel {
  stages: FlowStage[];
  nodes: FlowNode[];
  edges: FlowEdge[];
  width: number;
  height: number;
}

const NODE_W = 230;
const NODE_H = 78;
const SMALL_W = 198;
const SMALL_H = 68;
const CANVAS_W = 1200;
const DRILL_STAGES = [
  { label: "Trigger", y: 20, h: 92 },
  { label: "Ingress", y: 112, h: 96 },
  { label: "Reason", y: 208, h: 96 },
  { label: "Act", y: 304, h: 220 },
  { label: "Reply", y: 524, h: 92 },
  { label: "Observe", y: 616, h: 96 },
  { label: "End", y: 712, h: 86 },
];

export default function ToBeCanvas({
  toBeView,
  onSelectNode,
  selectedNodeId,
  selectedBucketType = null,
  selectedPlayer = null,
}: ToBeCanvasProps) {
  const model = useMemo(() => buildFlowModel(toBeView), [toBeView]);
  const defaultNodeId =
    model.nodes.find((node) => `plan:${node.id}` === selectedNodeId || node.id === selectedNodeId)?.id ??
    model.nodes.find((node) => node.workflow && playerForWorkflow(node.workflow) === selectedPlayer)?.id ??
    "ingress";
  const [selectedId, setSelectedId] = useState(defaultNodeId);
  const [drillOpen, setDrillOpen] = useState(false);
  const selectedNode = model.nodes.find((node) => node.id === selectedId) ?? model.nodes[1] ?? model.nodes[0];

  if (!toBeView || (toBeView.buckets.length === 0 && toBeView.workflows.length === 0)) {
    return <EmptyState label="TO-BE VIEW NOT CONFIGURED" />;
  }

  const visibleIds = new Set(
    model.nodes
      .filter((node) => {
        const byBucket = !selectedBucketType || node.workflow?.bucket === selectedBucketType || !node.workflow;
        const byPlayer = !selectedPlayer || (node.workflow && playerForWorkflow(node.workflow) === selectedPlayer) || !node.workflow;
        return byBucket && byPlayer;
      })
      .map((node) => node.id),
  );
  for (const node of model.nodes) {
    if (!node.workflow) visibleIds.add(node.id);
  }

  const selectNode = (node: FlowNode) => {
    setSelectedId(node.id);
    setDrillOpen(true);
    onSelectNode?.(`plan:${node.id}`);
  };

  return (
    <div data-testid="to-be-workflow-builder" style={rootStyle}>
      <div style={topBarStyle}>
        <div>
          <div style={eyebrowStyle}>TO-BE UIPATH FLOW</div>
          <div style={subtitleStyle}>
            {drillOpen ? `L1 drill-down for ${selectedNode.label}` : "High-level architecture first. Click any node to drill into the sub-workflow before generation."}
          </div>
        </div>
        {drillOpen ? (
          <button onClick={() => setDrillOpen(false)} style={backButtonStyle}>BACK TO L0 FLOW</button>
        ) : (
          <div style={toolbarPillsStyle}>
            <span style={metricPillStyle}>{toBeView.workflows.length} workflows</span>
            <span style={metricPillStyle}>{toBeView.integrations.length} integrations</span>
            <span style={metricPillStyle}>{toBeView.orchestrator.length} Orchestrator assets</span>
            <span style={metricPillStyle}>{toBeView.hitl.length} human gates</span>
          </div>
        )}
      </div>

      <div style={scrollAreaStyle}>
        {drillOpen ? (
          <FocusedToBeDrill
            selectedNode={selectedNode}
            toBeView={toBeView}
            onSelectNode={selectNode}
            model={model}
            onBack={() => setDrillOpen(false)}
          />
        ) : (
        <div style={{ ...diagramStyle, width: model.width, height: model.height }}>
          {model.stages.map((stage) => (
            <div key={stage.id} style={{ ...stageBandStyle, top: stage.y, height: stage.height }}>
              <span style={stageLabelStyle}>{stage.label}</span>
            </div>
          ))}

          <svg width={model.width} height={model.height} style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
            <defs>
              <marker id="to-be-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
                <path d="M 0 0 L 8 4 L 0 8 z" fill="#64748b" />
              </marker>
            </defs>
            {model.edges.map((edge) => {
              if (!visibleIds.has(edge.source) || !visibleIds.has(edge.target)) return null;
              const source = model.nodes.find((node) => node.id === edge.source);
              const target = model.nodes.find((node) => node.id === edge.target);
              if (!source || !target) return null;
              const path = connectorPath(source, target, edge);
              return (
                <g key={edge.id}>
                  <path
                    d={path}
                    fill="none"
                    stroke={edge.color ?? "#64748b"}
                    strokeWidth={edge.dashed ? 1.6 : 2.3}
                    strokeDasharray={edge.dashed ? "5 5" : undefined}
                    markerEnd="url(#to-be-arrow)"
                  />
                  <text
                    x={edge.label === "Callback" 
                      ? (source.x + source.w / 2 + (source.x < target.x ? target.x - 20 : target.x + target.w + 20)) / 2
                      : ((source.x + source.w / 2 + target.x + target.w / 2) / 2) + (edge.dashed && edge.label === "Drill" ? (source.x < target.x ? -20 : 20) : 0)}
                    y={edge.label === "Callback"
                      ? source.y + source.h + 16 - 5
                      : ((source.y + source.h + target.y) / 2 - 5)}
                    textAnchor="middle"
                    style={{ 
                      fontFamily: "JetBrains Mono, monospace", 
                      fontSize: 9, 
                      fill: edge.color ?? "#64748b", 
                      fontWeight: 700, 
                      letterSpacing: 0.6,
                      paintOrder: "stroke fill",
                      stroke: "#f8fafc",
                      strokeWidth: 4,
                      strokeLinejoin: "round"
                    }}
                  >
                    {edge.label}
                  </text>
                </g>
              );
            })}
          </svg>

          {model.nodes.filter((node) => visibleIds.has(node.id)).map((node) => (
            <WorkflowNode key={node.id} node={node} selected={node.id === selectedNode?.id} onClick={() => selectNode(node)} />
          ))}
        </div>
        )}
      </div>
    </div>
  );
}

function WorkflowNode({ node, selected, onClick }: { node: FlowNode; selected: boolean; onClick: () => void }) {
  const Icon = node.icon;
  const [hovered, setHovered] = useState(false);
  const compact = node.h < 74;
  return (
    <div
      tabIndex={0}
      style={{
        position: "absolute",
        left: node.x,
        top: node.y,
        width: node.w,
        height: node.h,
        overflow: "visible",
        zIndex: hovered ? 40 : selected ? 20 : 2,
        outline: "none",
      }}
    >
      <button
        onClick={onClick}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        onFocus={() => setHovered(true)}
        onBlur={() => setHovered(false)}
        aria-label={`${node.label} ${node.kind}`}
        title={`${node.label}\n${node.summary}\nInput: ${node.input}\nOutput: ${node.output}\nReadiness: ${node.readiness}\nBlocker: ${node.blocker}`}
        style={{
          position: "relative",
          width: "100%",
          height: "100%",
          boxSizing: "border-box",
          overflow: "hidden",
          borderRadius: 7,
        border: `1px solid ${selected ? node.color : "#d6d3d1"}`,
        borderTop: `4px solid ${node.color}`,
        background: "#fffdfa",
        color: PALETTE.text,
        textAlign: "left",
        cursor: "pointer",
        padding: "9px 11px",
          boxShadow: selected ? `0 0 0 4px ${node.color}20, 0 12px 22px rgba(15, 23, 42, 0.10)` : "0 4px 12px rgba(15, 23, 42, 0.06)",
      }}
    >
      <div style={{ display: "flex", gap: 9, alignItems: "flex-start" }}>
        <span style={{ ...nodeIconStyle, background: node.soft, borderColor: `${node.color}55` }}>
          <Icon size={15} color={node.color} strokeWidth={2.3} />
        </span>
        <span style={{ minWidth: 0, flex: 1 }}>
          <span style={nodeStepStyle}>{node.step} <span style={{ color: node.color }}>{node.kind}</span></span>
          <span style={nodeTitleStyle}>{node.label}</span>
        </span>
      </div>
        {!compact && <div style={nodeSummaryStyle}>{node.summary}</div>}
      <div style={nodeFooterStyle}>
        <span style={{ color: readinessColor(node.readiness) }}>{node.readiness}</span>
        <span>{node.workflow ? "DRILL" : "L1"}</span>
      </div>
      </button>
      {hovered && (
        <HoverCard
          color={node.color}
          side={node.x > CANVAS_W / 2 ? "left" : "right"}
          align={node.y > 600 ? "bottom" : "top"}
          title={node.label}
          rows={[
            ["Summary", node.summary],
            ["Owner", node.owner],
            ["Input", node.input],
            ["Output", node.output],
            ["Readiness", node.readiness],
            ["Blocker", node.blocker],
          ]}
        />
      )}
    </div>
  );
}

function HoverCard({
  title,
  rows,
  color,
  side,
  align,
}: {
  title: string;
  rows: Array<[string, string]>;
  color: string;
  side: "left" | "right";
  align: "top" | "bottom";
}) {
  return (
    <div
      style={{
        ...hoverCardStyle,
        ...(side === "left" ? { right: "calc(100% + 12px)" } : { left: "calc(100% + 12px)" }),
        ...(align === "bottom" ? { bottom: 0 } : { top: 0 }),
        borderTopColor: color,
      }}
    >
      <div style={hoverTitleStyle}>{title}</div>
      {rows.map(([label, value]) => (
        <div key={label} style={hoverRowStyle}>
          <span style={hoverLabelStyle}>{label}</span>
          <span>{value}</span>
        </div>
      ))}
    </div>
  );
}

function DrillDownDiagram({
  selectedNode,
  toBeView,
  onSelectNode,
  model,
}: {
  selectedNode: FlowNode;
  toBeView: ToBeView;
  onSelectNode: (node: FlowNode) => void;
  model: FlowModel;
}) {
  const activeWorkflow = selectedNode.workflow ?? findRelatedWorkflow(selectedNode, toBeView);
  const player = activeWorkflow ? playerForWorkflow(activeWorkflow) : selectedNode.owner;
  const steps = makeDrillSteps(selectedNode, activeWorkflow);
  const drillWorkflows = model.nodes.filter((node) => node.workflow && (selectedNode.id === "policy" || selectedNode.id === "approval" || node.id === selectedNode.id));

  return (
    <section style={drillPanelStyle}>
      <div style={drillHeaderStyle}>
        <span>L1 DRILL-DOWN: {selectedNode.label}</span>
        <span style={{ color: readinessColor(selectedNode.readiness) }}>{selectedNode.readiness}</span>
      </div>
      <div style={drillMetaStyle}>
        <span>Owner: {player}</span>
        <span>Input: {selectedNode.input}</span>
        <span>Output: {selectedNode.output}</span>
      </div>
      {drillWorkflows.length > 1 && (
        <div style={drillPickerStyle}>
          {drillWorkflows.map((node) => (
            <button key={node.id} onClick={() => onSelectNode(node)} style={drillPickerButtonStyle}>
              {playerForWorkflow(node.workflow!)}
            </button>
          ))}
        </div>
      )}
      <div style={drillCanvasStyle}>
        {DRILL_STAGES.map((stage) => (
          <div key={stage.label} style={{ ...stageBandStyle, top: stage.y, height: stage.h }}>
            <span style={stageLabelStyle}>{stage.label}</span>
          </div>
        ))}
        <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
          <defs>
            <marker id="drill-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M 0 0 L 8 4 L 0 8 z" fill="#64748b" />
            </marker>
          </defs>
          {drillEdges(steps).map((edge) => {
            const source = steps.find((step) => step.id === edge.source);
            const target = steps.find((step) => step.id === edge.target);
            if (!source || !target) return null;
            return (
              <path
                key={`${edge.source}-${edge.target}`}
                d={drillConnectorPath(source, target)}
                fill="none"
                stroke={edge.dashed ? "#0f766e" : "#64748b"}
                strokeWidth={edge.dashed ? 1.6 : 2}
                strokeDasharray={edge.dashed ? "5 5" : undefined}
                markerEnd="url(#drill-arrow)"
              />
            );
          })}
        </svg>
        {steps.map((step) => (
          <DrillStepNode key={step.id} step={step} />
        ))}
      </div>
    </section>
  );
}

function DrillStepNode({ step }: { step: DrillStep }) {
  const [hovered, setHovered] = useState(false);
  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setHovered(true)}
      onBlur={() => setHovered(false)}
      tabIndex={0}
      title={`${step.label}\n${step.detail}`}
      style={{
        ...drillNodeStyle,
        left: step.x,
        top: step.y,
        width: step.w,
        height: step.h,
        borderTopColor: step.color,
        zIndex: hovered ? 20 : 2,
      }}
    >
      <div style={nodeStepStyle}>{step.type}</div>
      <div style={drillNodeTitleStyle}>{step.label}</div>
      <div style={drillNodeDetailStyle}>{step.detail}</div>
      {hovered && (
        <HoverCard
          color={step.color}
          side={step.x > 500 ? "left" : "right"}
          align={step.y > 600 ? "bottom" : "top"}
          title={step.label}
          rows={[["Detail", step.detail]]}
        />
      )}
    </div>
  );
}

function FocusedToBeDrill({
  selectedNode,
  toBeView,
  onSelectNode,
  model,
  onBack,
}: {
  selectedNode: FlowNode;
  toBeView: ToBeView;
  onSelectNode: (node: FlowNode) => void;
  model: FlowModel;
  onBack: () => void;
}) {
  return (
    <div style={focusedDrillStyle}>
      <div style={focusedHeaderStyle}>
        <div>
          <div style={drillHeaderStyle}>L0 TO-BE UIPATH FLOW / L1 SUB-WORKFLOW</div>
          <div style={{ marginTop: 5, fontSize: 16, fontWeight: 800, color: PALETTE.text }}>{selectedNode.label}</div>
        </div>
        <button onClick={onBack} style={backButtonStyle}>BACK TO L0 FLOW</button>
      </div>
      <DrillDownDiagram selectedNode={selectedNode} toBeView={toBeView} onSelectNode={onSelectNode} model={model} />
      <div style={contractStripStyle}>
        <span>Owner: {selectedNode.owner}</span>
        <span>Input: {selectedNode.input}</span>
        <span>Output: {selectedNode.output}</span>
        <span style={{ color: readinessColor(selectedNode.readiness) }}>Readiness: {selectedNode.readiness}</span>
        <span>Blocker: {selectedNode.blocker}</span>
      </div>
    </div>
  );
}

function buildFlowModel(toBeView: ToBeView): FlowModel {
  const stages: FlowStage[] = [
    { id: "trigger", label: "Trigger", y: 22, height: 82 },
    { id: "ingress", label: "Ingress", y: 112, height: 90 },
    { id: "reason", label: "Reason", y: 202, height: 98 },
    { id: "act", label: "Act", y: 300, height: 300 },
    { id: "reply", label: "Reply", y: 600, height: 90 },
    { id: "observe", label: "Observe", y: 690, height: 90 },
    { id: "end", label: "End", y: 780, height: 88 },
  ];
  const workflows = toBeView.workflows;
  const intakeWorkflow = workflows.find((workflow) => workflow.bucket === "intake") ?? workflows[0];
  const approvalWorkflows = workflows.filter((workflow) => workflow.bucket === "processing").slice(0, 3);
  const primaryIntegration = toBeView.integrations[0];
  const evidenceResource = toBeView.orchestrator[1] ?? toBeView.orchestrator[0];
  const humanGate = toBeView.hitl[0];

  const nodes: FlowNode[] = [
    {
      id: "trigger",
      step: "STEP 00",
      label: "Slack request received",
      kind: "TRIGGER",
      stage: "trigger",
      x: 485,
      y: 44,
      w: NODE_W,
      h: NODE_H,
      color: LAYERS.ui.color,
      soft: LAYERS.ui.soft,
      icon: Radio,
      summary: "Requester submits renewal price commitment details from Slack.",
      input: "Slack message",
      output: "Request payload",
      owner: "Requester",
      readiness: "Draft",
      validators: ["UX comprehension reviewer", "Solution architect"],
      blocker: "Confirm mandatory Slack fields.",
    },
    {
      id: "ingress",
      step: "STEP 01",
      label: "Normalize renewal request",
      kind: "ACTIVITY",
      stage: "ingress",
      x: 485,
      y: 132,
      w: NODE_W,
      h: NODE_H,
      color: LAYERS.rpa.color,
      soft: LAYERS.rpa.soft,
      icon: Workflow,
      summary: "Validate payload, enrich account data, and create queue item.",
      input: "Request payload",
      output: "Queue item",
      owner: "UiPath workflow designer",
      readiness: "Needs data contract",
      validators: ["Solution architect", "UiPath workflow designer", "QA/readiness reviewer"],
      blocker: "Queue schema must be approved.",
      workflow: intakeWorkflow,
    },
    {
      id: "policy",
      step: "STEP 02",
      label: "Route approval policy",
      kind: "ACTIVITY",
      stage: "reason",
      x: 485,
      y: 222,
      w: NODE_W,
      h: NODE_H,
      color: LAYERS.agent.color,
      soft: LAYERS.agent.soft,
      icon: Route,
      summary: "Classify requester, thresholds, exception paths, and approver role.",
      input: "Queue item",
      output: "Approval request",
      owner: "Solution architect",
      readiness: "Needs BA decision",
      validators: ["Solution architect", "UX comprehension reviewer"],
      blocker: "Approval thresholds need sign-off.",
    },
    {
      id: "approval",
      step: "STEP 03",
      label: "Create approval task",
      kind: "HITL",
      stage: "act",
      x: 485,
      y: 358,
      w: NODE_W,
      h: NODE_H,
      color: LAYERS.app.color,
      soft: LAYERS.app.soft,
      icon: UserCheck,
      summary: humanGate ? `${humanGate.actor} reviews in ${humanGate.channel}.` : "Human reviewer approves, rejects, or redirects.",
      input: "Approval request",
      output: "Decision callback",
      owner: humanGate?.actor ?? "Business reviewer",
      readiness: "Needs approval contract",
      validators: ["HITL reviewer", "UX comprehension reviewer"],
      blocker: "Callback payload must be validated.",
    },
    {
      id: "update",
      step: "STEP 04",
      label: "Update Salesforce quote",
      kind: "ACTIVITY",
      stage: "act",
      x: 120,
      y: 552,
      w: SMALL_W,
      h: SMALL_H,
      color: LAYERS.external.color,
      soft: LAYERS.external.soft,
      icon: Cloud,
      summary: primaryIntegration ? `Apply approved outcome in ${primaryIntegration.system}.` : "Update the system of record.",
      input: "Decision callback",
      output: "Salesforce update",
      owner: "Integration reviewer",
      readiness: "Needs credential",
      validators: ["Integration contract reviewer", "QA/readiness reviewer"],
      blocker: "Credential and sandbox endpoint required.",
    },
    {
      id: "audit",
      step: "STEP 05",
      label: "Write audit evidence",
      kind: "ACTIVITY",
      stage: "act",
      x: 882,
      y: 552,
      w: SMALL_W,
      h: SMALL_H,
      color: LAYERS.orchestrator.color,
      soft: LAYERS.orchestrator.soft,
      icon: Database,
      summary: evidenceResource ? `${evidenceResource.label} stores traceability.` : "Store queue state and audit trail.",
      input: "Workflow event",
      output: "Audit event",
      owner: "QA/readiness reviewer",
      readiness: "Ready to generate",
      validators: ["QA/readiness reviewer", "Solution architect"],
      blocker: "No open blocker.",
    },
    {
      id: "reply",
      step: "STEP 06",
      label: "Reply in Slack",
      kind: "ACTIVITY",
      stage: "reply",
      x: 485,
      y: 660,
      w: NODE_W,
      h: NODE_H,
      color: "#334155",
      soft: "#e2e8f0",
      icon: ListChecks,
      summary: "Send final approved, rejected, or blocked status to requester.",
      input: "Salesforce update + audit event",
      output: "Slack status reply",
      owner: "Requester",
      readiness: "Ready to generate",
      validators: ["UX comprehension reviewer", "QA/readiness reviewer"],
      blocker: "Confirm final message copy.",
    },
    {
      id: "observe",
      step: "STEP 07",
      label: "Audit run",
      kind: "ACTIVITY",
      stage: "observe",
      x: 485,
      y: 750,
      w: NODE_W,
      h: NODE_H,
      color: LAYERS.orchestrator.color,
      soft: LAYERS.orchestrator.soft,
      icon: Database,
      summary: "Write run log, queue reference, and evidence records.",
      input: "Final state",
      output: "Audit trail",
      owner: "Orchestrator",
      readiness: "Ready to generate",
      validators: ["QA/readiness reviewer"],
      blocker: "No open blocker.",
    },
    {
      id: "done",
      step: "END",
      label: "Done",
      kind: "OUTCOME",
      stage: "end",
      x: 515,
      y: 846,
      w: 170,
      h: 54,
      color: "#475569",
      soft: "#e2e8f0",
      icon: CheckCircle2,
      summary: "Business status is visible and traceable.",
      input: "Audit trail",
      output: "Complete",
      owner: "Business",
      readiness: "Ready to generate",
      validators: ["Solution architect"],
      blocker: "No open blocker.",
    },
  ];

  approvalWorkflows.forEach((workflow, index) => {
    const x = [120, 882, 882][index] ?? 120;
    const y = [350, 350, 442][index] ?? 442;
    const player = playerForWorkflow(workflow);
    nodes.push({
      id: `subflow-${workflow.id}`,
      step: `SUB ${index + 1}`,
      label: `${player} approval workflow`,
      kind: "DRILL-DOWN",
      stage: "act",
      x,
      y,
      w: SMALL_W,
      h: SMALL_H,
      color: "#0f766e",
      soft: "#ccfbf1",
      icon: GitBranch,
      summary: `${workflow.internal_steps.length} planned UiPath steps for ${player}.`,
      input: "Approval request",
      output: "Decision callback",
      owner: player,
      readiness: inferWorkflowReadiness(workflow),
      validators: workflow.validator_roles ?? ["UiPath workflow designer", "QA/readiness reviewer"],
      blocker: workflow.blockers?.join(", ") || "Confirm credentials and test data.",
      workflow,
    });
  });

  const edges: FlowEdge[] = [
    { id: "trigger-ingress", source: "trigger", target: "ingress", label: "Slack request", color: LAYERS.ui.color },
    { id: "ingress-policy", source: "ingress", target: "policy", label: "Queue item", color: LAYERS.rpa.color },
    { id: "policy-approval", source: "policy", target: "approval", label: "Approval request", color: LAYERS.app.color },
    { id: "approval-update", source: "approval", target: "update", label: "Approved", color: LAYERS.external.color },
    { id: "approval-audit", source: "approval", target: "audit", label: "Decision", color: LAYERS.orchestrator.color },
    { id: "update-reply", source: "update", target: "reply", label: "Salesforce update", color: "#334155" },
    { id: "audit-reply", source: "audit", target: "reply", label: "Audit event", color: "#334155", dashed: true },
    { id: "reply-observe", source: "reply", target: "observe", label: "Slack reply", color: "#334155" },
    { id: "observe-done", source: "observe", target: "done", label: "Complete", color: "#475569" },
  ];
  for (const node of nodes.filter((node) => node.workflow && node.id.startsWith("subflow-"))) {
    edges.push({ id: `policy-${node.id}`, source: "policy", target: node.id, label: "Drill", color: "#0f766e", dashed: true });
    edges.push({ id: `${node.id}-approval`, source: node.id, target: "approval", label: "Callback", color: "#0f766e", dashed: true });
  }

  return { stages, nodes, edges, width: CANVAS_W, height: 880 };
}

function connectorPath(source: FlowNode, target: FlowNode, edge?: FlowEdge): string {
  const sx = source.x + source.w / 2;
  const sy = source.y + source.h;
  const tx = target.x + target.w / 2;
  const ty = target.y;

  if (edge?.label === "Callback") {
    const isLeft = source.x < target.x;
    const sideX = isLeft ? target.x - 20 : target.x + target.w + 20;
    const sideY = target.y + target.h / 2;
    return `M ${sx} ${sy} L ${sx} ${sy + 16} L ${sideX} ${sy + 16} L ${sideX} ${sideY} L ${isLeft ? target.x : target.x + target.w} ${sideY}`;
  }

  if (Math.abs(sx - tx) < 40 && target.y > source.y) {
    return `M ${sx} ${sy} L ${tx} ${ty}`;
  }
  const midY = sy + Math.max(22, (ty - sy) * 0.5);
  return `M ${sx} ${sy} L ${sx} ${midY} L ${tx} ${midY} L ${tx} ${ty}`;
}

function findRelatedWorkflow(node: FlowNode, toBeView: ToBeView): ToBeWorkflow | undefined {
  if (node.id === "ingress") return toBeView.workflows.find((workflow) => workflow.bucket === "intake");
  if (node.id === "policy" || node.id === "approval") return toBeView.workflows.find((workflow) => workflow.bucket === "processing");
  return undefined;
}

function makeDrillSteps(node: FlowNode, workflow?: ToBeWorkflow): DrillStep[] {
  const sourceSteps = workflow?.internal_steps?.slice(0, 5).map((step) => cleanStepLabel(step.label)) ?? [];
  const labels = sourceSteps.length > 0
    ? sourceSteps
    : ["Receive input", "Validate contract", "Decide route", "Execute activity", "Handle exception"];
  const centerX = 324;
  const branchLeft = 96;
  const branchRight = 602;
  const mainW = 238;
  const branchW = 206;
  return [
    { id: "input", type: "INPUT", label: node.input, detail: "Payload entering this sub-workflow.", color: LAYERS.ui.color, x: centerX, y: 42, w: mainW, h: 70 },
    { id: "ingress", type: "STEP 01", label: labels[0] ?? "Validate request", detail: "Normalize fields and reject missing data early.", color: LAYERS.rpa.color, x: centerX, y: 126, w: mainW, h: 74 },
    { id: "reason", type: "STEP 02", label: labels[1] ?? "Decide route", detail: "Apply rule, threshold, or approver routing logic.", color: LAYERS.agent.color, x: centerX, y: 220, w: mainW, h: 74 },
    { id: "act-main", type: "STEP 03", label: labels[2] ?? node.label, detail: "Primary UiPath activity group for the selected node.", color: LAYERS.app.color, x: centerX, y: 318, w: mainW, h: 74 },
    { id: "act-update", type: "STEP 04", label: labels[3] ?? "Commit approved state", detail: "Write the happy-path outcome to the next system.", color: LAYERS.external.color, x: branchLeft, y: 430, w: branchW, h: 74 },
    { id: "act-exception", type: "STEP 05", label: labels[4] ?? "Handle exception", detail: "Escalate blocked, rejected, or incomplete cases.", color: "#0f766e", x: branchRight, y: 430, w: branchW, h: 74 },
    { id: "reply", type: "OUTPUT", label: node.output, detail: "Contract emitted to the parent L0 flow.", color: "#334155", x: centerX, y: 546, w: mainW, h: 70 },
    { id: "observe", type: "AUDIT", label: "Write trace event", detail: "Persist input, decision, output, and correlation id.", color: LAYERS.orchestrator.color, x: centerX, y: 630, w: mainW, h: 70 },
    { id: "end", type: "END", label: "Return to parent flow", detail: "L0 continues from this completed sub-workflow.", color: "#475569", x: 358, y: 724, w: 170, h: 54 },
  ];
}

function drillEdges(steps: DrillStep[]) {
  const ids = new Set(steps.map((step) => step.id));
  return [
    { source: "input", target: "ingress" },
    { source: "ingress", target: "reason" },
    { source: "reason", target: "act-main" },
    { source: "act-main", target: "act-update" },
    { source: "act-main", target: "act-exception", dashed: true },
    { source: "act-update", target: "reply" },
    { source: "act-exception", target: "reply", dashed: true },
    { source: "reply", target: "observe" },
    { source: "observe", target: "end" },
  ].filter((edge) => ids.has(edge.source) && ids.has(edge.target));
}

function drillConnectorPath(source: DrillStep, target: DrillStep): string {
  const sx = source.x + source.w / 2;
  const sy = source.y + source.h;
  const tx = target.x + target.w / 2;
  const ty = target.y;
  if (Math.abs(sx - tx) < 36) return `M ${sx} ${sy} L ${tx} ${ty}`;
  const midY = sy + Math.max(24, (ty - sy) * 0.48);
  return `M ${sx} ${sy} L ${sx} ${midY} L ${tx} ${midY} L ${tx} ${ty}`;
}

function playerForWorkflow(workflow: ToBeWorkflow): string {
  const label = workflow.label.toLowerCase();
  if (label.includes("salesrep") || label.includes("sales rep")) return "Sales Rep";
  if (label.includes("manager")) return "Manager";
  if (label.includes("finance")) return "Finance";
  if (label.includes("revops") || label.includes("rev ops")) return "RevOps";
  if (workflow.bucket === "intake") return "Request Intake";
  return "Shared";
}

function inferWorkflowReadiness(workflow: ToBeWorkflow): string {
  const text = `${workflow.label} ${workflow.internal_steps.map((step) => step.label).join(" ")}`.toLowerCase();
  if (text.includes("credential")) return "Needs credential";
  if (workflow.bucket === "intake") return "Needs data contract";
  return "Needs BA decision";
}

function cleanStepLabel(label: string): string {
  return label
    .replace(/\.xaml/gi, "")
    .replace(/_/g, " ")
    .replace(/\b(Get|Set|Invoke|Create|Update|Send|Write|Read)\b/g, (verb) => verb.toLowerCase())
    .replace(/\s+/g, " ")
    .trim();
}

function readinessColor(readiness: string): string {
  const value = readiness.toLowerCase();
  if (value.includes("ready") || value.includes("tested") || value.includes("generated")) return "#059669";
  if (value.includes("blocked")) return "#dc2626";
  if (value.includes("credential") || value.includes("contract") || value.includes("decision")) return "#d97706";
  return "#64748b";
}

const rootStyle: React.CSSProperties = {
  position: "absolute",
  inset: 0,
  background: "#f8fafc",
  overflow: "hidden",
  display: "flex",
  flexDirection: "column",
};

const topBarStyle: React.CSSProperties = {
  minHeight: 60,
  borderBottom: `1px solid ${PALETTE.rule}`,
  background: PALETTE.panel,
  padding: "10px 16px",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 12,
  flexShrink: 0,
};

const scrollAreaStyle: React.CSSProperties = {
  flex: 1,
  overflow: "auto",
  padding: "12px 0 24px",
};

const diagramStyle: React.CSSProperties = {
  position: "relative",
  margin: "0 auto",
  background: "radial-gradient(circle at 1px 1px, #d9e1ea 1px, transparent 0)",
  backgroundSize: "22px 22px",
  borderLeft: `1px solid ${PALETTE.rule}`,
  borderRight: `1px solid ${PALETTE.rule}`,
};

const stageBandStyle: React.CSSProperties = {
  position: "absolute",
  left: 0,
  right: 0,
  borderTop: `1px solid ${PALETTE.rule}`,
  background: "rgba(255,255,255,0.56)",
};

const stageLabelStyle: React.CSSProperties = {
  position: "absolute",
  left: 24,
  top: 14,
  border: `1px solid ${PALETTE.rule}`,
  background: "#ffffff",
  color: PALETTE.textDim,
  padding: "3px 8px",
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 8.5,
  letterSpacing: "0.14em",
  fontWeight: 800,
  textTransform: "uppercase",
};

const nodeIconStyle: React.CSSProperties = {
  width: 27,
  height: 27,
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  border: "1px solid",
  flexShrink: 0,
};

const nodeStepStyle: React.CSSProperties = {
  display: "block",
  color: PALETTE.textMute,
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 8,
  letterSpacing: "0.1em",
  fontWeight: 800,
  textTransform: "uppercase",
};

const nodeTitleStyle: React.CSSProperties = {
  display: "block",
  marginTop: 3,
  color: PALETTE.text,
  fontSize: 13,
  fontWeight: 800,
  lineHeight: 1.12,
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
};

const nodeSummaryStyle: React.CSSProperties = {
  marginTop: 6,
  color: PALETTE.textDim,
  fontSize: 10.5,
  lineHeight: 1.28,
  display: "-webkit-box",
  WebkitLineClamp: 2,
  WebkitBoxOrient: "vertical",
  overflow: "hidden",
};

const nodeFooterStyle: React.CSSProperties = {
  marginTop: 8,
  display: "flex",
  justifyContent: "space-between",
  gap: 8,
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 8,
  letterSpacing: "0.08em",
  fontWeight: 800,
  textTransform: "uppercase",
};

const drillPanelStyle: React.CSSProperties = {
  border: `1px solid ${PALETTE.rule}`,
  borderTop: "4px solid #0f766e",
  background: "rgba(255, 255, 255, 0.96)",
  boxShadow: "0 18px 40px rgba(15, 23, 42, 0.12)",
  padding: 14,
};

const drillHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: 12,
  color: PALETTE.textDim,
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 9.5,
  letterSpacing: "0.13em",
  fontWeight: 800,
  textTransform: "uppercase",
};

const drillMetaStyle: React.CSSProperties = {
  marginTop: 10,
  display: "flex",
  gap: 8,
  flexWrap: "wrap",
  color: PALETTE.textDim,
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 9,
};

const drillPickerStyle: React.CSSProperties = {
  marginTop: 10,
  display: "flex",
  gap: 6,
  flexWrap: "wrap",
};

const drillPickerButtonStyle: React.CSSProperties = {
  border: "1px solid #0f766e",
  background: "#ccfbf1",
  color: "#0f766e",
  padding: "5px 8px",
  fontSize: 10,
  fontWeight: 800,
  cursor: "pointer",
};

const drillCanvasStyle: React.CSSProperties = {
  position: "relative",
  height: 812,
  marginTop: 10,
  background: "radial-gradient(circle at 1px 1px, #d9e1ea 1px, transparent 0)",
  backgroundSize: "20px 20px",
  overflow: "auto",
};

const drillNodeStyle: React.CSSProperties = {
  position: "absolute",
  border: `1px solid ${PALETTE.rule}`,
  borderTop: "4px solid",
  background: "#fffdfa",
  padding: 8,
  borderRadius: 7,
  boxSizing: "border-box",
  overflow: "hidden",
  boxShadow: "0 4px 12px rgba(15, 23, 42, 0.06)",
};

const drillNodeTitleStyle: React.CSSProperties = {
  marginTop: 4,
  fontWeight: 800,
  fontSize: 12,
  lineHeight: 1.15,
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
};

const drillNodeDetailStyle: React.CSSProperties = {
  marginTop: 4,
  color: PALETTE.textDim,
  fontSize: 10.5,
  lineHeight: 1.25,
  display: "-webkit-box",
  WebkitLineClamp: 2,
  WebkitBoxOrient: "vertical",
  overflow: "hidden",
};

const hoverCardStyle: React.CSSProperties = {
  position: "absolute",
  width: 282,
  maxWidth: 282,
  border: `1px solid ${PALETTE.rule}`,
  borderTop: "4px solid",
  borderRadius: 8,
  background: "#ffffff",
  color: PALETTE.text,
  padding: 10,
  boxShadow: "0 18px 38px rgba(15, 23, 42, 0.16)",
  pointerEvents: "none",
  fontFamily: "'Inter', system-ui, sans-serif",
  textAlign: "left",
};

const hoverTitleStyle: React.CSSProperties = {
  fontSize: 12.5,
  fontWeight: 800,
  lineHeight: 1.25,
  marginBottom: 8,
};

const hoverRowStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "78px 1fr",
  gap: 8,
  fontSize: 11,
  lineHeight: 1.32,
  color: PALETTE.textDim,
  marginTop: 5,
};

const hoverLabelStyle: React.CSSProperties = {
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 8.5,
  letterSpacing: "0.08em",
  fontWeight: 800,
  color: PALETTE.textMute,
  textTransform: "uppercase",
};

const eyebrowStyle: React.CSSProperties = {
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 10,
  letterSpacing: "0.18em",
  fontWeight: 800,
  color: "#0f766e",
};

const subtitleStyle: React.CSSProperties = {
  marginTop: 4,
  fontSize: 13,
  color: PALETTE.textDim,
};

const toolbarPillsStyle: React.CSSProperties = {
  display: "flex",
  gap: 8,
  flexWrap: "wrap",
  justifyContent: "flex-end",
};

const metricPillStyle: React.CSSProperties = {
  border: `1px solid ${PALETTE.rule}`,
  background: "#ffffff",
  color: PALETTE.textDim,
  padding: "5px 8px",
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 9,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  whiteSpace: "nowrap",
};

const focusedDrillStyle: React.CSSProperties = {
  width: "min(920px, calc(100% - 48px))",
  margin: "0 auto",
  display: "grid",
  gap: 12,
};

const focusedHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 12,
  border: `1px solid ${PALETTE.rule}`,
  background: PALETTE.panel,
  padding: 12,
};

const backButtonStyle: React.CSSProperties = {
  border: "1px solid #0f766e",
  background: "#ccfbf1",
  color: "#0f766e",
  padding: "7px 10px",
  cursor: "pointer",
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 9.5,
  letterSpacing: "0.08em",
  fontWeight: 800,
};

const contractStripStyle: React.CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: 8,
  border: `1px solid ${PALETTE.rule}`,
  background: "#fffdfa",
  padding: 10,
  color: PALETTE.textDim,
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 9.5,
};

function EmptyState({ label }: { label: string }) {
  return (
    <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", color: PALETTE.textDim }}>
      <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, letterSpacing: "0.18em", fontWeight: 800 }}>
        {label}
      </div>
    </div>
  );
}
