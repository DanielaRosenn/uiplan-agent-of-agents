import React, { useMemo, useState } from "react";
import { LayoutGrid, List as ListIcon, Search, Sparkles, X } from "lucide-react";

import { PALETTE, STATUS_COLOR } from "../theme";
import type { ProjectGraph, ProjectNode } from "../projectGraph/types";

const ORIGIN_COLORS: Record<string, { fg: string; bg: string; border: string }> = {
  "uipath-submodule": { fg: "#0f766e", bg: "#ccfbf1", border: "#5eead4" },
  user:               { fg: "#7c3aed", bg: "#f3e8ff", border: "#ddd6fe" },
  extension:          { fg: "#d97706", bg: "#fef3c7", border: "#fde68a" },
  cursor:             { fg: "#2563eb", bg: "#dbeafe", border: "#bfdbfe" },
};

function originStyle(origin: string) {
  return ORIGIN_COLORS[origin] ?? { fg: PALETTE.text, bg: PALETTE.bg, border: PALETTE.rule };
}

interface SkillsCanvasProps {
  graph: ProjectGraph;
  selectedSkillId: string | null;
  onSelectSkill: (id: string) => void;
}

type ViewMode = "grid" | "list";

const DESC_TRUNCATE = 280;

export default function SkillsCanvas({ graph, selectedSkillId, onSelectSkill }: SkillsCanvasProps) {
  const skills = useMemo(() => {
    return graph.nodes
      .filter((n) => n.kind === "skill")
      .slice()
      .sort((a, b) => {
        const ca = Number(a.meta?.coverage_count ?? 0);
        const cb = Number(b.meta?.coverage_count ?? 0);
        if (cb !== ca) return cb - ca;
        return a.label.localeCompare(b.label);
      });
  }, [graph.nodes]);

  const origins = useMemo(() => {
    const set = new Set<string>();
    for (const s of skills) {
      const o = String(s.meta?.origin ?? "").trim();
      if (o) set.add(o);
    }
    return Array.from(set).sort();
  }, [skills]);

  const [originFilter, setOriginFilter] = useState<Set<string>>(new Set());
  const [query, setQuery] = useState("");
  const [view, setView] = useState<ViewMode>("grid");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return skills.filter((s) => {
      if (originFilter.size > 0) {
        const o = String(s.meta?.origin ?? "");
        if (!originFilter.has(o)) return false;
      }
      if (q) {
        const hay = `${s.label}\n${s.desc ?? ""}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [skills, originFilter, query]);

  const toggleOrigin = (o: string) => {
    setOriginFilter((prev) => {
      const next = new Set(prev);
      if (next.has(o)) next.delete(o);
      else next.add(o);
      return next;
    });
  };

  return (
    <div style={{
      position: "absolute", inset: 0,
      display: "flex", flexDirection: "column",
      background: PALETTE.bg, overflow: "hidden",
    }}>
      {/* Toolbar */}
      <div style={{
        flexShrink: 0,
        padding: "14px 20px",
        borderBottom: `1px solid ${PALETTE.rule}`,
        background: PALETTE.panel,
        display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap",
      }}>
        <div style={{
          display: "flex", alignItems: "center", gap: 8,
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11, letterSpacing: "0.22em", fontWeight: 700,
          color: PALETTE.text,
        }}>
          <Sparkles size={14} color="#0f766e" strokeWidth={2.2} />
          SKILLS
          <span style={{ color: PALETTE.textDim, fontWeight: 600 }}>
            · {String(filtered.length).padStart(2, "0")}/{String(skills.length).padStart(2, "0")}
          </span>
        </div>

        <div style={{ position: "relative", minWidth: 220 }}>
          <Search size={12} style={{
            position: "absolute", left: 9, top: "50%", transform: "translateY(-50%)",
            color: PALETTE.textDim,
          }} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="search skills…"
            style={{
              width: "100%", boxSizing: "border-box",
              background: PALETTE.bg,
              border: `1px solid ${PALETTE.rule}`,
              borderRadius: 4,
              padding: "6px 26px 6px 26px",
              fontSize: 12, fontFamily: "'JetBrains Mono', monospace",
              color: PALETTE.text, outline: "none",
            }}
          />
          {query && (
            <button onClick={() => setQuery("")} style={{
              position: "absolute", right: 4, top: "50%", transform: "translateY(-50%)",
              background: "transparent", border: "none", color: PALETTE.textDim,
              cursor: "pointer", padding: 4,
            }}>
              <X size={11} />
            </button>
          )}
        </div>

        {origins.length > 0 && (
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {origins.map((o) => {
              const style = originStyle(o);
              const active = originFilter.size === 0 || originFilter.has(o);
              return (
                <button
                  key={o}
                  onClick={() => toggleOrigin(o)}
                  style={{
                    fontSize: 10, fontFamily: "'JetBrains Mono', monospace",
                    letterSpacing: "0.1em", fontWeight: 700,
                    color: active ? style.fg : PALETTE.textDim,
                    background: active ? style.bg : "transparent",
                    border: `1px solid ${active ? style.border : PALETTE.rule}`,
                    padding: "4px 9px", borderRadius: 12, cursor: "pointer",
                    opacity: active ? 1 : 0.5,
                  }}
                >
                  {o.toUpperCase()}
                </button>
              );
            })}
          </div>
        )}

        <div style={{ flex: 1 }} />

        <div style={{
          display: "flex",
          border: `1px solid ${PALETTE.rule}`, borderRadius: 4, overflow: "hidden",
        }}>
          <ToolbarToggle active={view === "grid"} onClick={() => setView("grid")} title="Grid view">
            <LayoutGrid size={12} />
          </ToolbarToggle>
          <ToolbarToggle active={view === "list"} onClick={() => setView("list")} title="List view">
            <ListIcon size={12} />
          </ToolbarToggle>
        </div>
      </div>

      {/* Body */}
      <div style={{ flex: 1, overflow: "auto", padding: 20 }}>
        {filtered.length === 0 ? (
          <div style={{
            color: PALETTE.textMute, fontSize: 12,
            fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.12em",
            textAlign: "center", marginTop: 60,
          }}>
            ∅ NO SKILLS MATCH
          </div>
        ) : view === "grid" ? (
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
            gap: 16,
          }}>
            {filtered.map((s) => (
              <SkillCard
                key={s.id}
                node={s}
                selected={s.id === selectedSkillId}
                onOpen={() => onSelectSkill(s.id)}
                truncate
              />
            ))}
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {filtered.map((s) => (
              <SkillCard
                key={s.id}
                node={s}
                selected={s.id === selectedSkillId}
                onOpen={() => onSelectSkill(s.id)}
                truncate={false}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ToolbarToggle({ active, onClick, title, children }: {
  active: boolean; onClick: () => void; title: string; children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      style={{
        background: active ? PALETTE.bg : PALETTE.panel,
        border: "none",
        borderRight: `1px solid ${PALETTE.rule}`,
        padding: "6px 10px",
        cursor: "pointer",
        color: active ? PALETTE.text : PALETTE.textDim,
        display: "flex", alignItems: "center",
      }}
    >
      {children}
    </button>
  );
}

function SkillCard({ node, selected, onOpen, truncate }: {
  node: ProjectNode;
  selected: boolean;
  onOpen: () => void;
  truncate: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const origin = String(node.meta?.origin ?? "");
  const oStyle = originStyle(origin);
  const coverage = Number(node.meta?.coverage_count ?? 0);
  const status = node.status;
  const desc = node.desc ?? "";
  const showFullDesc = !truncate || expanded || desc.length <= DESC_TRUNCATE;
  const shownDesc = showFullDesc ? desc : desc.slice(0, DESC_TRUNCATE).trimEnd() + "…";

  return (
    <div
      onClick={onOpen}
      style={{
        background: PALETTE.panel,
        border: `1px solid ${selected ? "#0f766e" : PALETTE.rule}`,
        borderLeft: `3px solid #8b5cf6`,
        borderRadius: 6,
        padding: 14,
        cursor: "pointer",
        display: "flex", flexDirection: "column", gap: 10,
        boxShadow: selected ? "0 0 0 2px #0f766e22" : "none",
        transition: "box-shadow 0.15s",
        fontFamily: "'Inter', sans-serif",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <Sparkles size={14} color="#7c3aed" strokeWidth={2.2} />
        <div style={{
          fontSize: 13, fontWeight: 700, color: PALETTE.text,
          flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
        }}>
          {node.label}
        </div>
        {status && (
          <span title={`status: ${status}`} style={{
            width: 7, height: 7, borderRadius: "50%",
            background: STATUS_COLOR[status] ?? PALETTE.textMute,
            flexShrink: 0,
          }} />
        )}
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
        {origin && (
          <span style={{
            fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
            letterSpacing: "0.1em", fontWeight: 700,
            color: oStyle.fg, background: oStyle.bg,
            border: `1px solid ${oStyle.border}`,
            padding: "2px 7px", borderRadius: 3,
          }}>
            {origin.toUpperCase()}
          </span>
        )}
        <span title="nodes covered" style={{
          fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
          letterSpacing: "0.1em", fontWeight: 700,
          color: "#7c3aed", background: "#f3e8ff",
          border: "1px solid #ddd6fe",
          padding: "2px 7px", borderRadius: 3,
        }}>
          ◆ {coverage} NODE{coverage === 1 ? "" : "S"}
        </span>
      </div>

      {desc && (
        <div style={{
          fontSize: 12, lineHeight: 1.5, color: PALETTE.text,
        }}>
          {shownDesc}
          {truncate && desc.length > DESC_TRUNCATE && (
            <button
              onClick={(e) => { e.stopPropagation(); setExpanded((v) => !v); }}
              style={{
                marginLeft: 6, padding: 0, background: "transparent",
                border: "none", cursor: "pointer", color: "#0f766e",
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 10, fontWeight: 700, letterSpacing: "0.1em",
              }}
            >
              {expanded ? "LESS" : "MORE"}
            </button>
          )}
        </div>
      )}

      <div style={{
        marginTop: "auto",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 10, letterSpacing: "0.14em", fontWeight: 700,
        color: "#0f766e",
        paddingTop: 4, borderTop: `1px dashed ${PALETTE.ruleSoft}`,
      }}>
        <span style={{ color: PALETTE.textMute, fontWeight: 500, letterSpacing: "0.06em" }}>
          {String(node.meta?.path ?? node.id)}
        </span>
        <span>OPEN STORY →</span>
      </div>
    </div>
  );
}
