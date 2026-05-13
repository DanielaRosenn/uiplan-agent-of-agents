import React, { useState } from "react";
import {
  AlertTriangle, ChevronDown, ChevronRight,
  CheckSquare, Circle, MinusSquare, Notebook, Search, Sparkles, Square, X,
} from "lucide-react";

import { LAYERS, PALETTE } from "../theme";
import type { LayerKey, ProjectGraph, ProjectNode } from "../projectGraph/types";
import { Section } from "./primitives";

interface LeftRailProps {
  graph: ProjectGraph;
  bundles?: ProjectNode[];
  selectedNodeId?: string | null;
  query: string;
  setQuery: (q: string) => void;
  layerFilter: Set<string>;
  toggleLayer: (key: string) => void;
  issuesOnly: boolean;
  setIssuesOnly: (v: boolean) => void;
  showSkillCoverage: boolean;
  setShowSkillCoverage: (v: boolean) => void;
  onSelectNode?: (id: string) => void;
  onSelectBundle?: (id: string) => void;
  onSelectTask?: (taskId: string, bundleId: string) => void;
  searchInputRef?: React.RefObject<HTMLInputElement>;
  onSubmitSearch?: () => void;
  onApplyFilterPreset?: (preset: "all" | "core" | "delivery" | "quality") => void;
  isUiplanFlow?: boolean;
}

export default function LeftRail({
  graph, bundles, selectedNodeId,
  query, setQuery,
  layerFilter, toggleLayer,
  issuesOnly, setIssuesOnly,
  showSkillCoverage, setShowSkillCoverage, onSelectNode,
  onSelectBundle, onSelectTask,
  searchInputRef, onSubmitSearch,
  onApplyFilterPreset, isUiplanFlow,
}: LeftRailProps) {
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>(() => {
    try {
      const raw = localStorage.getItem("uiplan:left-rail:collapsed");
      return raw ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  });
  const toggleSection = (key: string) => {
    setCollapsedSections((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      try {
        localStorage.setItem("uiplan:left-rail:collapsed", JSON.stringify(next));
      } catch {
        // ignore
      }
      return next;
    });
  };
  const isCollapsed = (key: string) => !!collapsedSections[key];

  const technicalLayers = new Set(["api", "rpa", "agent", "maestro", "app", "orchestrator", "external", "test"]);
  const layersWithCount = (Object.keys(LAYERS) as LayerKey[])
    .filter(key => !(isUiplanFlow && technicalLayers.has(key)))
    .map((key) => ({
      key, count: graph.nodes.filter((n) => n.layer === key).length,
    })).filter((x) => x.count > 0);

  const issueCount = graph.errors?.length ?? 0;
  const skillNodes = graph.nodes
    .filter((n) => n.kind === "skill")
    .sort((a, b) => Number(b.meta?.coverage_count ?? 0) - Number(a.meta?.coverage_count ?? 0));

  return (
    <div style={{
      width: 272, background: PALETTE.panel,
      borderRight: `1px solid ${PALETTE.rule}`,
      display: "flex", flexDirection: "column",
      fontFamily: "'Inter', system-ui, sans-serif",
      color: PALETTE.text, overflow: "auto", flexShrink: 0,
      position: "relative", zIndex: 10,
    }}>
      {bundles && bundles.length > 0 && (
        <UiplanTasksSection
          bundles={bundles}
          selectedNodeId={selectedNodeId ?? null}
          onSelectBundle={onSelectBundle}
          onSelectTask={onSelectTask}
        />
      )}
      <div style={{ padding: 18, borderBottom: `1px solid ${PALETTE.rule}` }}>
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
              padding: "9px 30px 9px 30px", fontSize: 13,
              fontFamily: "'JetBrains Mono', monospace",
              outline: "none", borderRadius: 8, boxSizing: "border-box",
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
          marginTop: 8, fontSize: 12, color: PALETTE.textMute,
          fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.06em",
        }}>
          PRESS&nbsp;<kbd style={{ background: PALETTE.bg, border: `1px solid ${PALETTE.rule}`, padding: "0 4px", borderRadius: 2 }}>/</kbd>&nbsp;TO&nbsp;FOCUS
        </div>
      </div>

      <div style={{ padding: 18, borderBottom: `1px solid ${PALETTE.rule}`, flex: "0 0 auto" }}>
        <Section label="PRESETS" />
        <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {[
            { id: "all", label: "ALL" },
            { id: "core", label: "CORE" },
            { id: "delivery", label: "DELIVERY" },
            { id: "quality", label: "QUALITY" },
          ].map((preset) => (
            <button
              key={preset.id}
              onClick={() => onApplyFilterPreset?.(preset.id as "all" | "core" | "delivery" | "quality")}
              style={{
                border: `1px solid ${PALETTE.rule}`,
                borderRadius: 8,
                background: PALETTE.bg,
                color: PALETTE.text,
                padding: "8px 10px",
                cursor: "pointer",
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 12,
                letterSpacing: "0.05em",
                fontWeight: 700,
              }}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ padding: 18, borderBottom: `1px solid ${PALETTE.rule}`, flex: "0 0 auto" }}>
        <Section label="LAYERS" />
        <button onClick={() => toggleSection("layers")} style={collapseBtnStyle(isCollapsed("layers"))}>
          {isCollapsed("layers") ? "SHOW" : "HIDE"}
        </button>
        {!isCollapsed("layers") && (
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
          {layersWithCount.length === 0 && (
            <div style={{ fontSize: 12, color: PALETTE.textMute, fontFamily: "'JetBrains Mono', monospace" }}>
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
                aria-pressed={active}
                style={{
                  display: "flex", alignItems: "center", gap: 10,
                  background: active ? layer.soft : "transparent",
                  border: `1px solid ${active ? layer.color + "33" : "transparent"}`,
                  borderLeft: `3px solid ${active ? layer.color : PALETTE.rule}`,
                  padding: "10px 12px", cursor: "pointer", textAlign: "left",
                  opacity: active ? 1 : 0.45, transition: "all 0.15s",
                  borderRadius: 8, fontFamily: "'Inter', sans-serif",
                }}
              >
                <LayerIcon size={13} color={layer.color} strokeWidth={2} />
                <span style={{ fontSize: 13, color: PALETTE.text, flex: 1, fontWeight: 600 }}>{layer.name}</span>
                <span style={{ fontSize: 12, color: PALETTE.textDim, fontFamily: "'JetBrains Mono', monospace" }}>
                  {String(count).padStart(2, "0")}
                </span>
              </button>
            );
          })}
        </div>
        )}
      </div>

      <div style={{ padding: 18, borderBottom: `1px solid ${PALETTE.rule}`, flex: "0 0 auto" }}>
        <Section label="HEALTH" />
        <button
          onClick={() => setIssuesOnly(!issuesOnly)}
          aria-pressed={issuesOnly}
          style={{
            marginTop: 10, width: "100%",
            display: "flex", alignItems: "center", gap: 8,
            background: issuesOnly ? "#fef2f2" : PALETTE.bg,
            border: `1px solid ${issuesOnly ? "#fecaca" : PALETTE.rule}`,
            borderLeft: `3px solid ${issuesOnly ? "#dc2626" : PALETTE.rule}`,
            padding: "10px 12px", cursor: "pointer",
            borderRadius: 8, fontFamily: "'Inter', sans-serif",
          }}>
          <AlertTriangle size={13} color={issuesOnly ? "#dc2626" : PALETTE.textDim} />
          <span style={{ fontSize: 13, color: PALETTE.text, fontWeight: 700, flex: 1, textAlign: "left" }}>
            issues only
          </span>
          <span style={{ fontSize: 12, color: PALETTE.textDim, fontFamily: "'JetBrains Mono', monospace" }}>
            {String(issueCount).padStart(2, "0")}
          </span>
        </button>
      </div>

      <div style={{ padding: 18, borderBottom: `1px solid ${PALETTE.rule}`, flex: "0 0 auto" }}>
        <Section label="SKILLS" count={skillNodes.length} />
        <button onClick={() => toggleSection("skills")} style={collapseBtnStyle(isCollapsed("skills"))}>
          {isCollapsed("skills") ? "SHOW" : "HIDE"}
        </button>
        {!isCollapsed("skills") && (
        <>
        <button
          onClick={() => setShowSkillCoverage(!showSkillCoverage)}
          aria-pressed={showSkillCoverage}
          style={{
            marginTop: 10, width: "100%",
            display: "flex", alignItems: "center", gap: 8,
            background: showSkillCoverage ? "#f3e8ff" : PALETTE.bg,
            border: `1px solid ${showSkillCoverage ? "#c4b5fd" : PALETTE.rule}`,
            borderLeft: `3px solid ${showSkillCoverage ? "#8b5cf6" : PALETTE.rule}`,
            padding: "10px 12px", cursor: "pointer",
            borderRadius: 8, fontFamily: "'Inter', sans-serif",
          }}>
          <Sparkles size={13} color={showSkillCoverage ? "#8b5cf6" : PALETTE.textDim} />
          <span style={{ fontSize: 13, color: PALETTE.text, fontWeight: 700, flex: 1, textAlign: "left" }}>
            show coverage
          </span>
          <span style={{ fontSize: 12, color: PALETTE.textDim, fontFamily: "'JetBrains Mono', monospace" }}>
            {showSkillCoverage ? "ON" : "OFF"}
          </span>
        </button>
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
          {skillNodes.length === 0 ? (
            <div style={{ fontSize: 12, color: PALETTE.textMute, fontFamily: "'JetBrains Mono', monospace" }}>
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
                  borderRadius: 8,
                  padding: "9px 10px",
                  cursor: "pointer",
                  fontFamily: "'Inter', sans-serif",
                }}
              >
                <div style={{
                  display: "flex", alignItems: "center", gap: 6,
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 12, letterSpacing: "0.05em", fontWeight: 700,
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
                    marginTop: 4, fontSize: 12, color: PALETTE.textDim,
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
        </>
        )}
      </div>

      <div style={{ padding: 18, marginTop: "auto", flex: "0 0 auto" }}>
        <Section label="META" />
        <div style={{ marginTop: 10, fontSize: 12, lineHeight: 2, fontFamily: "'JetBrains Mono', monospace", color: PALETTE.textDim }}>
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

// ---------------------------------------------------------------------------
// UiPlan Tasks pinned section
// ---------------------------------------------------------------------------

const TASK_STATUS_COLOR: Record<string, string> = {
  done: "#059669",
  in_progress: "#d97706",
  pending: "#6b7280",
  cancelled: "#9ca3af",
};

function UiplanTasksSection({
  bundles, selectedNodeId, onSelectBundle, onSelectTask,
}: {
  bundles: ProjectNode[];
  selectedNodeId: string | null;
  onSelectBundle?: (id: string) => void;
  onSelectTask?: (taskId: string, bundleId: string) => void;
}) {
  const [collapsed, setCollapsed] = useState(false);
  return (
    <div style={{
      position: "sticky", top: 0, zIndex: 2,
      background: PALETTE.panel,
      borderBottom: `1px solid ${PALETTE.rule}`,
      flexShrink: 0,
    }}>
      <button
        onClick={() => setCollapsed((c) => !c)}
        style={{
          width: "100%", display: "flex", alignItems: "center", gap: 8,
          padding: "12px 16px",
          background: "transparent", border: "none", cursor: "pointer",
          textAlign: "left",
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 12, letterSpacing: "0.22em", fontWeight: 700,
          color: PALETTE.text,
        }}
      >
        {collapsed ? <ChevronRight size={11} /> : <ChevronDown size={11} />}
        <Notebook size={12} color="#0f766e" />
        <span style={{ flex: 1 }}>UIPLAN TASKS</span>
        <span style={{ color: PALETTE.textDim, fontWeight: 600 }}>
          {String(bundles.length).padStart(2, "0")}
        </span>
      </button>
      {!collapsed && (
        <div style={{
          padding: "0 12px 12px",
          maxHeight: 360, overflowY: "auto",
          display: "flex", flexDirection: "column", gap: 6,
        }}>
          {bundles.map((b) => (
            <BundleRow
              key={b.id}
              bundle={b}
              isSelected={b.id === selectedNodeId}
              selectedNodeId={selectedNodeId}
              onSelectBundle={onSelectBundle}
              onSelectTask={onSelectTask}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function BundleRow({
  bundle, isSelected, selectedNodeId, onSelectBundle, onSelectTask,
}: {
  bundle: ProjectNode;
  isSelected: boolean;
  selectedNodeId: string | null;
  onSelectBundle?: (id: string) => void;
  onSelectTask?: (taskId: string, bundleId: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const summary = bundle.task_summary;
  const total = summary?.total ?? 0;
  const done = summary?.done ?? 0;
  const donePct = total > 0 ? (done / total) * 100 : 0;

  // Squash all uiplan_task children across all uiplan_tasks files in the bundle.
  const tasks: ProjectNode[] = [];
  for (const child of bundle.children?.nodes ?? []) {
    if (child.kind === "uiplan_tasks") {
      for (const t of child.children?.nodes ?? []) {
        if (t.kind === "uiplan_task") tasks.push(t);
      }
    } else if (child.kind === "uiplan_task") {
      tasks.push(child);
    }
  }

  return (
    <div style={{
      background: isSelected ? "#ccfbf1" : PALETTE.bg,
      borderTop: `1px solid ${isSelected ? "#0f766e" : PALETTE.rule}`,
      borderRight: `1px solid ${isSelected ? "#0f766e" : PALETTE.rule}`,
      borderBottom: `1px solid ${isSelected ? "#0f766e" : PALETTE.rule}`,
      borderLeft: `3px solid #0f766e`,
      borderRadius: 4, overflow: "hidden",
    }}>
      <div style={{ display: "flex", alignItems: "stretch" }}>
        <button
          onClick={() => onSelectBundle?.(bundle.id)}
          style={{
            flex: 1, padding: "8px 10px",
            background: "transparent", border: "none", cursor: "pointer",
            textAlign: "left", display: "flex", flexDirection: "column", gap: 4,
            fontFamily: "'Inter', sans-serif",
          }}
        >
          <div style={{
            fontSize: 12, fontWeight: 600, color: PALETTE.text,
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
          }}>
            {bundle.label}
          </div>
          {total > 0 && (
            <>
              <div style={{
                height: 4, borderRadius: 2,
                background: PALETTE.rule, overflow: "hidden",
              }}>
                <div style={{
                  width: `${donePct}%`, height: "100%",
                  background: done === total ? "#059669" : "#0f766e",
                }} />
              </div>
              <div style={{
                fontSize: 12, color: PALETTE.textDim,
                fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.1em",
              }}>
                {done}/{total} · {Math.round(donePct)}%
              </div>
            </>
          )}
          {total === 0 && (
            <div style={{
              fontSize: 12, color: PALETTE.textMute,
              fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.1em",
            }}>
              no tasks
            </div>
          )}
        </button>
        {tasks.length > 0 && (
          <button
            onClick={() => setExpanded((v) => !v)}
            title={expanded ? "Collapse" : "Expand"}
            style={{
              padding: "0 10px",
              background: "transparent",
              border: "none",
              borderLeft: `1px solid ${PALETTE.rule}`,
              cursor: "pointer", color: PALETTE.textDim,
            }}
          >
            {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </button>
        )}
      </div>
      {expanded && tasks.length > 0 && (
        <div style={{
          borderTop: `1px solid ${PALETTE.rule}`,
          background: PALETTE.panel,
          display: "flex", flexDirection: "column",
        }}>
          {tasks.map((t) => (
            <TaskRow
              key={t.id}
              task={t}
              isSelected={t.id === selectedNodeId}
              onClick={() => onSelectTask?.(t.id, bundle.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function TaskRow({ task, isSelected, onClick }: {
  task: ProjectNode; isSelected: boolean; onClick: () => void;
}) {
  const status = String(task.meta?.task_status ?? "pending");
  const color = TASK_STATUS_COLOR[status] ?? PALETTE.textDim;
  const Icon = status === "done" ? CheckSquare
    : status === "cancelled" ? MinusSquare
    : status === "in_progress" ? Circle
    : Square;
  const struck = status === "done" || status === "cancelled";
  const line = String(task.meta?.task_line ?? "");
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex", alignItems: "center", gap: 7,
        padding: "6px 9px",
        background: isSelected ? "#ccfbf1" : "transparent",
        border: "none",
        borderTop: `1px dashed ${PALETTE.ruleSoft}`,
        cursor: "pointer", textAlign: "left",
        fontFamily: "'Inter', sans-serif",
      }}
    >
      <Icon size={11} color={color} strokeWidth={2} style={{ flexShrink: 0 }} />
      <span style={{
        flex: 1, fontSize: 12, color: PALETTE.text,
        textDecoration: struck ? "line-through" : "none",
        opacity: struck ? 0.6 : 1,
        overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
      }}>
        {task.label}
      </span>
      {line && (
        <span style={{
          fontSize: 12, fontFamily: "'JetBrains Mono', monospace",
          color: PALETTE.textMute, letterSpacing: "0.05em",
          flexShrink: 0,
        }}>
          L{line}
        </span>
      )}
    </button>
  );
}

function collapseBtnStyle(collapsed: boolean): React.CSSProperties {
  return {
    marginTop: 8,
    width: "100%",
    border: `1px solid ${PALETTE.rule}`,
    borderRadius: 8,
    background: collapsed ? "#f8fafc" : PALETTE.bg,
    color: PALETTE.textDim,
    padding: "6px 8px",
    cursor: "pointer",
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 12,
    letterSpacing: "0.06em",
    fontWeight: 700,
  };
}
