import React from "react";
import { ExternalLink, Sparkles, Target, Users, Workflow, Zap } from "lucide-react";

import { PALETTE } from "../theme";
import type { ProjectGraph } from "../projectGraph/types";
import { Section } from "./primitives";

interface ProjectOverviewProps {
  graph: ProjectGraph;
  onClose?: () => void;
}

/**
 * BA-shaped project overview, shown in the inspector slot when nothing is
 * selected. Pulls from `graph.overview` (project-level) and aggregates a few
 * canvas-derived numbers (HITL gates, exception edges, error count).
 */
export default function ProjectOverview({ graph }: ProjectOverviewProps) {
  const overview = graph.overview;

  const hitlCount = graph.nodes.filter(
    (n) => n.roles?.includes("hitl") || n.roles?.includes("approval"),
  ).length;
  const exceptionEdges = graph.edges.filter((e) => e.path_class === "exception").length;
  const issueCount = graph.errors?.length ?? 0;

  if (!overview) {
    return (
      <div style={{ padding: 22, fontFamily: "'Inter', sans-serif", color: PALETTE.textDim }}>
        <Section label="PROJECT" />
        <div style={{ marginTop: 12, fontSize: 13, lineHeight: 1.55, fontFamily: "'Newsreader', Georgia, serif", fontStyle: "italic" }}>
          No project overview captured for this worktree. Add an{" "}
          <code style={{ background: PALETTE.bg, border: `1px solid ${PALETTE.rule}`, padding: "1px 5px", borderRadius: 3, fontSize: 12 }}>
            overview
          </code>{" "}
          block to the project graph to surface name, owner, triggers, actors, and KPIs here.
        </div>
        <div style={{ marginTop: 22 }}>
          <Section label="CANVAS · AGGREGATE" />
          {renderAggregate(graph.nodes.length, graph.edges.length, hitlCount, exceptionEdges, issueCount)}
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: 22, fontFamily: "'Inter', sans-serif", overflowY: "auto" }}>
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 12, letterSpacing: "0.22em", fontWeight: 700,
        color: PALETTE.textDim, marginBottom: 6,
      }}>
        PROJECT
      </div>
      <div style={{
        fontSize: 18, fontWeight: 700, color: PALETTE.text, lineHeight: 1.2,
        letterSpacing: "-0.01em",
      }}>
        {overview.name}
      </div>
      {overview.owner && (
        <div style={{ marginTop: 4, fontSize: 12, color: PALETTE.textDim, fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.05em" }}>
          owner&nbsp;·&nbsp;<span style={{ color: PALETTE.text, fontWeight: 600 }}>{overview.owner}</span>
        </div>
      )}

      <div style={{
        marginTop: 14, fontSize: 13, lineHeight: 1.6,
        fontFamily: "'Newsreader', Georgia, serif",
        color: PALETTE.text,
      }}>
        {overview.summary}
      </div>

      {overview.kpis && overview.kpis.length > 0 && (
        <div style={{ marginTop: 22 }}>
          <Section label="KPIS" />
          <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            {overview.kpis.map((k, i) => (
              <div key={i} style={{
                background: PALETTE.bg, border: `1px solid ${PALETTE.rule}`,
                borderLeft: `3px solid #059669`,
                padding: "8px 10px", borderRadius: 4,
              }}>
                <div style={{ fontSize: 12, letterSpacing: "0.15em", color: PALETTE.textDim, fontFamily: "'JetBrains Mono', monospace", fontWeight: 600 }}>
                  {k.label.toUpperCase()}
                </div>
                <div style={{ fontSize: 14, color: PALETTE.text, fontWeight: 700, marginTop: 2 }}>
                  {k.value}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {overview.triggers && overview.triggers.length > 0 && (
        <div style={{ marginTop: 22 }}>
          <Section label="TRIGGERS" count={overview.triggers.length} />
          <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
            {overview.triggers.map((t, i) => (
              <div key={i} style={{
                display: "flex", alignItems: "flex-start", gap: 10,
                padding: "8px 10px", background: PALETTE.bg,
                border: `1px solid ${PALETTE.rule}`, borderLeft: `3px solid #2563eb`,
                borderRadius: 4,
              }}>
                <Zap size={13} color="#2563eb" style={{ flexShrink: 0, marginTop: 2 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12, color: "#2563eb", fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.15em", fontWeight: 700 }}>
                    {t.kind.toUpperCase()}
                  </div>
                  <div style={{ fontSize: 12, color: PALETTE.text, lineHeight: 1.4, marginTop: 2 }}>
                    {t.description}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {overview.actors && overview.actors.length > 0 && (
        <div style={{ marginTop: 22 }}>
          <Section label="ACTORS" count={overview.actors.length} />
          <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 4 }}>
            {overview.actors.map((a, i) => (
              <div key={i} style={{
                display: "flex", alignItems: "center", gap: 10,
                padding: "6px 10px", background: PALETTE.bg,
                border: `1px solid ${PALETTE.rule}`, borderRadius: 4,
              }}>
                <Users size={12} color={PALETTE.textDim} />
                <span style={{ fontSize: 12, color: PALETTE.text, fontWeight: 600 }}>{a.name}</span>
                <span style={{ marginLeft: "auto", fontSize: 12, color: PALETTE.textDim, fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.1em" }}>
                  {a.role}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {overview.stakeholders && overview.stakeholders.length > 0 && (
        <div style={{ marginTop: 22 }}>
          <Section label="STAKEHOLDERS" />
          <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 6 }}>
            {overview.stakeholders.map((s) => (
              <span key={s} style={{
                fontSize: 12, color: PALETTE.text, fontWeight: 500,
                padding: "4px 9px", background: PALETTE.bg,
                border: `1px solid ${PALETTE.rule}`, borderRadius: 12,
              }}>
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      <div style={{ marginTop: 22 }}>
        <Section label="CANVAS · AGGREGATE" />
        {renderAggregate(graph.nodes.length, graph.edges.length, hitlCount, exceptionEdges, issueCount)}
      </div>

      {overview.pdd && (
        <div style={{ marginTop: 22 }}>
          <Section label="PDD" />
          <div style={{
            marginTop: 10, padding: "10px 12px",
            background: PALETTE.bg, border: `1px solid ${PALETTE.rule}`,
            borderLeft: `3px solid #7c3aed`, borderRadius: 4,
            display: "flex", alignItems: "center", gap: 10,
          }}>
            <Target size={13} color="#7c3aed" />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 12, color: "#7c3aed", fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.1em", fontWeight: 700 }}>
                {overview.pdd.doc_id}
              </div>
              <div style={{ fontSize: 12, color: PALETTE.text, marginTop: 2 }}>{overview.pdd.section}</div>
            </div>
            {overview.pdd.path && (
              <span style={{ fontSize: 12, color: PALETTE.textDim, fontFamily: "'JetBrains Mono', monospace" }}>
                {overview.pdd.path}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function renderAggregate(nodes: number, edges: number, hitl: number, exceptions: number, issues: number) {
  const cells: Array<{ label: string; value: string; color: string; Icon: React.ComponentType<{ size?: number; color?: string; strokeWidth?: number }> }> = [
    { label: "nodes",      value: String(nodes),      color: PALETTE.text, Icon: Workflow },
    { label: "edges",      value: String(edges),      color: PALETTE.text, Icon: ExternalLink },
    { label: "hitl gates", value: String(hitl),       color: hitl > 0 ? "#dc2626" : PALETTE.text, Icon: Sparkles },
    { label: "exceptions", value: String(exceptions), color: exceptions > 0 ? "#d97706" : PALETTE.text, Icon: Sparkles },
    { label: "issues",     value: String(issues),     color: issues > 0 ? "#dc2626" : PALETTE.text, Icon: Sparkles },
  ];
  return (
    <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
      {cells.map((c) => (
        <div key={c.label} style={{
          background: PALETTE.bg, border: `1px solid ${PALETTE.rule}`,
          padding: "7px 10px", borderRadius: 4,
          display: "flex", alignItems: "center", gap: 8,
        }}>
          <c.Icon size={11} color={PALETTE.textDim} />
          <span style={{ fontSize: 12, color: PALETTE.textDim, fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.1em", flex: 1 }}>
            {c.label}
          </span>
          <span style={{ fontSize: 13, color: c.color, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>
            {c.value}
          </span>
        </div>
      ))}
    </div>
  );
}
