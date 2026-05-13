import React, { useEffect, useState } from "react";
import { ChevronRight, Copy, Sparkles, X } from "lucide-react";

import { KIND_ICONS, PALETTE, getLayer } from "../theme";
import type { ProjectGraph, ProjectNode } from "../projectGraph/types";
import { loadSkillDetail, type SkillDetailResponse } from "../projectGraph/api";
import { Section } from "./primitives";
import { MarkdownView } from "./UiplanInspector";

const ORIGIN_COLORS: Record<string, { fg: string; bg: string; border: string }> = {
  "uipath-submodule": { fg: "#0f766e", bg: "#ccfbf1", border: "#5eead4" },
  user:               { fg: "#7c3aed", bg: "#f3e8ff", border: "#ddd6fe" },
  extension:          { fg: "#d97706", bg: "#fef3c7", border: "#fde68a" },
  cursor:             { fg: "#2563eb", bg: "#dbeafe", border: "#bfdbfe" },
};

function originStyle(origin: string) {
  return ORIGIN_COLORS[origin] ?? { fg: PALETTE.text, bg: PALETTE.bg, border: PALETTE.rule };
}

function skillIdFromNode(node: ProjectNode): string {
  return String(node.meta?.skill_id ?? node.label).replace(/^skill:/, "");
}

function matchedNodeIds(node: ProjectNode): string[] {
  const raw = node.meta?.matched_node_ids;
  if (!raw) return [];
  return String(raw).split(",").map((s) => s.trim()).filter(Boolean);
}

function splitList(raw: unknown, sep: string | RegExp): string[] {
  if (!raw) return [];
  return String(raw).split(sep).map((s) => s.trim()).filter(Boolean);
}

function compactText(value: string, max = 86): string {
  const cleaned = value.replace(/\s+/g, " ").trim();
  return cleaned.length > max ? `${cleaned.slice(0, max).trimEnd()}...` : cleaned;
}

function findNodeRecursive(nodes: ProjectNode[], id: string): ProjectNode | null {
  for (const n of nodes) {
    if (n.id === id) return n;
    if (n.children?.nodes) {
      const sub = findNodeRecursive(n.children.nodes, id);
      if (sub) return sub;
    }
  }
  return null;
}

interface SkillStoryPanelProps {
  skillNode: ProjectNode;
  rootGraph: ProjectGraph;
  onClose: () => void;
  onJumpToNode: (nodeId: string) => void;
}

function FlowStep({
  eyebrow, title, body, accent = "#8b5cf6",
}: {
  eyebrow: string;
  title: string;
  body: string;
  accent?: string;
}) {
  return (
    <div style={{
      position: "relative",
      padding: "10px 12px",
      background: PALETTE.bg,
      border: `1px solid ${PALETTE.rule}`,
      borderLeft: `3px solid ${accent}`,
      borderRadius: 5,
    }}>
      <div style={{
        fontSize: 8.5,
        letterSpacing: "0.16em",
        color: accent,
        fontFamily: "'JetBrains Mono', monospace",
        fontWeight: 700,
        textTransform: "uppercase",
      }}>
        {eyebrow}
      </div>
      <div style={{
        marginTop: 4,
        fontSize: 12,
        color: PALETTE.text,
        fontWeight: 700,
        lineHeight: 1.35,
      }}>
        {title}
      </div>
      <div style={{
        marginTop: 4,
        fontSize: 11,
        color: PALETTE.textDim,
        lineHeight: 1.45,
      }}>
        {body}
      </div>
    </div>
  );
}

function FlowArrow() {
  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "1fr auto 1fr",
      alignItems: "center",
      gap: 8,
      color: "#8b5cf6",
      padding: "1px 6px",
    }}>
      <div style={{ height: 1, background: "#ddd6fe" }} />
      <ChevronRight size={14} strokeWidth={2.2} />
      <div style={{ height: 1, background: "#ddd6fe" }} />
    </div>
  );
}

function SkillFlowDiagram({
  skillNode, description, triggers, usedByNodes, detail,
}: {
  skillNode: ProjectNode;
  description: string;
  triggers: string[];
  usedByNodes: ProjectNode[];
  detail: SkillDetailResponse | null;
}) {
  const firstTrigger = triggers[0] || "A user request or project file matches this skill.";
  const usage = usedByNodes.length > 0
    ? usedByNodes.slice(0, 3).map((n) => n.label).join(", ")
    : "No project nodes matched yet.";
  const usageSuffix = usedByNodes.length > 3 ? ` +${usedByNodes.length - 3} more` : "";

  // Enhanced visualization with metadata
  const capabilities = detail?.metadata?.capabilities || [];
  const guardrails = detail?.metadata?.guardrails || [];
  const outputs = detail?.metadata?.outputs || [];
  const services = detail?.metadata?.backing_services || [];

  return (
    <div style={{ marginTop: 22 }}>
      <Section label="FLOW" />
      <div style={{
        marginTop: 10,
        padding: 12,
        background: "linear-gradient(180deg, #faf5ff 0%, #ffffff 100%)",
        border: "1px solid #ddd6fe",
        borderRadius: 6,
      }}>
        <FlowStep
          eyebrow="trigger"
          title="When this applies"
          body={compactText(firstTrigger)}
        />
        <FlowArrow />
        <FlowStep
          eyebrow="skill"
          title={skillNode.label}
          body={compactText(description || "Guides the assistant with project-specific behavior.")}
          accent="#7c3aed"
        />
        {capabilities.length > 0 && (
          <>
            <FlowArrow />
            <FlowStep
              eyebrow="capabilities"
              title={`${capabilities.length} capability${capabilities.length === 1 ? "" : "ies"}`}
              body={compactText(capabilities.join(", "))}
              accent="#2563eb"
            />
          </>
        )}
        {outputs.length > 0 && (
          <>
            <FlowArrow />
            <FlowStep
              eyebrow="outputs"
              title="Produces"
              body={compactText(outputs.join(", "))}
              accent="#d97706"
            />
          </>
        )}
        <FlowArrow />
        <FlowStep
          eyebrow="project usage"
          title={`${usedByNodes.length} matched node${usedByNodes.length === 1 ? "" : "s"}`}
          body={compactText(`${usage}${usageSuffix}`)}
          accent="#0f766e"
        />
      </div>
      {(guardrails.length > 0 || services.length > 0 || triggers.length > 1) && (
        <div style={{
          marginTop: 8,
          fontSize: 10.5,
          color: PALETTE.textMute,
          fontFamily: "'JetBrains Mono', monospace",
          display: "flex",
          flexDirection: "column",
          gap: 4,
        }}>
          {guardrails.length > 0 && (
            <div>Guardrails: {guardrails.slice(0, 2).join(", ")}{guardrails.length > 2 ? ` +${guardrails.length - 2} more` : ""}</div>
          )}
          {services.length > 0 && (
            <div>Services: {services.slice(0, 2).join(", ")}{services.length > 2 ? ` +${services.length - 2} more` : ""}</div>
          )}
          {triggers.length > 1 && (
            <div>+ {triggers.length - 1} more trigger{triggers.length === 2 ? "" : "s"} below</div>
          )}
        </div>
      )}
    </div>
  );
}

export default function SkillStoryPanel({
  skillNode, rootGraph, onClose, onJumpToNode,
}: SkillStoryPanelProps) {
  const skillId = skillIdFromNode(skillNode);
  const [detail, setDetail] = useState<SkillDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(undefined);
    setDetail(null);
    loadSkillDetail(skillId).then((res) => {
      if (cancelled) return;
      setDetail(res.data);
      setError(res.error);
      setLoading(false);
    });
    return () => { cancelled = true; };
  }, [skillId]);

  const origin = String(detail?.origin ?? skillNode.meta?.origin ?? "");
  const oStyle = originStyle(origin);
  const coverage = Number(skillNode.meta?.coverage_count ?? 0);
  const path = String(detail?.path ?? skillNode.meta?.path ?? "");
  const description = detail?.description || skillNode.desc || "";

  const tags = detail?.tags?.length
    ? detail.tags
    : splitList(skillNode.meta?.tags, ",");
  const triggers = detail?.triggers?.length
    ? detail.triggers
    : splitList(skillNode.meta?.triggers, /[|,]/);

  const usedByIds = matchedNodeIds(skillNode);
  const usedByNodes = usedByIds
    .map((id) => findNodeRecursive(rootGraph.nodes, id))
    .filter(Boolean) as ProjectNode[];

  const copyPath = async () => {
    if (!path) return;
    try { await navigator.clipboard.writeText(path); } catch { /* noop */ }
  };

  return (
    <div style={{
      width: 420, background: PALETTE.panel,
      borderLeft: `1px solid ${PALETTE.rule}`,
      display: "flex", flexDirection: "column",
      overflow: "hidden", fontFamily: "'Inter', sans-serif",
      flexShrink: 0,
    }}>
      {/* Hero */}
      <div style={{
        padding: 18, borderBottom: `1px solid ${PALETTE.rule}`,
        background: "linear-gradient(180deg, #faf5ff 0%, #ffffff 100%)",
      }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 6,
            background: "#f3e8ff", border: "1px solid #ddd6fe",
            display: "flex", alignItems: "center", justifyContent: "center",
            flexShrink: 0,
          }}>
            <Sparkles size={18} color="#7c3aed" strokeWidth={1.8} />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              fontSize: 9, letterSpacing: "0.22em", color: "#7c3aed",
              fontWeight: 700, fontFamily: "'JetBrains Mono', monospace",
              marginBottom: 3,
            }}>
              SKILL · STORY
            </div>
            <div style={{
              fontSize: 16, color: PALETTE.text, fontWeight: 700,
              wordBreak: "break-word", lineHeight: 1.25,
            }}>
              {skillNode.label}
            </div>
          </div>
          <button
            onClick={onClose}
            title="Close skill story"
            style={{
              background: "transparent", border: "none", cursor: "pointer",
              padding: 6, color: PALETTE.textDim,
            }}
          >
            <X size={16} />
          </button>
        </div>

        <div style={{ marginTop: 10, display: "flex", gap: 6, flexWrap: "wrap" }}>
          {origin && (
            <span style={{
              fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
              letterSpacing: "0.1em", fontWeight: 700,
              color: oStyle.fg, background: oStyle.bg,
              border: `1px solid ${oStyle.border}`,
              padding: "3px 8px", borderRadius: 3,
            }}>
              {origin.toUpperCase()}
            </span>
          )}
          <span title="nodes covered" style={{
            fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
            letterSpacing: "0.1em", fontWeight: 700,
            color: "#7c3aed", background: "#f3e8ff",
            border: "1px solid #ddd6fe",
            padding: "3px 8px", borderRadius: 3,
          }}>
            ◆ {coverage} NODE{coverage === 1 ? "" : "S"}
          </span>
        </div>

        {path && (
          <button
            onClick={copyPath}
            title="Copy path"
            style={{
              marginTop: 10, width: "100%",
              display: "flex", alignItems: "center", gap: 8,
              background: PALETTE.bg,
              border: `1px solid ${PALETTE.rule}`,
              borderRadius: 4, padding: "7px 9px",
              cursor: "pointer",
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10.5, color: PALETTE.text,
              textAlign: "left",
            }}
          >
            <Copy size={11} color={PALETTE.textDim} />
            <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {path}
            </span>
          </button>
        )}
      </div>

      {/* Body */}
      <div style={{ flex: 1, overflowY: "auto", padding: 18 }}>
        {description && (
          <>
            <Section label="WHAT IT DOES" />
            <div style={{
              marginTop: 10, fontSize: 13, lineHeight: 1.6,
              color: PALETTE.text, fontWeight: 500,
            }}>
              {description}
            </div>
          </>
        )}

        <SkillFlowDiagram
          skillNode={skillNode}
          description={description}
          triggers={triggers}
          usedByNodes={usedByNodes}
          detail={detail}
        />

        {tags.length > 0 && (
          <div style={{ marginTop: 22 }}>
            <Section label="TAGS" />
            <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 6 }}>
              {tags.map((tag) => (
                <span key={tag} style={{
                  fontSize: 10, fontFamily: "'JetBrains Mono', monospace",
                  letterSpacing: "0.1em", fontWeight: 700,
                  color: "#7c3aed", background: "#f3e8ff",
                  border: "1px solid #ddd6fe", padding: "3px 8px", borderRadius: 3,
                }}>
                  {tag.toUpperCase()}
                </span>
              ))}
            </div>
          </div>
        )}

        {triggers.length > 0 && (
          <div style={{ marginTop: 22 }}>
            <Section label="TRIGGERS" count={triggers.length} />
            <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
              {triggers.map((t, i) => (
                <div key={i} style={{
                  padding: "7px 9px", background: PALETTE.bg,
                  border: `1px solid ${PALETTE.rule}`, borderLeft: "3px solid #8b5cf6",
                  borderRadius: 4, fontSize: 11.5, lineHeight: 1.45,
                }}>
                  {t}
                </div>
              ))}
            </div>
          </div>
        )}

        <div style={{ marginTop: 22 }}>
          <Section label="THE STORY" />
          {loading && (
            <div style={{
              marginTop: 10, padding: "10px 12px",
              background: PALETTE.bg, border: `1px solid ${PALETTE.rule}`,
              borderRadius: 4,
              fontFamily: "'JetBrains Mono', monospace", fontSize: 10.5,
              color: PALETTE.textMute, letterSpacing: "0.1em",
            }}>
              loading skill story…
            </div>
          )}
          {!loading && error && !detail?.body && (
            <div style={{
              marginTop: 10, padding: "10px 12px",
              background: "#fef2f2", border: "1px solid #fecaca",
              borderLeft: "3px solid #dc2626", borderRadius: 4,
              fontFamily: "'JetBrains Mono', monospace", fontSize: 10.5,
              color: "#991b1b",
            }}>
              Failed to load story · {error}
            </div>
          )}
          {!loading && detail?.body && (
            <div style={{ marginTop: 10 }}>
              <MarkdownView source={detail.body} />
            </div>
          )}
          {!loading && !error && !detail?.body && (
            <div style={{
              marginTop: 10, color: PALETTE.textMute, fontSize: 11,
              fontFamily: "'JetBrains Mono', monospace",
            }}>
              no skill body available
            </div>
          )}
        </div>

        {usedByNodes.length > 0 && (
          <div style={{ marginTop: 22 }}>
            <Section label="USED BY" count={usedByNodes.length} />
            <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
              {usedByNodes.map((match) => {
                const layer = getLayer(match.layer);
                const Icon = KIND_ICONS[match.kind];
                return (
                  <button
                    key={match.id}
                    onClick={() => onJumpToNode(match.id)}
                    style={{
                      display: "flex", alignItems: "center", gap: 10,
                      padding: "8px 10px", background: PALETTE.bg,
                      border: `1px solid ${PALETTE.rule}`,
                      borderLeft: `3px solid ${layer.color}`,
                      borderRadius: 4, cursor: "pointer", textAlign: "left",
                      fontFamily: "'Inter', sans-serif", color: PALETTE.text,
                    }}
                  >
                    {Icon && <Icon size={13} color={layer.color} strokeWidth={2} />}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{
                        fontSize: 12, color: PALETTE.text, fontWeight: 600,
                        overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                      }}>
                        {match.label}
                      </div>
                      <div style={{
                        fontSize: 9, color: layer.color,
                        fontFamily: "'JetBrains Mono', monospace",
                        letterSpacing: "0.14em", marginTop: 2,
                      }}>
                        {layer.short} · {match.kind.toUpperCase()}
                      </div>
                    </div>
                    <ChevronRight size={12} style={{ color: PALETTE.textMute }} />
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
