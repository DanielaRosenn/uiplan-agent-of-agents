import React from "react";
import { AlertTriangle, Search, Sparkles, X } from "lucide-react";

import { EDGE_STYLE, LAYERS, PALETTE, PATH_CLASS_COLOR, STATUS_COLOR } from "../theme";
import type { EdgeKind, LayerKey, PathClass, ProjectGraph } from "../projectGraph/types";
import { Section } from "./primitives";

interface LeftRailProps {
  graph: ProjectGraph;
  query: string;
  setQuery: (q: string) => void;
  layerFilter: Set<string>;
  toggleLayer: (key: string) => void;
  pathFilter: Set<PathClass>;
  togglePath: (key: PathClass) => void;
  issuesOnly: boolean;
  setIssuesOnly: (v: boolean) => void;
  showSkillCoverage: boolean;
  setShowSkillCoverage: (v: boolean) => void;
  onSelectNode?: (id: string) => void;
  searchInputRef?: React.RefObject<HTMLInputElement>;
  onSubmitSearch?: () => void;
}

const PATH_CLASSES: PathClass[] = ["happy", "alt", "loopback", "exception"];

export default function LeftRail({
  graph, query, setQuery,
  layerFilter, toggleLayer,
  pathFilter, togglePath,
  issuesOnly, setIssuesOnly,
  showSkillCoverage, setShowSkillCoverage, onSelectNode,
  searchInputRef, onSubmitSearch,
}: LeftRailProps) {
  const layersWithCount = (Object.keys(LAYERS) as LayerKey[]).map((key) => ({
    key, count: graph.nodes.filter((n) => n.layer === key).length,
  })).filter((x) => x.count > 0);

  const issueCount = graph.errors?.length ?? 0;
  const skillNodes = graph.nodes
    .filter((n) => n.kind === "skill")
    .sort((a, b) => Number(b.meta?.coverage_count ?? 0) - Number(a.meta?.coverage_count ?? 0));

  return (
    <div style={{
      width: 240, background: PALETTE.panel,
      borderRight: `1px solid ${PALETTE.rule}`,
      display: "flex", flexDirection: "column",
      fontFamily: "'Inter', system-ui, sans-serif",
      color: PALETTE.text, overflow: "auto", flexShrink: 0,
    }}>
      <div style={{ padding: 16, borderBottom: `1px solid ${PALETTE.rule}` }}>
        <Section label="QUERY" />
        <div style={{ position: "relative", marginTop: 10 }}>
          <Search size={12} style={{ position: "absolute", left: 9, top: "50%", transform: "translateY(-50%)", color: PALETTE.textDim }} />
          <input
            ref={searchInputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && onSubmitSearch) onSubmitSearch();
            }}
            placeholder="filter / press ⏎ to jump…"
            style={{
              width: "100%", background: PALETTE.bg,
              border: `1px solid ${PALETTE.rule}`, color: PALETTE.text,
              padding: "7px 28px 7px 28px", fontSize: 12,
              fontFamily: "'JetBrains Mono', monospace",
              outline: "none", borderRadius: 4, boxSizing: "border-box",
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
        <div style={{
          marginTop: 6, fontSize: 9, color: PALETTE.textMute,
          fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.12em",
        }}>
          PRESS&nbsp;<kbd style={{ background: PALETTE.bg, border: `1px solid ${PALETTE.rule}`, padding: "0 4px", borderRadius: 2 }}>/</kbd>&nbsp;TO&nbsp;FOCUS
        </div>
      </div>

      <div style={{ padding: 16, borderBottom: `1px solid ${PALETTE.rule}`, flex: "0 0 auto" }}>
        <Section label="LAYERS" />
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 2 }}>
          {layersWithCount.length === 0 && (
            <div style={{ fontSize: 10, color: PALETTE.textMute, fontFamily: "'JetBrains Mono', monospace" }}>
              ∅ no layers in view
            </div>
          )}
          {layersWithCount.map(({ key, count }) => {
            const layer = LAYERS[key];
            const active = layerFilter.size === 0 || layerFilter.has(key);
            const LayerIcon = layer.Icon;
            return (
              <button
                key={key}
                onClick={() => toggleLayer(key)}
                style={{
                  display: "flex", alignItems: "center", gap: 10,
                  background: active ? layer.soft : "transparent",
                  border: `1px solid ${active ? layer.color + "33" : "transparent"}`,
                  borderLeft: `3px solid ${active ? layer.color : PALETTE.rule}`,
                  padding: "8px 10px", cursor: "pointer", textAlign: "left",
                  opacity: active ? 1 : 0.45, transition: "all 0.15s",
                  borderRadius: 4, fontFamily: "'Inter', sans-serif",
                }}
              >
                <LayerIcon size={13} color={layer.color} strokeWidth={2} />
                <span style={{ fontSize: 12, color: PALETTE.text, flex: 1, fontWeight: 500 }}>{layer.name}</span>
                <span style={{ fontSize: 10, color: PALETTE.textDim, fontFamily: "'JetBrains Mono', monospace" }}>
                  {String(count).padStart(2, "0")}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      <div style={{ padding: 16, borderBottom: `1px solid ${PALETTE.rule}`, flex: "0 0 auto" }}>
        <Section label="PATHS" />
        <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 6 }}>
          {PATH_CLASSES.map((p) => {
            const meta = PATH_CLASS_COLOR[p];
            const active = pathFilter.size === 0 || pathFilter.has(p);
            return (
              <button
                key={p}
                onClick={() => togglePath(p)}
                style={{
                  fontSize: 10, fontWeight: 700, letterSpacing: "0.12em",
                  fontFamily: "'JetBrains Mono', monospace",
                  background: active ? meta.color + "22" : "transparent",
                  border: `1px solid ${active ? meta.color : PALETTE.rule}`,
                  color: active ? meta.color : PALETTE.textDim,
                  padding: "4px 9px", borderRadius: 12, cursor: "pointer",
                  opacity: active ? 1 : 0.5,
                }}
                title={meta.label}
              >
                {p.toUpperCase()}
              </button>
            );
          })}
        </div>
        <div style={{ marginTop: 6, fontSize: 9, color: PALETTE.textMute, fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.1em" }}>
          {pathFilter.size === 0 ? "ALL EDGES VISIBLE" : `${pathFilter.size} CLASS${pathFilter.size > 1 ? "ES" : ""} ACTIVE`}
        </div>
      </div>

      <div style={{ padding: 16, borderBottom: `1px solid ${PALETTE.rule}`, flex: "0 0 auto" }}>
        <Section label="HEALTH" />
        <button
          onClick={() => setIssuesOnly(!issuesOnly)}
          style={{
            marginTop: 10, width: "100%",
            display: "flex", alignItems: "center", gap: 8,
            background: issuesOnly ? "#fef2f2" : PALETTE.bg,
            border: `1px solid ${issuesOnly ? "#fecaca" : PALETTE.rule}`,
            borderLeft: `3px solid ${issuesOnly ? "#dc2626" : PALETTE.rule}`,
            padding: "8px 10px", cursor: "pointer",
            borderRadius: 4, fontFamily: "'Inter', sans-serif",
          }}>
          <AlertTriangle size={13} color={issuesOnly ? "#dc2626" : PALETTE.textDim} />
          <span style={{ fontSize: 12, color: PALETTE.text, fontWeight: 600, flex: 1, textAlign: "left" }}>
            issues only
          </span>
          <span style={{ fontSize: 10, color: PALETTE.textDim, fontFamily: "'JetBrains Mono', monospace" }}>
            {String(issueCount).padStart(2, "0")}
          </span>
        </button>
      </div>

      <div style={{ padding: 16, borderBottom: `1px solid ${PALETTE.rule}`, flex: "0 0 auto" }}>
        <Section label="SKILLS" count={skillNodes.length} />
        <button
          onClick={() => setShowSkillCoverage(!showSkillCoverage)}
          style={{
            marginTop: 10, width: "100%",
            display: "flex", alignItems: "center", gap: 8,
            background: showSkillCoverage ? "#f3e8ff" : PALETTE.bg,
            border: `1px solid ${showSkillCoverage ? "#c4b5fd" : PALETTE.rule}`,
            borderLeft: `3px solid ${showSkillCoverage ? "#8b5cf6" : PALETTE.rule}`,
            padding: "8px 10px", cursor: "pointer",
            borderRadius: 4, fontFamily: "'Inter', sans-serif",
          }}>
          <Sparkles size={13} color={showSkillCoverage ? "#8b5cf6" : PALETTE.textDim} />
          <span style={{ fontSize: 12, color: PALETTE.text, fontWeight: 600, flex: 1, textAlign: "left" }}>
            show coverage
          </span>
          <span style={{ fontSize: 10, color: PALETTE.textDim, fontFamily: "'JetBrains Mono', monospace" }}>
            {showSkillCoverage ? "ON" : "OFF"}
          </span>
        </button>
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
          {skillNodes.length === 0 ? (
            <div style={{ fontSize: 10, color: PALETTE.textMute, fontFamily: "'JetBrains Mono', monospace" }}>
              ∅ no skills matched
            </div>
          ) : (
            skillNodes.slice(0, 8).map((skill) => (
              <button
                key={skill.id}
                onClick={() => onSelectNode?.(skill.id)}
                style={{
                  width: "100%", textAlign: "left",
                  background: PALETTE.bg,
                  border: `1px solid ${PALETTE.rule}`,
                  borderLeft: "3px solid #8b5cf6",
                  borderRadius: 4,
                  padding: "7px 9px",
                  cursor: "pointer",
                  fontFamily: "'Inter', sans-serif",
                }}
              >
                <div style={{
                  display: "flex", alignItems: "center", gap: 6,
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 10, letterSpacing: "0.08em", fontWeight: 700,
                  color: "#7c3aed",
                }}>
                  <Sparkles size={11} />
                  <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {String(skill.meta?.skill_id ?? skill.label)}
                  </span>
                  <span style={{ color: PALETTE.textDim }}>
                    {String(skill.meta?.coverage_count ?? 0)}
                  </span>
                </div>
                {skill.desc && (
                  <div style={{
                    marginTop: 3, fontSize: 10.5, color: PALETTE.textDim,
                    lineHeight: 1.35, display: "-webkit-box",
                    WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden",
                  }}>
                    {skill.desc}
                  </div>
                )}
              </button>
            ))
          )}
        </div>
      </div>

      <div style={{ padding: 16, borderBottom: `1px solid ${PALETTE.rule}`, flex: "0 0 auto" }}>
        <Section label="EDGES" />
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 7 }}>
          {(Object.entries(EDGE_STYLE) as Array<[EdgeKind, typeof EDGE_STYLE[EdgeKind]]>).map(([kind, style]) => (
            <div key={kind} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 11 }}>
              <svg width="36" height="6">
                <line x1="0" y1="3" x2="36" y2="3" stroke={style.color} strokeWidth={style.width} strokeDasharray={style.dash} />
              </svg>
              <span style={{ color: PALETTE.text, fontWeight: 500 }}>{kind}</span>
            </div>
          ))}
        </div>
      </div>

      <div style={{ padding: 16, borderBottom: `1px solid ${PALETTE.rule}`, flex: "0 0 auto" }}>
        <Section label="STATUS" />
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
          {(Object.entries(STATUS_COLOR) as Array<[keyof typeof STATUS_COLOR, string]>).map(([s, color]) => (
            <div key={s} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 11 }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: color, boxShadow: `0 0 0 2px ${color}33` }} />
              <span style={{ color: PALETTE.text, fontWeight: 500 }}>{s}</span>
            </div>
          ))}
        </div>
      </div>

      <div style={{ padding: 16, marginTop: "auto", flex: "0 0 auto" }}>
        <Section label="META" />
        <div style={{ marginTop: 10, fontSize: 10.5, lineHeight: 1.9, fontFamily: "'JetBrains Mono', monospace", color: PALETTE.textDim }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span>nodes</span><span style={{ color: PALETTE.text }}>{String(graph.nodes.length).padStart(3, "0")}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span>edges</span><span style={{ color: PALETTE.text }}>{String(graph.edges.length).padStart(3, "0")}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span>errors</span>
            <span style={{ color: graph.errors?.length ? "#dc2626" : PALETTE.text }}>
              {String(graph.errors?.length || 0).padStart(3, "0")}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
