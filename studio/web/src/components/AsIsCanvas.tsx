import React, { useMemo, useState } from "react";
import { CheckCircle2, FileSpreadsheet, Mail, MessageSquare, Search, Timer, Users } from "lucide-react";

import { PALETTE } from "../theme";
import type { AsIsView, Handoff } from "../projectGraph/types";

interface AsIsCanvasProps {
  asIsView: AsIsView;
  onSelectHandoff?: (handoffId: string) => void;
  selectedHandoffId?: string | null;
  selectedActor?: string | null;
  density?: "executive" | "detailed";
  selectedPhase?: number | null;
  onSelectActor?: (actor: string | null) => void;
}

type IconComponent = React.ComponentType<{ size?: number; color?: string; strokeWidth?: number }>;

interface ManualNode {
  id: string;
  step: string;
  label: string;
  type: string;
  stage: string;
  x: number;
  y: number;
  w: number;
  h: number;
  color: string;
  icon: IconComponent;
  actor: string;
  system: string;
  output: string;
  pain: string;
  handoff?: Handoff;
}

interface ManualEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  dashed?: boolean;
}

interface ManualDrillStep {
  id: string;
  type: string;
  label: string;
  detail: string;
  x: number;
  y: number;
  w: number;
  h: number;
  color: string;
}

const CANVAS_W = 1200;
const NODE_W = 238;
const NODE_H = 86;

export default function AsIsCanvas({ asIsView, onSelectHandoff, selectedHandoffId, selectedActor = null }: AsIsCanvasProps) {
  const model = useMemo(() => buildAsIsModel(asIsView), [asIsView]);
  const initialId = model.nodes.find((node) => node.handoff?.id === selectedHandoffId)?.id ?? "manual-triage";
  const [selectedId, setSelectedId] = useState(initialId);
  const [drillOpen, setDrillOpen] = useState(false);
  const selectedNode = model.nodes.find((node) => node.id === selectedId) ?? model.nodes[0];

  if (!asIsView || asIsView.swimlanes.length === 0) {
    return <EmptyState />;
  }

  const visibleNodes = selectedActor
    ? model.nodes.filter((node) => node.actor === selectedActor || !node.handoff)
    : model.nodes;
  const visibleIds = new Set(visibleNodes.map((node) => node.id));

  const selectNode = (node: ManualNode) => {
    setSelectedId(node.id);
    setDrillOpen(true);
    if (node.handoff) onSelectHandoff?.(node.handoff.id);
  };

  return (
    <div style={rootStyle}>
      <div style={topBarStyle}>
        <div>
          <div style={eyebrowStyle}>AS-IS MANUAL FLOW</div>
          <div style={subtitleStyle}>
            {drillOpen ? `L1 drill-down for ${selectedNode.label}` : "How work happens today: people, handoffs, systems, delays, and evidence gaps."}
          </div>
        </div>
        {drillOpen ? (
          <button onClick={() => setDrillOpen(false)} style={backButtonStyle}>BACK TO L0 FLOW</button>
        ) : (
          <div style={frictionSummaryStyle}>
            {(asIsView.pain_points ?? []).slice(0, 3).map((point) => (
              <span key={point.label} style={painPillStyle}>{point.label}</span>
            ))}
          </div>
        )}
      </div>

      <div style={scrollAreaStyle}>
        {drillOpen ? (
          <FocusedManualDrill node={selectedNode} onBack={() => setDrillOpen(false)} />
        ) : (
        <div style={{ ...diagramStyle, width: CANVAS_W, height: 930 }}>
          {STAGES.map((stage) => (
            <div key={stage.label} style={{ ...stageBandStyle, top: stage.y, height: stage.h }}>
              <span style={stageLabelStyle}>{stage.label}</span>
            </div>
          ))}

          <svg width={CANVAS_W} height={930} style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
            <defs>
              <marker id="as-is-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
                <path d="M 0 0 L 8 4 L 0 8 z" fill="#78716c" />
              </marker>
            </defs>
            {model.edges.map((edge) => {
              if (!visibleIds.has(edge.source) || !visibleIds.has(edge.target)) return null;
              const source = model.nodes.find((node) => node.id === edge.source);
              const target = model.nodes.find((node) => node.id === edge.target);
              if (!source || !target) return null;
              return (
                <g key={edge.id}>
                  <path
                    d={connectorPath(source, target)}
                    fill="none"
                    stroke="#78716c"
                    strokeWidth={edge.dashed ? 1.5 : 2.2}
                    strokeDasharray={edge.dashed ? "5 5" : undefined}
                    markerEnd="url(#as-is-arrow)"
                  />
                  <text
                    x={(source.x + source.w / 2 + target.x + target.w / 2) / 2}
                    y={(source.y + source.h + target.y) / 2 - 5}
                    textAnchor="middle"
                    style={{ 
                      fontFamily: "JetBrains Mono, monospace", 
                      fontSize: 9, 
                      fill: "#78716c", 
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

          {visibleNodes.map((node) => (
            <ManualFlowNode key={node.id} node={node} selected={node.id === selectedId} onClick={() => selectNode(node)} />
          ))}
        </div>
        )}
      </div>
    </div>
  );
}

function ManualFlowNode({ node, selected, onClick }: { node: ManualNode; selected: boolean; onClick: () => void }) {
  const Icon = node.icon;
  const [hovered, setHovered] = useState(false);
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
        aria-label={`${node.label} ${node.type}`}
        title={`${node.label}\nActor: ${node.actor}\nSystem: ${node.system}\nOutput: ${node.output}\nFriction: ${node.pain}`}
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
        <span style={{ ...nodeIconStyle, background: `${node.color}14`, borderColor: `${node.color}55` }}>
          <Icon size={15} color={node.color} strokeWidth={2.3} />
        </span>
        <span style={{ minWidth: 0, flex: 1 }}>
          <span style={nodeStepStyle}>{node.step} <span style={{ color: node.color }}>{node.type}</span></span>
          <span style={nodeTitleStyle}>{node.label}</span>
        </span>
      </div>
      <div style={nodeMetaStyle}>
        <span>Actor: {node.actor}</span>
        <span>System: {node.system}</span>
      </div>
      {node.pain && <div style={painBadgeStyle}>{node.pain}</div>}
      </button>
      {hovered && (
        <HoverCard
          color={node.color}
          side={node.x > CANVAS_W / 2 ? "left" : "right"}
          align={node.y > 650 ? "bottom" : "top"}
          title={node.label}
          rows={[
            ["Actor", node.actor],
            ["System", node.system],
            ["Output", node.output],
            ["Friction", node.pain],
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

function ManualDrillDown({ node }: { node: ManualNode }) {
  const steps: ManualDrillStep[] = [
    { id: "input", type: "TRIGGER", label: "Receive work item", detail: node.handoff?.artifact ?? node.output, x: 324, y: 42, w: 238, h: 70, color: "#d97706" },
    { id: "ingress", type: "INGRESS", label: "Read and interpret", detail: `${node.actor} reviews the request and decides what is missing.`, x: 324, y: 126, w: 238, h: 74, color: "#2563eb" },
    { id: "reason", type: "REASON", label: "Manual judgment", detail: node.pain || "The next action depends on local knowledge.", x: 324, y: 220, w: 238, h: 74, color: "#7c3aed" },
    { id: "act-left", type: "ACT", label: "Ask / wait", detail: "Send a message or wait for another person to respond.", x: 96, y: 430, w: 206, h: 74, color: "#db2777" },
    { id: "act-main", type: "ACT", label: "Update manually", detail: "Copy data into the current system of record.", x: 324, y: 318, w: 238, h: 74, color: "#dc2626" },
    { id: "act-right", type: "ACT", label: "Track evidence", detail: "Record notes or status outside the main workflow.", x: 602, y: 430, w: 206, h: 74, color: "#78716c" },
    { id: "reply", type: "REPLY", label: "Pass output forward", detail: node.output, x: 324, y: 546, w: 238, h: 70, color: "#334155" },
    { id: "observe", type: "OBSERVE", label: "Evidence gap", detail: "Traceability depends on manual notes and message history.", x: 324, y: 630, w: 238, h: 70, color: "#78716c" },
    { id: "end", type: "END", label: "Return to L0 flow", detail: "The next manual step continues in the parent diagram.", x: 358, y: 724, w: 170, h: 54, color: "#475569" },
  ];
  return (
    <section style={drillPanelStyle}>
      <div style={drillHeaderStyle}>AS-IS DRILL-DOWN: {node.label}</div>
      <div style={manualDrillCanvasStyle}>
        {DRILL_STAGES.map((stage) => (
          <div key={stage.label} style={{ ...stageBandStyle, top: stage.y, height: stage.h }}>
            <span style={stageLabelStyle}>{stage.label}</span>
          </div>
        ))}
        <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
          <defs>
            <marker id="manual-drill-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M 0 0 L 8 4 L 0 8 z" fill="#78716c" />
            </marker>
          </defs>
          {manualDrillEdges(steps).map((edge) => {
            const source = steps.find((step) => step.id === edge.source);
            const target = steps.find((step) => step.id === edge.target);
            if (!source || !target) return null;
            return (
              <path
                key={`${edge.source}-${edge.target}`}
                d={manualDrillPath(source, target)}
                fill="none"
                stroke="#78716c"
                strokeWidth={edge.dashed ? 1.5 : 1.9}
                strokeDasharray={edge.dashed ? "5 5" : undefined}
                markerEnd="url(#manual-drill-arrow)"
              />
            );
          })}
        </svg>
        {steps.map((step) => (
          <ManualDrillStepNode key={step.id} step={step} />
        ))}
      </div>
    </section>
  );
}

function ManualDrillStepNode({ step }: { step: ManualDrillStep }) {
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

function FocusedManualDrill({ node, onBack }: { node: ManualNode; onBack: () => void }) {
  return (
    <div style={focusedDrillStyle}>
      <div style={focusedHeaderStyle}>
        <div>
          <div style={drillHeaderStyle}>L0 AS-IS FLOW / L1 DRILL-DOWN</div>
          <div style={{ marginTop: 5, fontSize: 16, fontWeight: 800, color: PALETTE.text }}>{node.label}</div>
        </div>
        <button onClick={onBack} style={backButtonStyle}>BACK TO L0 FLOW</button>
      </div>
      <ManualDrillDown node={node} />
      <div style={contractStripStyle}>
        <span>Actor: {node.actor}</span>
        <span>System: {node.system}</span>
        <span>Output: {node.output}</span>
        <span>Friction: {node.pain || "Manual interpretation"}</span>
      </div>
    </div>
  );
}

function buildAsIsModel(asIsView: AsIsView) {
  const handoffs = [...asIsView.handoffs].sort((a, b) => a.sequence - b.sequence);
  const h0 = handoffs[0];
  const h1 = handoffs[1] ?? h0;
  const h2 = handoffs[2] ?? h1;
  const h3 = handoffs[3] ?? h2;
  const h4 = handoffs[4] ?? h3;
  const nodes: ManualNode[] = [
    node("request", "STEP 00", "Renewal request arrives", "TRIGGER", 481, 48, MessageSquare, "#d97706", h0?.from_actor ?? "Requester", "Slack / email", "Request details", "Unstructured request", h0),
    node("read", "STEP 01", "Sales Ops reads request", "HANDOFF", 481, 144, Mail, "#2563eb", h0?.to_actor ?? "Sales Ops", "Inbox / Slack", "Manual intake", "Ownership unclear", h0),
    node("lookup", "STEP 02", "Manual account lookup", "LOOKUP", 481, 258, Search, "#7c3aed", h1?.from_actor ?? "Sales Ops", "Salesforce", "Account context", "Manual copy/paste", h1),
    node("route", "STEP 03", "Decide approval path", "DECISION", 481, 378, Users, "#0f766e", h2?.from_actor ?? "Sales Ops", "Policy docs", "Approver request", "Rules vary by case", h2),
    node("approval", "STEP 04", "Wait for approval", "WAIT", 120, 510, Timer, "#db2777", h3?.to_actor ?? "Manager", "Email / Slack", "Approval answer", "2-day delay risk", h3),
    node("update", "STEP 05", "Update quote by hand", "MANUAL UPDATE", 842, 510, FileSpreadsheet, "#dc2626", h4?.from_actor ?? "RevOps", "Salesforce / spreadsheet", "Updated quote", "Audit trail missing", h4),
    node("reply", "STEP 06", "Reply to requester", "REPLY", 481, 628, MessageSquare, "#334155", h4?.to_actor ?? "Sales Rep", "Slack / email", "Status reply", "Status can be stale", h4),
    node("evidence", "STEP 07", "Copy notes into tracker", "EVIDENCE", 481, 732, FileSpreadsheet, "#78716c", "Sales Ops", "Spreadsheet", "Manual evidence", "Evidence fragmented"),
    node("done", "END", "Manual case closed", "OUTCOME", 520, 844, CheckCircle2, "#475569", "Business", "Slack / Salesforce / tracker", "Closed request", "Traceability depends on manual notes"),
  ];
  const edges: ManualEdge[] = [
    { id: "request-read", source: "request", target: "read", label: "Manual handoff" },
    { id: "read-lookup", source: "read", target: "lookup", label: "Lookup" },
    { id: "lookup-route", source: "lookup", target: "route", label: "Policy check" },
    { id: "route-approval", source: "route", target: "approval", label: "Approval ask" },
    { id: "route-update", source: "route", target: "update", label: "Context" },
    { id: "approval-reply", source: "approval", target: "reply", label: "Decision" },
    { id: "update-reply", source: "update", target: "reply", label: "Manual update" },
    { id: "reply-evidence", source: "reply", target: "evidence", label: "Copy evidence", dashed: true },
    { id: "evidence-done", source: "evidence", target: "done", label: "Close", dashed: true },
  ];
  return { nodes, edges };
}

function node(
  id: string,
  step: string,
  label: string,
  type: string,
  x: number,
  y: number,
  icon: IconComponent,
  color: string,
  actor: string,
  system: string,
  output: string,
  pain: string,
  handoff?: Handoff,
): ManualNode {
  return { id, step, label, type, stage: "", x, y, w: NODE_W, h: NODE_H, color, icon, actor, system, output, pain, handoff };
}

function connectorPath(source: ManualNode, target: ManualNode): string {
  const sx = source.x + source.w / 2;
  const sy = source.y + source.h;
  const tx = target.x + target.w / 2;
  const ty = target.y;
  if (Math.abs(sx - tx) < 40) return `M ${sx} ${sy} L ${tx} ${ty}`;
  const midY = sy + Math.max(24, (ty - sy) * 0.5);
  return `M ${sx} ${sy} L ${sx} ${midY} L ${tx} ${midY} L ${tx} ${ty}`;
}

const STAGES = [
  { label: "Trigger", y: 28, h: 100 },
  { label: "Ingress", y: 128, h: 108 },
  { label: "Reason", y: 236, h: 242 },
  { label: "Act", y: 478, h: 132 },
  { label: "Reply", y: 610, h: 106 },
  { label: "Observe", y: 716, h: 108 },
  { label: "End", y: 824, h: 96 },
];

const DRILL_STAGES = [
  { label: "Trigger", y: 20, h: 92 },
  { label: "Ingress", y: 112, h: 96 },
  { label: "Reason", y: 208, h: 96 },
  { label: "Act", y: 304, h: 220 },
  { label: "Reply", y: 524, h: 92 },
  { label: "Observe", y: 616, h: 96 },
  { label: "End", y: 712, h: 86 },
];

function manualDrillEdges(steps: ManualDrillStep[]) {
  const ids = new Set(steps.map((step) => step.id));
  return [
    { source: "input", target: "ingress" },
    { source: "ingress", target: "reason" },
    { source: "reason", target: "act-main" },
    { source: "act-main", target: "act-left", dashed: true },
    { source: "act-main", target: "act-right", dashed: true },
    { source: "act-left", target: "reply", dashed: true },
    { source: "act-main", target: "reply" },
    { source: "act-right", target: "reply", dashed: true },
    { source: "reply", target: "observe" },
    { source: "observe", target: "end" },
  ].filter((edge) => ids.has(edge.source) && ids.has(edge.target));
}

function manualDrillPath(source: ManualDrillStep, target: ManualDrillStep): string {
  const sx = source.x + source.w / 2;
  const sy = source.y + source.h;
  const tx = target.x + target.w / 2;
  const ty = target.y;
  if (Math.abs(sx - tx) < 36) return `M ${sx} ${sy} L ${tx} ${ty}`;
  const midY = sy + Math.max(24, (ty - sy) * 0.48);
  return `M ${sx} ${sy} L ${sx} ${midY} L ${tx} ${midY} L ${tx} ${ty}`;
}

const rootStyle: React.CSSProperties = {
  position: "absolute",
  inset: 0,
  display: "flex",
  flexDirection: "column",
  background: "#f8fafc",
  overflow: "hidden",
};

const topBarStyle: React.CSSProperties = {
  minHeight: 54,
  borderBottom: `1px solid ${PALETTE.rule}`,
  background: PALETTE.panel,
  padding: "8px 16px",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 12,
  flexShrink: 0,
};

const scrollAreaStyle: React.CSSProperties = { flex: 1, overflow: "auto", padding: "10px 0 24px" };
const diagramStyle: React.CSSProperties = {
  position: "relative",
  margin: "0 auto",
  background: "radial-gradient(circle at 1px 1px, #d9e1ea 1px, transparent 0)",
  backgroundSize: "22px 22px",
  borderLeft: `1px solid ${PALETTE.rule}`,
  borderRight: `1px solid ${PALETTE.rule}`,
};
const stageBandStyle: React.CSSProperties = { position: "absolute", left: 0, right: 0, borderTop: `1px solid ${PALETTE.rule}`, background: "rgba(255,255,255,0.58)" };
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
const nodeIconStyle: React.CSSProperties = { width: 27, height: 27, display: "inline-flex", alignItems: "center", justifyContent: "center", border: "1px solid", flexShrink: 0 };
const nodeStepStyle: React.CSSProperties = { display: "block", color: PALETTE.textMute, fontFamily: "'JetBrains Mono', monospace", fontSize: 8, letterSpacing: "0.1em", fontWeight: 800, textTransform: "uppercase" };
const nodeTitleStyle: React.CSSProperties = { display: "block", marginTop: 3, color: PALETTE.text, fontSize: 13, fontWeight: 800, lineHeight: 1.12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" };
const nodeMetaStyle: React.CSSProperties = { marginTop: 8, display: "grid", gap: 2, color: PALETTE.textDim, fontFamily: "'JetBrains Mono', monospace", fontSize: 8.5, overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis" };
const painBadgeStyle: React.CSSProperties = { marginTop: 7, display: "inline-block", maxWidth: "100%", color: "#92400e", background: "#fffbeb", border: "1px solid #fde68a", padding: "2px 6px", fontFamily: "'JetBrains Mono', monospace", fontSize: 8, fontWeight: 800, textTransform: "uppercase", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" };
const drillPanelStyle: React.CSSProperties = { border: `1px solid ${PALETTE.rule}`, borderTop: "4px solid #78716c", background: "rgba(255,255,255,0.96)", padding: 14, boxShadow: "0 18px 40px rgba(15,23,42,0.12)" };
const drillHeaderStyle: React.CSSProperties = { fontFamily: "'JetBrains Mono', monospace", fontSize: 9.5, letterSpacing: "0.13em", fontWeight: 800, color: PALETTE.textDim, textTransform: "uppercase" };
const manualDrillCanvasStyle: React.CSSProperties = { position: "relative", height: 812, marginTop: 10, background: "radial-gradient(circle at 1px 1px, #d9e1ea 1px, transparent 0)", backgroundSize: "20px 20px", overflow: "auto" };
const drillNodeStyle: React.CSSProperties = { position: "absolute", border: `1px solid ${PALETTE.rule}`, borderTop: "4px solid #78716c", borderRadius: 7, background: "#fffdfa", padding: 8, boxSizing: "border-box", overflow: "hidden", boxShadow: "0 4px 12px rgba(15,23,42,0.06)" };
const drillNodeTitleStyle: React.CSSProperties = { marginTop: 4, fontWeight: 800, fontSize: 12, lineHeight: 1.15, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" };
const drillNodeDetailStyle: React.CSSProperties = { marginTop: 4, color: PALETTE.textDim, fontSize: 10.5, lineHeight: 1.25, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" };
const hoverCardStyle: React.CSSProperties = { position: "absolute", width: 282, maxWidth: 282, border: `1px solid ${PALETTE.rule}`, borderTop: "4px solid", borderRadius: 8, background: "#ffffff", color: PALETTE.text, padding: 10, boxShadow: "0 18px 38px rgba(15,23,42,0.16)", pointerEvents: "none", fontFamily: "'Inter', system-ui, sans-serif", textAlign: "left" };
const hoverTitleStyle: React.CSSProperties = { fontSize: 12.5, fontWeight: 800, lineHeight: 1.25, marginBottom: 8 };
const hoverRowStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "78px 1fr", gap: 8, fontSize: 11, lineHeight: 1.32, color: PALETTE.textDim, marginTop: 5 };
const hoverLabelStyle: React.CSSProperties = { fontFamily: "'JetBrains Mono', monospace", fontSize: 8.5, letterSpacing: "0.08em", fontWeight: 800, color: PALETTE.textMute, textTransform: "uppercase" };
const eyebrowStyle: React.CSSProperties = { fontFamily: "'JetBrains Mono', monospace", fontSize: 10, letterSpacing: "0.18em", fontWeight: 800, color: "#78716c" };
const subtitleStyle: React.CSSProperties = { marginTop: 4, fontSize: 13, color: PALETTE.textDim };
const frictionSummaryStyle: React.CSSProperties = { display: "flex", gap: 6, flexWrap: "wrap", justifyContent: "flex-end" };
const painPillStyle: React.CSSProperties = { border: "1px solid #fde68a", background: "#fffbeb", color: "#92400e", padding: "4px 7px", fontFamily: "'JetBrains Mono', monospace", fontSize: 8.5, fontWeight: 800, textTransform: "uppercase" };
const focusedDrillStyle: React.CSSProperties = { width: "min(920px, calc(100% - 48px))", margin: "0 auto", display: "grid", gap: 12 };
const focusedHeaderStyle: React.CSSProperties = { display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, border: `1px solid ${PALETTE.rule}`, background: PALETTE.panel, padding: 12 };
const backButtonStyle: React.CSSProperties = { border: "1px solid #78716c", background: "#f5f5f4", color: "#44403c", padding: "7px 10px", cursor: "pointer", fontFamily: "'JetBrains Mono', monospace", fontSize: 9.5, letterSpacing: "0.08em", fontWeight: 800 };
const contractStripStyle: React.CSSProperties = { display: "flex", flexWrap: "wrap", gap: 8, border: `1px solid ${PALETTE.rule}`, background: "#fffdfa", padding: 10, color: PALETTE.textDim, fontFamily: "'JetBrains Mono', monospace", fontSize: 9.5 };

function EmptyState() {
  return (
    <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", color: PALETTE.textDim }}>
      <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, letterSpacing: "0.18em", fontWeight: 800 }}>AS-IS VIEW NOT CONFIGURED</div>
    </div>
  );
}
