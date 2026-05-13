import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  Book,
  ChevronRight,
  ExternalLink,
  FileText,
  Maximize2,
  PanelRightClose,
  PanelRightOpen,
  Sparkles,
} from "lucide-react";

import {
  BUSINESS_STATUS_COLOR,
  KIND_ICONS,
  PALETTE,
  STATUS_COLOR,
  getEdgeStyle,
  getLayer,
} from "../theme";
import type {
  DocCitation,
  ProjectEdge,
  ProjectGraph,
  ProjectNode,
  SkillRef,
} from "../projectGraph/types";
import {
  loadLibrarySection,
  loadNodeKnowledge,
  loadSkillDetail,
  type SkillDetailResponse,
  openInEditor,
} from "../projectGraph/api";
import { Section, SyntaxHighlight } from "./primitives";
import ProjectOverview from "./ProjectOverview";
import { MarkdownView, UiplanProgressPanel, UiplanTaskPanel } from "./UiplanInspector";
import SkillStoryPanel from "./SkillStoryPanel";

type InspectorTab = "overview" | "code" | "knowledge" | "links" | "notes";

function Tab({ active, onClick, children, count }: { active: boolean; onClick: () => void; children: React.ReactNode; count?: number }) {
  return (
    <button onClick={onClick} style={{
      flex: 1, padding: "12px 6px",
      background: active ? PALETTE.panel : "transparent",
      border: "none",
      borderBottom: `2px solid ${active ? PALETTE.ink : "transparent"}`,
      color: active ? PALETTE.text : PALETTE.textDim,
      cursor: "pointer", fontSize: 12,
      fontFamily: "'JetBrains Mono', monospace",
      letterSpacing: "0.08em", fontWeight: active ? 700 : 600,
      transition: "all 0.15s",
      display: "flex", alignItems: "center", justifyContent: "center", gap: 5,
    }}>
      {children}
      {count !== undefined && count > 0 && (
        <span style={{ fontSize: 12, color: PALETTE.textMute, background: PALETTE.bg, padding: "1px 5px", borderRadius: 8, fontWeight: 500 }}>
          {count}
        </span>
      )}
    </button>
  );
}

function CitationItem({ c }: { c: DocCitation }) {
  const [expanded, setExpanded] = useState(false);
  const [body, setBody] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | undefined>();

  const toggle = async () => {
    if (expanded) { setExpanded(false); return; }
    setExpanded(true);
    if (body !== null) return;
    setLoading(true);
    const res = await loadLibrarySection(c.book_id, c.chapter_id, c.section_id);
    setLoading(false);
    if (res.data) setBody(res.data.body);
    else setError(res.error || "section not available");
  };

  return (
    <div style={{
      background: PALETTE.bg,
      border: `1px solid ${PALETTE.rule}`,
      borderLeft: `3px solid #2563eb`,
      borderRadius: 4, fontFamily: "'Inter', sans-serif",
      overflow: "hidden",
    }}>
      <button onClick={toggle} style={{
        all: "unset", display: "block", width: "100%", cursor: "pointer",
        padding: "10px 12px", boxSizing: "border-box",
      }}>
        <div style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 12, color: PALETTE.textDim, letterSpacing: "0.08em",
          marginBottom: 4, display: "flex", alignItems: "center", gap: 6,
        }}>
          <Book size={11} color="#2563eb" />
          <span style={{ color: "#2563eb", fontWeight: 700 }}>{c.book_id}</span>
          <span>/ {c.chapter_id} / {c.section_id}</span>
          {c.score !== undefined && (
            <span style={{ marginLeft: "auto", fontSize: 12, color: PALETTE.textMute }}>
              score {c.score}
            </span>
          )}
        </div>
        <div style={{ fontSize: 12, color: PALETTE.text, lineHeight: 1.5 }}>{c.snippet}</div>
        <div style={{
          marginTop: 6, fontSize: 12, fontFamily: "'JetBrains Mono', monospace",
          color: PALETTE.textMute, letterSpacing: "0.12em",
        }}>
          {expanded ? "▾ COLLAPSE" : "▸ READ FULL SECTION"}
        </div>
      </button>
      {expanded && (
        <div style={{
          padding: "10px 12px", borderTop: `1px dashed ${PALETTE.rule}`,
          background: PALETTE.panel, fontSize: 12, lineHeight: 1.55, color: PALETTE.text,
          maxHeight: 320, overflowY: "auto",
          fontFamily: "'Newsreader', Georgia, serif",
        }}>
          {loading && (
            <div style={{ color: PALETTE.textMute, fontStyle: "italic", fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>
              loading section…
            </div>
          )}
          {error && (
            <div style={{ color: "#92400e", fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>
              {error}
            </div>
          )}
          {body !== null && (
            <pre style={{
              margin: 0, whiteSpace: "pre-wrap",
              fontFamily: "'Newsreader', Georgia, serif",
              fontSize: 12, lineHeight: 1.6,
            }}>{body}</pre>
          )}
          {c.href && (
            <a href={c.href} target="_blank" rel="noreferrer" style={{
              display: "inline-flex", alignItems: "center", gap: 4,
              marginTop: 8, fontSize: 12,
              fontFamily: "'JetBrains Mono', monospace",
              color: "#2563eb", textDecoration: "none", letterSpacing: "0.1em",
            }}>
              <ExternalLink size={10} /> OPEN IN BROWSER
            </a>
          )}
        </div>
      )}
    </div>
  );
}

function SkillItem({ s, onOpenStory }: { s: SkillRef; onOpenStory?: (skillNodeId: string) => void }) {
  return (
    <div style={{
      padding: "10px 12px",
      background: PALETTE.bg,
      border: `1px solid ${PALETTE.rule}`,
      borderLeft: `3px solid #7c3aed`,
      borderRadius: 4, fontFamily: "'Inter', sans-serif",
    }}>
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 12, letterSpacing: "0.08em",
        marginBottom: 4, display: "flex", alignItems: "center", gap: 6,
      }}>
        <Sparkles size={11} color="#7c3aed" />
        <span style={{ color: "#7c3aed", fontWeight: 700 }}>{s.id}</span>
        {onOpenStory && (
          <button
            onClick={() => onOpenStory(`skill:${s.id}`)}
            style={{
              marginLeft: "auto", background: "transparent", border: "none",
              color: "#0f766e", cursor: "pointer", padding: 0,
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 12, fontWeight: 700, letterSpacing: "0.12em",
            }}
          >
            OPEN STORY →
          </button>
        )}
      </div>
      <div style={{ fontSize: 12, color: PALETTE.textDim, marginBottom: 4, fontFamily: "'JetBrains Mono', monospace" }}>
        {s.path}
      </div>
      {s.reason && <div style={{ fontSize: 12, color: PALETTE.text, lineHeight: 1.5 }}>{s.reason}</div>}
    </div>
  );
}

function skillIdFromNode(node: ProjectNode): string {
  return String(node.meta?.skill_id ?? node.label).replace(/^skill:/, "");
}

function matchedNodeIds(node: ProjectNode): string[] {
  const raw = node.meta?.matched_node_ids;
  if (!raw) return [];
  return String(raw).split(",").map((s) => s.trim()).filter(Boolean);
}

function SkillOverviewTab({ node, detail }: { node: ProjectNode; detail: SkillDetailResponse | null }) {
  const tags = detail?.tags?.length ? detail.tags : String(node.meta?.tags ?? "").split(",").map((s) => s.trim()).filter(Boolean);
  const triggers = detail?.triggers?.length ? detail.triggers : String(node.meta?.triggers ?? "").split("|").map((s) => s.trim()).filter(Boolean);
  return (
    <div style={{ padding: 18, fontFamily: "'Inter', sans-serif" }}>
      <Section label="WHAT THIS SKILL DOES" />
      <div style={{ marginTop: 10, fontSize: 13, lineHeight: 1.6, color: PALETTE.text, fontWeight: 500 }}>
        {detail?.description || node.desc || "No description available for this skill."}
      </div>

      <div style={{ marginTop: 22 }}>
        <Section label="PROJECT COVERAGE" />
        <div style={{
          marginTop: 10, padding: "10px 12px", background: "#faf5ff",
          border: "1px solid #ddd6fe", borderLeft: "3px solid #8b5cf6",
          borderRadius: 4, fontFamily: "'JetBrains Mono', monospace",
          fontSize: 12, lineHeight: 1.8,
        }}>
          <div><span style={{ color: PALETTE.textDim }}>matched nodes&nbsp;</span><span style={{ color: PALETTE.text, fontWeight: 700 }}>{String(node.meta?.coverage_count ?? matchedNodeIds(node).length)}</span></div>
          {node.meta?.origin && <div><span style={{ color: PALETTE.textDim }}>origin&nbsp;</span><span style={{ color: PALETTE.text, fontWeight: 700 }}>{String(node.meta.origin)}</span></div>}
          {detail?.path || node.meta?.path ? <div style={{ wordBreak: "break-all" }}><span style={{ color: PALETTE.textDim }}>path&nbsp;</span><span style={{ color: PALETTE.text }}>{detail?.path ?? String(node.meta?.path)}</span></div> : null}
        </div>
      </div>

      {tags.length > 0 && (
        <div style={{ marginTop: 22 }}>
          <Section label="TAGS" />
          <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 6 }}>
            {tags.map((tag) => (
              <span key={tag} style={{
                fontSize: 12, fontFamily: "'JetBrains Mono', monospace",
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
          <Section label="WHEN TO USE" count={triggers.length} />
          <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
            {triggers.slice(0, 8).map((trigger, i) => (
              <div key={i} style={{
                padding: "7px 9px", background: PALETTE.bg,
                border: `1px solid ${PALETTE.rule}`, borderLeft: "3px solid #8b5cf6",
                borderRadius: 4, fontSize: 12, lineHeight: 1.45,
              }}>
                {trigger}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function SkillBodyTab({ skillId }: { skillId: string }) {
  const [detail, setDetail] = useState<SkillDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(undefined);
    loadSkillDetail(skillId).then((res) => {
      if (cancelled) return;
      setDetail(res.data);
      setError(res.error);
      setLoading(false);
    });
    return () => { cancelled = true; };
  }, [skillId]);

  return (
    <div style={{ padding: 18, fontFamily: "'Inter', sans-serif" }}>
      <Section label="SKILL.md" />
      {loading && (
        <div style={{ marginTop: 10, color: PALETTE.textMute, fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>
          loading skill context...
        </div>
      )}
      {error && (
        <div style={{ marginTop: 10, color: "#92400e", fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>
          {error}
        </div>
      )}
      {detail?.body && (
        <pre style={{
          margin: "10px 0 0", whiteSpace: "pre-wrap",
          fontFamily: "'Newsreader', Georgia, serif",
          fontSize: 12.5, lineHeight: 1.65, color: PALETTE.text,
        }}>
          {detail.body}
        </pre>
      )}
      {!loading && !detail?.body && !error && (
        <div style={{ marginTop: 10, color: PALETTE.textMute, fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>
          no skill body available
        </div>
      )}
    </div>
  );
}

function SkillCoverageTab({ node, graph, onSelectNode }: {
  node: ProjectNode;
  graph: ProjectGraph;
  onSelectNode: (id: string) => void;
}) {
  const ids = matchedNodeIds(node);
  const matched = ids
    .map((id) => graph.nodes.find((n) => n.id === id))
    .filter(Boolean) as ProjectNode[];
  return (
    <div style={{ padding: 18 }}>
      <Section label="TOP MATCHED NODES" count={matched.length} />
      <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
        {matched.length === 0 ? (
          <div style={{ color: PALETTE.textMute, fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>
            no coverage nodes attached
          </div>
        ) : matched.map((match) => {
          const layer = getLayer(match.layer);
          const Icon = KIND_ICONS[match.kind];
          return (
            <button
              key={match.id}
              onClick={() => onSelectNode(match.id)}
              style={{
                display: "flex", alignItems: "center", gap: 10,
                padding: "9px 10px", background: PALETTE.bg,
                border: `1px solid ${PALETTE.rule}`,
                borderLeft: `3px solid ${layer.color}`,
                borderRadius: 4, cursor: "pointer", textAlign: "left",
                fontFamily: "'Inter', sans-serif", color: PALETTE.text,
              }}
            >
              {Icon && <Icon size={13} color={layer.color} strokeWidth={2} />}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12, color: PALETTE.text, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {match.label}
                </div>
                <div style={{ fontSize: 12, color: layer.color, fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.14em", marginTop: 2 }}>
                  {layer.short} · {match.kind.toUpperCase()}
                </div>
              </div>
              <ChevronRight size={12} style={{ color: PALETTE.textMute }} />
            </button>
          );
        })}
      </div>
      <div style={{ marginTop: 12, fontSize: 12, color: PALETTE.textDim, lineHeight: 1.5 }}>
        Coverage is capped to the top 3 nodes per skill so the canvas stays readable.
      </div>
    </div>
  );
}

function OverviewTab({ node, graph }: { node: ProjectNode; graph: ProjectGraph }) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const errors = graph.errors?.filter((e) => e.nodeId === node.id) || [];
  return (
    <div style={{ padding: 18, fontFamily: "'Inter', sans-serif" }}>
      {/* Business strip — only renders when BA fields are present */}
      {(node.business_status || node.business_meta) && (
        <div style={{
          padding: "10px 12px", marginBottom: 16,
          background: PALETTE.bg, border: `1px solid ${PALETTE.rule}`,
          borderLeft: `3px solid ${BUSINESS_STATUS_COLOR[node.business_status ?? "drafted"]}`,
          borderRadius: 4,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 12, letterSpacing: "0.18em", fontWeight: 700,
              color: BUSINESS_STATUS_COLOR[node.business_status ?? "drafted"],
            }}>
              {(node.business_status ?? "DRAFTED").toUpperCase()}
            </span>
            {node.business_meta?.risk && (
              <span style={{
                fontSize: 12, fontFamily: "'JetBrains Mono', monospace",
                letterSpacing: "0.1em", fontWeight: 700,
                padding: "2px 6px", borderRadius: 3,
                color: node.business_meta.risk === "high" ? "#dc2626" : node.business_meta.risk === "medium" ? "#d97706" : "#059669",
                background: node.business_meta.risk === "high" ? "#fee2e2" : node.business_meta.risk === "medium" ? "#fef3c7" : "#d1fae5",
              }}>
                {node.business_meta.risk.toUpperCase()} RISK
              </span>
            )}
          </div>
          {node.business_meta && (
            <div style={{ marginTop: 8, display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 12px", fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>
              {node.business_meta.owner  && <div><span style={{ color: PALETTE.textDim }}>owner&nbsp;</span><span style={{ color: PALETTE.text, fontWeight: 600 }}>{node.business_meta.owner}</span></div>}
              {node.business_meta.volume && <div><span style={{ color: PALETTE.textDim }}>volume&nbsp;</span><span style={{ color: PALETTE.text, fontWeight: 600 }}>{node.business_meta.volume}</span></div>}
              {node.business_meta.sla    && <div style={{ gridColumn: "span 2" }}><span style={{ color: PALETTE.textDim }}>sla&nbsp;</span><span style={{ color: PALETTE.text, fontWeight: 600 }}>{node.business_meta.sla}</span></div>}
            </div>
          )}
          {node.business_meta?.value && (
            <div style={{ marginTop: 8, fontSize: 12, color: PALETTE.text, lineHeight: 1.5, fontFamily: "'Newsreader', Georgia, serif", fontStyle: "italic" }}>
              {node.business_meta.value}
            </div>
          )}
        </div>
      )}

      {node.desc && (
        <>
          <Section label="SUMMARY" />
          <div style={{ marginTop: 10, fontSize: 13, lineHeight: 1.55, color: PALETTE.text, fontWeight: 500 }}>
            {node.desc}
          </div>
        </>
      )}

      {node.concept && (
        <div style={{ marginTop: 22 }}>
          <Section label="CONCEPT" />
          <div style={{ marginTop: 10, fontSize: 13, lineHeight: 1.65, color: PALETTE.text, fontFamily: "'Newsreader', Georgia, serif" }}>
            {node.concept}
          </div>
        </div>
      )}

      {node.pdd_anchor && (
        <div style={{ marginTop: 22 }}>
          <Section label="PDD ANCHOR" />
          <div style={{
            marginTop: 10, padding: "8px 12px",
            background: PALETTE.bg, border: `1px solid ${PALETTE.rule}`,
            borderLeft: `3px solid #7c3aed`, borderRadius: 4,
            fontFamily: "'JetBrains Mono', monospace", fontSize: 12,
          }}>
            <span style={{ color: "#7c3aed", fontWeight: 700 }}>{node.pdd_anchor.doc_id}</span>
            <span style={{ color: PALETTE.text }}> · {node.pdd_anchor.section}</span>
            {node.pdd_anchor.path && (
              <div style={{ marginTop: 3, color: PALETTE.textDim }}>{node.pdd_anchor.path}</div>
            )}
          </div>
        </div>
      )}

      {node.roles && node.roles.length > 0 && (
        <div style={{ marginTop: 22 }}>
          <Section label="ROLES" />
          <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 6 }}>
            {node.roles.map((r) => (
              <span key={r} style={{
                fontSize: 12, fontFamily: "'JetBrains Mono', monospace",
                letterSpacing: "0.1em", fontWeight: 700,
                color: r === "hitl" || r === "approval" ? "#dc2626" : PALETTE.text,
                background: r === "hitl" || r === "approval" ? "#fee2e2" : PALETTE.bg,
                border: `1px solid ${r === "hitl" || r === "approval" ? "#fecaca" : PALETTE.rule}`,
                padding: "3px 8px", borderRadius: 3,
              }}>
                {r.toUpperCase()}
              </span>
            ))}
          </div>
        </div>
      )}

      {errors.length > 0 && (
        <div style={{ marginTop: 22 }}>
          <Section label="ISSUES" count={errors.length} />
          <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
            {errors.map((e, i) => (
              <div key={i} style={{
                display: "flex", alignItems: "flex-start", gap: 8, padding: "8px 10px",
                background: e.severity === "error" ? "#fef2f2" : e.severity === "warn" ? "#fffbeb" : "#eff6ff",
                border: `1px solid ${e.severity === "error" ? "#fecaca" : e.severity === "warn" ? "#fde68a" : "#bfdbfe"}`,
                borderLeft: `3px solid ${e.severity === "error" ? "#dc2626" : e.severity === "warn" ? "#d97706" : "#2563eb"}`,
                borderRadius: 4,
              }}>
                <AlertTriangle size={12} color={e.severity === "error" ? "#dc2626" : e.severity === "warn" ? "#d97706" : "#2563eb"} style={{ flexShrink: 0, marginTop: 1 }} />
                <div style={{ fontSize: 12, lineHeight: 1.5, color: e.severity === "error" ? "#991b1b" : e.severity === "warn" ? "#92400e" : "#1e40af" }}>
                  {e.message}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {node.meta && Object.keys(node.meta).length > 0 && (
        <div style={{ marginTop: 22 }}>
          <Section label="ADVANCED DETAILS" />
          <button
            onClick={() => setShowAdvanced((v) => !v)}
            style={{
              marginTop: 10,
              width: "100%",
              border: `1px solid ${PALETTE.rule}`,
              borderRadius: 8,
              background: PALETTE.bg,
              color: PALETTE.textDim,
              padding: "8px 10px",
              cursor: "pointer",
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 12,
              letterSpacing: "0.06em",
              fontWeight: 700,
            }}
          >
            {showAdvanced ? "HIDE TECHNICAL META" : "SHOW TECHNICAL META"}
          </button>
          {showAdvanced && (
            <div style={{ marginTop: 10, fontSize: 12, lineHeight: 1.9, fontFamily: "'JetBrains Mono', monospace" }}>
              {Object.entries(node.meta).map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "3px 0", borderBottom: `1px dashed ${PALETTE.ruleSoft}` }}>
                  <span style={{ color: PALETTE.textDim }}>{k}</span>
                  <span style={{ color: PALETTE.text }}>{String(v)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function CodeTab({ node }: { node: ProjectNode }) {
  if (!node.code) {
    return (
      <div style={{ padding: 18, color: PALETTE.textMute, fontSize: 12, fontFamily: "'Inter', sans-serif" }}>
        No code reference attached to this node.
      </div>
    );
  }
  const layer = getLayer(node.layer);
  return (
    <div style={{ padding: 18, fontFamily: "'JetBrains Mono', monospace" }}>
      <Section label="LOCATION" />
      <div style={{
        marginTop: 10, padding: "10px 12px",
        background: PALETTE.bg, border: `1px solid ${PALETTE.rule}`,
        borderRadius: 4, display: "flex", alignItems: "center", gap: 8,
      }}>
        <FileText size={13} color={layer.color} strokeWidth={2} />
        <div style={{ flex: 1, fontSize: 12, color: PALETTE.text, wordBreak: "break-all" }}>
          {node.code.path}
        </div>
        {node.code.lines && (
          <div style={{ fontSize: 12, color: PALETTE.textDim, background: PALETTE.panel, padding: "2px 7px", borderRadius: 3, border: `1px solid ${PALETTE.rule}`, letterSpacing: "0.05em" }}>
            L {node.code.lines}
          </div>
        )}
      </div>

      {node.code.snippet && (
        <div style={{ marginTop: 18 }}>
          <Section label="SNIPPET" />
          <div style={{ marginTop: 10, background: "#1e1e1e", border: `1px solid ${PALETTE.rule}`, borderRadius: 6, overflow: "hidden" }}>
            <div style={{ padding: "6px 12px", borderBottom: "1px solid #2d2d2d", fontSize: 12, letterSpacing: "0.2em", color: "#858585", fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
              <div style={{ display: "flex", gap: 4 }}>
                <div style={{ width: 7, height: 7, borderRadius: "50%", background: "#ff5f57" }} />
                <div style={{ width: 7, height: 7, borderRadius: "50%", background: "#febc2e" }} />
                <div style={{ width: 7, height: 7, borderRadius: "50%", background: "#28c840" }} />
              </div>
              <span style={{ marginLeft: 6 }}>{node.code.path.split("/").pop()}</span>
            </div>
            <pre style={{ margin: 0, padding: "12px 14px", fontSize: 12, lineHeight: 1.55, color: "#d4d4d4", fontFamily: "'JetBrains Mono', monospace", overflowX: "auto", whiteSpace: "pre" }}>
              <SyntaxHighlight code={node.code.snippet} />
            </pre>
          </div>
        </div>
      )}

      <div style={{ marginTop: 14 }}>
        <button
          onClick={() => {
            const lineMatch = node.code?.lines?.match(/^(\d+)/);
            const line = lineMatch ? parseInt(lineMatch[1], 10) : undefined;
            openInEditor(node.code!.path, line);
          }}
          style={{
            width: "100%", padding: "9px 12px",
            background: PALETTE.panel,
            border: `1px solid ${PALETTE.rule}`,
            borderRadius: 4, cursor: "pointer",
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 12, fontWeight: 700, letterSpacing: "0.15em",
            color: PALETTE.text,
            display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
          }}>
          <ExternalLink size={12} />
          OPEN IN EDITOR
        </button>
      </div>
    </div>
  );
}

function KnowledgeTab({ node, sourcePath, onOpenStory }: {
  node: ProjectNode;
  sourcePath: string;
  onOpenStory?: (skillNodeId: string) => void;
}) {
  const inlineCitations = node.citations ?? [];
  const inlineSkills = node.skills ?? [];

  const [liveCitations, setLiveCitations] = useState<DocCitation[]>([]);
  const [liveSkills, setLiveSkills] = useState<SkillRef[]>([]);
  const [loading, setLoading] = useState(false);
  const [source, setSource] = useState<"inline" | "api">("inline");
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(undefined);
    loadNodeKnowledge(sourcePath, node.id, node.label).then((res) => {
      if (cancelled) return;
      setLiveCitations(res.data.citations);
      setLiveSkills(res.data.skills);
      setSource(res.source);
      setError(res.error);
      setLoading(false);
    });
    return () => { cancelled = true; };
  }, [sourcePath, node.id, node.label]);

  const allCitations = [...inlineCitations, ...liveCitations];
  const allSkills = [...inlineSkills, ...liveSkills];

  return (
    <div style={{ padding: 18, fontFamily: "'Inter', sans-serif" }}>
      <div style={{
        marginBottom: 14,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 12, letterSpacing: "0.18em", color: PALETTE.textMute,
        display: "flex", alignItems: "center", gap: 6,
      }}>
        SOURCE&nbsp;·&nbsp;
        <span style={{ color: source === "api" ? "#059669" : "#d97706", fontWeight: 700 }}>
          {loading ? "LOADING…" : source === "api" ? "LIVE" : "INLINE"}
        </span>
        {error && <span style={{ color: "#dc2626", marginLeft: 8 }}>· {error}</span>}
      </div>

      <Section label="DOCUMENTATION" count={allCitations.length} />
      <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 8 }}>
        {allCitations.length === 0 ? (
          <div style={{ fontSize: 12, color: PALETTE.textMute, fontFamily: "'JetBrains Mono', monospace" }}>
            ∅ no citations linked to this node yet
          </div>
        ) : (
          allCitations.map((c, i) => <CitationItem key={`${c.book_id}-${c.section_id}-${i}`} c={c} />)
        )}
      </div>

      <div style={{ marginTop: 22 }}>
        <Section label="SKILLS" count={allSkills.length} />
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 8 }}>
          {allSkills.length === 0 ? (
            <div style={{ fontSize: 12, color: PALETTE.textMute, fontFamily: "'JetBrains Mono', monospace" }}>
              ∅ no skills referenced for this node
            </div>
          ) : (
            allSkills.map((s, i) => <SkillItem key={`${s.id}-${i}`} s={s} onOpenStory={onOpenStory} />)
          )}
        </div>
      </div>
    </div>
  );
}

function NotesTab({ node }: { node: ProjectNode }) {
  const [note, setNote] = useState(() => {
    try {
      return localStorage.getItem(`uiplan:notes:${node.id}`) || "";
    } catch {
      return "";
    }
  });

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setNote(value);
    try {
      localStorage.setItem(`uiplan:notes:${node.id}`, value);
    } catch {
      // ignore
    }
  };

  return (
    <div style={{ padding: 18, fontFamily: "'Inter', sans-serif", display: "flex", flexDirection: "column", height: "100%", boxSizing: "border-box" }}>
      <Section label="MANUAL NOTES" />
      <div style={{ marginTop: 10, flex: 1, display: "flex", flexDirection: "column" }}>
        <textarea
          value={note}
          onChange={handleChange}
          placeholder="Add manual notes or context for this node..."
          style={{
            flex: 1,
            minHeight: 200,
            width: "100%",
            background: PALETTE.bg,
            border: `1px solid ${PALETTE.rule}`,
            borderRadius: 6,
            padding: "10px 12px",
            fontFamily: "'Inter', sans-serif",
            fontSize: 13,
            lineHeight: 1.5,
            color: PALETTE.text,
            resize: "vertical",
            outline: "none",
            boxSizing: "border-box",
          }}
        />
      </div>
      <div style={{ marginTop: 12 }}>
        <Section label="RAW METADATA" />
        <div style={{
          marginTop: 10, padding: "10px 12px",
          background: PALETTE.bg, border: `1px solid ${PALETTE.rule}`,
          borderRadius: 6, overflow: "auto", maxHeight: 300,
        }}>
          <pre style={{ margin: 0, fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: PALETTE.textDim, whiteSpace: "pre-wrap" }}>
            {JSON.stringify(node.meta, null, 2) || "No metadata available."}
          </pre>
        </div>
      </div>
    </div>
  );
}

function ConnectionsTab({ node, graph, onSelectNode, onSelectEdge }: {
  node: ProjectNode;
  graph: ProjectGraph;
  onSelectNode: (id: string) => void;
  onSelectEdge: (id: string) => void;
}) {
  const incoming = graph.edges.filter((e) => e.target === node.id);
  const outgoing = graph.edges.filter((e) => e.source === node.id);

  const renderList = (edges: ProjectEdge[], direction: "source" | "target", title: string) => {
    if (edges.length === 0) {
      return (
        <div style={{ marginBottom: 18 }}>
          <Section label={title} count={0} />
          <div style={{ marginTop: 8, fontSize: 12, color: PALETTE.textMute, fontFamily: "'JetBrains Mono', monospace" }}>
            ∅ none
          </div>
        </div>
      );
    }
    return (
      <div style={{ marginBottom: 18 }}>
        <Section label={title} count={edges.length} />
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 4 }}>
          {edges.map((edge) => {
            const otherId = edge[direction];
            const other = graph.nodes.find((n) => n.id === otherId);
            if (!other) return null;
            const otherLayer = getLayer(other.layer);
            const style = getEdgeStyle(edge.kind);
            const Icon = KIND_ICONS[other.kind];
            return (
              <div key={edge.id} style={{ display: "flex", gap: 4 }}>
                <button
                  onClick={() => onSelectNode(otherId)}
                  style={{
                    flex: 1,
                    display: "flex", alignItems: "center", gap: 10,
                    padding: "8px 10px",
                    background: PALETTE.bg,
                    border: `1px solid ${PALETTE.rule}`,
                    borderLeft: `3px solid ${otherLayer.color}`,
                    cursor: "pointer", textAlign: "left",
                    borderRadius: 4, fontFamily: "'Inter', sans-serif",
                  }}
                >
                  {Icon && <Icon size={13} color={otherLayer.color} strokeWidth={2} />}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12, color: PALETTE.text, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {other.label}
                    </div>
                    <div style={{ fontSize: 12, color: style.color, fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.15em", fontWeight: 600, marginTop: 2 }}>
                      {edge.kind.toUpperCase()}{edge.label ? ` · ${edge.label.toUpperCase()}` : ""}
                    </div>
                  </div>
                  <ChevronRight size={12} style={{ color: PALETTE.textMute }} />
                </button>
                <button
                  onClick={() => onSelectEdge(edge.id)}
                  title="Inspect this edge"
                  style={{
                    background: PALETTE.bg,
                    border: `1px solid ${PALETTE.rule}`,
                    borderRadius: 4, padding: "0 10px",
                    cursor: "pointer", color: PALETTE.textDim,
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 12, letterSpacing: "0.1em", fontWeight: 700,
                  }}>
                  EDGE
                </button>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div style={{ padding: 18 }}>
      {renderList(incoming, "source", "INBOUND")}
      {renderList(outgoing, "target", "OUTBOUND")}
    </div>
  );
}

interface InspectorProps {
  graph: ProjectGraph;
  rootGraph?: ProjectGraph;
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  selectedSkillId?: string | null;
  sourcePath: string;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  onSelectNode: (id: string | null) => void;
  onSelectEdge: (id: string | null) => void;
  onSelectSkill?: (id: string | null) => void;
  onJumpToSkillNode?: (nodeId: string) => void;
  onDrillDown: (node: ProjectNode) => void;
  onJumpToFile?: (path: string) => void;
}

export default function Inspector({
  graph, rootGraph, selectedNodeId, selectedEdgeId, selectedSkillId, sourcePath,
  collapsed, onToggleCollapsed,
  onSelectNode, onSelectEdge, onSelectSkill, onJumpToSkillNode,
  onDrillDown, onJumpToFile,
}: InspectorProps) {
  const [tab, setTab] = useState<InspectorTab>("overview");
  useEffect(() => {
    const sel = selectedNodeId
      ? (graph.nodes.find((n) => n.id === selectedNodeId)
          ?? findNodeRecursive(rootGraph?.nodes ?? [], selectedNodeId))
      : null;
    if (sel?.kind === "uiplan_doc") setTab("code");
    else setTab("overview");
  }, [selectedNodeId, graph.nodes, rootGraph]);

  const node = selectedNodeId
    ? (graph.nodes.find((n) => n.id === selectedNodeId)
        ?? findNodeRecursive(rootGraph?.nodes ?? [], selectedNodeId)
        ?? null)
    : null;
  const edge = selectedEdgeId ? graph.edges.find((e) => e.id === selectedEdgeId) ?? null : null;

  if (collapsed) {
    return (
      <div style={{
        width: 36, background: PALETTE.panel,
        borderLeft: `1px solid ${PALETTE.rule}`,
        display: "flex", flexDirection: "column", alignItems: "center",
        padding: "10px 0", flexShrink: 0,
      }}>
        <button onClick={onToggleCollapsed} title="Expand inspector" style={{
          background: "transparent", border: "none", cursor: "pointer",
          padding: 6, color: PALETTE.textDim,
        }}>
          <PanelRightOpen size={16} />
        </button>
      </div>
    );
  }

  // Skill story panel — independent selection mode
  if (selectedSkillId && rootGraph) {
    const skillNode = findNodeRecursive(rootGraph.nodes, selectedSkillId);
    if (skillNode && skillNode.kind === "skill") {
      return (
        <SkillStoryPanel
          skillNode={skillNode}
          rootGraph={rootGraph}
          onClose={() => onSelectSkill?.(null)}
          onJumpToNode={(id) => {
            onJumpToSkillNode?.(id);
          }}
        />
      );
    }
  }

  // Edge inspector (no node selected, but an edge is)
  if (edge && !node) {
    const fromNode = graph.nodes.find((n) => n.id === edge.source);
    const toNode = graph.nodes.find((n) => n.id === edge.target);
    const style = getEdgeStyle(edge.kind);

    return (
      <div style={{
        width: 392, background: PALETTE.panel,
        borderLeft: `1px solid ${PALETTE.rule}`,
        display: "flex", flexDirection: "column",
        overflow: "hidden", fontFamily: "'Inter', sans-serif", flexShrink: 0,
      }}>
        <div style={{ padding: 20, borderBottom: `1px solid ${PALETTE.rule}`, display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ flex: 1 }}>
            <div style={{
              fontSize: 12, letterSpacing: "0.22em", color: style.color,
              fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", marginBottom: 4,
            }}>
              EDGE · {edge.kind.toUpperCase()}{edge.label ? ` · ${edge.label.toUpperCase()}` : ""}
            </div>
            <div style={{ fontSize: 15, color: PALETTE.text, fontWeight: 700 }}>
              {fromNode?.label ?? edge.source}
              <span style={{ color: PALETTE.textMute, margin: "0 8px" }}>→</span>
              {toNode?.label ?? edge.target}
            </div>
          </div>
          <button onClick={onToggleCollapsed} title="Collapse inspector" style={{
            background: "transparent", border: "none", cursor: "pointer",
            padding: 6, color: PALETTE.textDim,
          }}>
            <PanelRightClose size={16} />
          </button>
        </div>
        <div style={{ padding: 20, flex: 1, overflowY: "auto" }}>
          {edge.desc && (
            <>
              <Section label="DESCRIPTION" />
              <div style={{ marginTop: 10, fontSize: 13, lineHeight: 1.55, color: PALETTE.text }}>
                {edge.desc}
              </div>
            </>
          )}
          <div style={{ marginTop: 22 }}>
            <Section label="ENDPOINTS" />
            <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
              {fromNode && (
                <button onClick={() => onSelectNode(fromNode.id)} style={endpointBtn(getLayer(fromNode.layer).color)}>
                  <span style={{ fontSize: 12, color: PALETTE.textDim, fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.15em" }}>FROM</span>
                  <span style={{ flex: 1, fontWeight: 600 }}>{fromNode.label}</span>
                  <ChevronRight size={12} style={{ color: PALETTE.textMute }} />
                </button>
              )}
              {toNode && (
                <button onClick={() => onSelectNode(toNode.id)} style={endpointBtn(getLayer(toNode.layer).color)}>
                  <span style={{ fontSize: 12, color: PALETTE.textDim, fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.15em" }}>TO</span>
                  <span style={{ flex: 1, fontWeight: 600 }}>{toNode.label}</span>
                  <ChevronRight size={12} style={{ color: PALETTE.textMute }} />
                </button>
              )}
            </div>
          </div>
          {edge.citations && edge.citations.length > 0 && (
            <div style={{ marginTop: 22 }}>
              <Section label="DOCUMENTATION" count={edge.citations.length} />
              <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 8 }}>
                {edge.citations.map((c, i) => <CitationItem key={i} c={c} />)}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Empty state — show the project-level overview (BA shell)
  if (!node) {
    return (
      <div style={{
        width: 392, background: PALETTE.panel,
        borderLeft: `1px solid ${PALETTE.rule}`,
        display: "flex", flexDirection: "column",
        flexShrink: 0, overflow: "hidden",
      }}>
        <div style={{
          padding: "12px 18px", borderBottom: `1px solid ${PALETTE.rule}`,
          display: "flex", alignItems: "center", justifyContent: "space-between",
          background: PALETTE.bg,
        }}>
          <span style={{
            fontSize: 12, letterSpacing: "0.22em", fontWeight: 700,
            color: PALETTE.textDim, fontFamily: "'JetBrains Mono', monospace",
          }}>
            CONTEXT · PROJECT
          </span>
          <button onClick={onToggleCollapsed} title="Collapse inspector" style={{
            background: "transparent", border: "none", cursor: "pointer",
            padding: 4, color: PALETTE.textDim,
          }}>
            <PanelRightClose size={14} />
          </button>
        </div>
        <div style={{ flex: 1, overflowY: "auto" }}>
          <ProjectOverview graph={graph} />
        </div>
      </div>
    );
  }

  const layer = getLayer(node.layer);
  const KindIcon = KIND_ICONS[node.kind];
  const incoming = graph.edges.filter((e) => e.target === node.id);
  const outgoing = graph.edges.filter((e) => e.source === node.id);
  const knowledgeCount = node.kind === "skill"
    ? matchedNodeIds(node).length
    : (node.citations?.length ?? 0) + (node.skills?.length ?? 0);
  const status = node.status ?? "ok";
  const statusColor = STATUS_COLOR[status];
  const isSkill = node.kind === "skill";
  const skillId = isSkill ? skillIdFromNode(node) : "";
  const isUiplanFile = node.kind === "uiplan_doc" || node.kind === "uiplan_tasks";
  const isUiplanBundle = node.kind === "uiplan_bundle";
  const isUiplanTask = node.kind === "uiplan_task";
  const isUiplanPlanningNode = String(node.kind).startsWith("uiplan_") && node.kind !== "uiplan_doc";
  const uiplanBody = isUiplanFile ? String(node.meta?.body ?? "") : "";

  return (
    <div style={{
      width: 392, background: PALETTE.panel,
      borderLeft: `1px solid ${PALETTE.rule}`,
      display: "flex", flexDirection: "column",
      overflow: "hidden", fontFamily: "'Inter', sans-serif",
      flexShrink: 0,
    }}>
      <div style={{ padding: 20, borderBottom: `1px solid ${PALETTE.rule}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
          <div style={{ width: 40, height: 40, borderRadius: 8, background: layer.soft, border: `1px solid ${layer.color}33`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            {KindIcon && <KindIcon size={18} color={layer.color} strokeWidth={1.8} />}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 12, letterSpacing: "0.08em", color: layer.color, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", marginBottom: 3, display: "flex", alignItems: "center", gap: 6 }}>
              <span>{layer.short} · {node.kind.replace("_", " ").toUpperCase()}</span>
              <span title={`status: ${status}`} style={{ width: 7, height: 7, borderRadius: "50%", background: statusColor, marginLeft: "auto" }} />
            </div>
            <div style={{ fontSize: 17, color: PALETTE.text, fontWeight: 700, wordBreak: "break-word", lineHeight: 1.25 }}>
              {node.label}
            </div>
          </div>
          <button onClick={onToggleCollapsed} title="Collapse inspector" style={{
            background: "transparent", border: "none", cursor: "pointer",
            padding: 6, color: PALETTE.textDim,
          }}>
            <PanelRightClose size={14} />
          </button>
        </div>
        <div style={{
          fontSize: 12, color: PALETTE.textMute,
          fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.08em",
          padding: "4px 8px", background: PALETTE.bg,
          border: `1px solid ${PALETTE.rule}`, borderRadius: 6,
          display: "inline-block",
        }}>
          {node.id}
        </div>
        <div style={{ marginTop: 12 }}>
          <Section label="NEXT ACTIONS" />
          <div style={{ marginTop: 8, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <button
              onClick={() => setTab("code")}
              style={quickActionStyle()}
            >
              OPEN CODE
            </button>
            <button
              onClick={() => setTab("links")}
              style={quickActionStyle()}
            >
              TRACE LINKS
            </button>
          </div>
        </div>

        {node.children && node.children.nodes.length > 0 && (
          <button
            onClick={() => onDrillDown(node)}
            style={{
              marginTop: 12, width: "100%",
              display: "flex", alignItems: "center", gap: 8,
              padding: "10px 12px",
              background: layer.soft,
              border: `1px solid ${layer.color}55`,
              borderRadius: 8, cursor: "pointer",
              color: layer.color,
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 12, fontWeight: 700, letterSpacing: "0.08em",
            }}
          >
            <Maximize2 size={13} strokeWidth={2.2} />
            <span style={{ flex: 1, textAlign: "left" }}>OPEN SUB-GRAPH</span>
            <span style={{ background: "rgba(0,0,0,0.08)", padding: "2px 7px", borderRadius: 3, fontSize: 12 }}>
              {node.children.nodes.length}
            </span>
          </button>
        )}
      </div>

      <div style={{ display: "flex", borderBottom: `1px solid ${PALETTE.rule}`, background: PALETTE.bg }}>
        <Tab active={tab === "overview"} onClick={() => setTab("overview")}>OVERVIEW</Tab>
        {!isUiplanPlanningNode && (
          <Tab active={tab === "code"} onClick={() => setTab("code")}>{isSkill ? "BODY" : "CODE"}</Tab>
        )}
        <Tab active={tab === "knowledge"} onClick={() => setTab("knowledge")} count={knowledgeCount > 0 ? knowledgeCount : undefined}>
          {isSkill ? "COVERAGE" : "KNOWLEDGE"}
        </Tab>
        <Tab active={tab === "links"} onClick={() => setTab("links")} count={incoming.length + outgoing.length}>
          LINKS
        </Tab>
        <Tab active={tab === "notes"} onClick={() => setTab("notes")}>
          NOTES
        </Tab>
      </div>

      <div style={{ flex: 1, overflowY: "auto", background: PALETTE.panel }}>
        {tab === "overview" && (
          isUiplanTask
            ? <UiplanTaskPanel node={node} rootGraph={rootGraph ?? graph} onJumpToFile={onJumpToFile} />
            : isUiplanBundle || node.kind === "uiplan_tasks"
              ? <UiplanProgressPanel node={node} rootGraph={rootGraph ?? graph} onJumpToFile={onJumpToFile} />
              : isUiplanFile
                ? <OverviewTab node={node} graph={graph} />
                : isSkill
                  ? <SkillOverviewTab node={node} detail={null} />
                  : <OverviewTab node={node} graph={graph} />
        )}
        {tab === "code" && !isUiplanPlanningNode && (
          isUiplanFile
            ? <div style={{ padding: 18 }}>{uiplanBody
                ? <MarkdownView source={uiplanBody} />
                : <CodeTab node={node} />}</div>
            : isSkill
              ? <SkillBodyTab skillId={skillId} />
              : <CodeTab node={node} />
        )}
        {tab === "knowledge" && (isSkill
          ? <SkillCoverageTab node={node} graph={graph} onSelectNode={onSelectNode as (id: string) => void} />
          : <KnowledgeTab node={node} sourcePath={sourcePath} onOpenStory={onSelectSkill ? (id) => onSelectSkill(id) : undefined} />)}
        {tab === "links" && (
          <ConnectionsTab node={node} graph={graph} onSelectNode={onSelectNode} onSelectEdge={onSelectEdge} />
        )}
        {tab === "notes" && (
          <NotesTab node={node} />
        )}
      </div>
    </div>
  );
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

function endpointBtn(borderColor: string): React.CSSProperties {
  return {
    display: "flex", alignItems: "center", gap: 10,
    padding: "8px 10px", background: PALETTE.bg,
    border: `1px solid ${PALETTE.rule}`,
    borderLeft: `3px solid ${borderColor}`,
    borderRadius: 4, cursor: "pointer", textAlign: "left",
    fontFamily: "'Inter', sans-serif", color: PALETTE.text,
  };
}

function quickActionStyle(): React.CSSProperties {
  return {
    border: `1px solid ${PALETTE.rule}`,
    borderRadius: 8,
    background: PALETTE.bg,
    color: PALETTE.text,
    padding: "8px 10px",
    cursor: "pointer",
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 12,
    letterSpacing: "0.06em",
    fontWeight: 700,
  };
}
