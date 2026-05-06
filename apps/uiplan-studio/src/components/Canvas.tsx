import React, { useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState, forwardRef } from "react";
import { AlertTriangle, Hand, Maximize2 } from "lucide-react";

import {
  EDGE_STYLE,
  KIND_ICONS,
  LAYERS,
  NODE_H,
  NODE_W,
  PALETTE,
  STATUS_COLOR,
  getEdgeStyle,
  getLayer,
} from "../theme";
import type { Layout } from "../layout";
import type { ProjectEdge, ProjectGraph, ProjectNode } from "../projectGraph/types";

export interface CanvasHandle {
  /** Pan + zoom so the given node is centered. */
  centerOn: (nodeId: string) => void;
  /** Reset to fit-to-content. */
  resetView: () => void;
}

interface CanvasProps {
  graph: ProjectGraph;
  layout: Layout;
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  hovered: string | null;
  hoveredEdgeId: string | null;
  query: string;
  layerFilter: Set<string>;
  pathFilter: Set<string>;
  issuesOnly: boolean;
  showSkillCoverage: boolean;
  onSelectNode: (id: string | null) => void;
  onSelectEdge: (id: string | null) => void;
  onHoverNode: (id: string | null) => void;
  onHoverEdge: (id: string | null) => void;
  onDrillDown: (node: ProjectNode) => void;
}

interface NodeCardProps {
  node: ProjectNode;
  isSelected: boolean;
  isHovered: boolean;
  isAdjacent: boolean;
  isDimmed: boolean;
  hasError: boolean;
  onClick: (e: React.MouseEvent) => void;
  onDoubleClick: (e: React.MouseEvent) => void;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
}

function NodeCard({
  node, isSelected, isHovered, isAdjacent, isDimmed, hasError,
  onClick, onDoubleClick, onMouseEnter, onMouseLeave,
}: NodeCardProps) {
  const layer = getLayer(node.layer);
  const KindIcon = KIND_ICONS[node.kind] || ((null as unknown) as React.ComponentType<{size?:number;color?:string;strokeWidth?:number}>);
  const hasChildren = !!(node.children && node.children.nodes && node.children.nodes.length > 0);
  const status = node.status ?? "ok";
  const statusColor = STATUS_COLOR[status];
  const isHitl = node.roles?.includes("hitl") || node.roles?.includes("approval");
  const isSkill = node.kind === "skill";

  return (
    <foreignObject
      width={NODE_W + 12}
      height={NODE_H + 12}
      style={{
        overflow: "visible",
        cursor: "pointer",
        opacity: isDimmed ? 0.18 : 1,
        transition: "opacity 0.15s",
      }}
      data-node={node.id}
      onClick={onClick}
      onDoubleClick={onDoubleClick}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      <div
        title={node.desc}
        style={{
          width: NODE_W, height: NODE_H, position: "relative",
          background: isSkill ? "linear-gradient(135deg, #ffffff 0%, #faf5ff 100%)" : PALETTE.panel,
          border: `1px solid ${isSelected ? layer.color : isHovered || isAdjacent ? layer.color : PALETTE.rule}`,
          borderRadius: 8,
          boxShadow: isSelected
            ? `0 0 0 3px ${layer.soft}, 0 4px 12px rgba(0,0,0,0.08)`
            : isHovered
              ? "0 4px 10px rgba(0,0,0,0.06)"
              : isSkill
                ? "0 2px 8px rgba(139,92,246,0.10)"
                : "0 1px 2px rgba(0,0,0,0.04)",
          display: "flex", overflow: "visible",
          transition: "all 0.12s",
          fontFamily: "'Inter', system-ui, sans-serif",
        }}
      >
        {hasChildren && (
          <>
            <div style={{ position: "absolute", top: 4, left: 4, right: -4, bottom: -4, background: PALETTE.panel, border: `1px solid ${PALETTE.rule}`, borderRadius: 8, zIndex: -1, opacity: 0.6 }} />
            <div style={{ position: "absolute", top: 7, left: 7, right: -7, bottom: -7, background: PALETTE.panel, border: `1px solid ${PALETTE.rule}`, borderRadius: 8, zIndex: -2, opacity: 0.3 }} />
          </>
        )}

        <div style={{
          width: 56, height: "100%",
          background: layer.soft,
          borderRight: `1px solid ${PALETTE.rule}`,
          borderTopLeftRadius: 7, borderBottomLeftRadius: 7,
          display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
        }}>
          {KindIcon && <KindIcon size={22} color={layer.color} strokeWidth={1.6} />}
        </div>

        <div style={{ flex: 1, padding: "10px 12px", display: "flex", flexDirection: "column", justifyContent: "center", minWidth: 0 }}>
          <div style={{
            fontSize: 8.5, letterSpacing: "0.18em", fontWeight: 700,
            color: layer.color, marginBottom: 3,
            fontFamily: "'JetBrains Mono', monospace",
            display: "flex", alignItems: "center", gap: 6,
          }}>
            <span>{layer.short} · {node.kind.replace("_", " ").toUpperCase()}</span>
            {hasChildren && (
              <span style={{
                background: layer.color, color: "#fff",
                padding: "1px 5px", borderRadius: 3,
                fontSize: 7.5, letterSpacing: "0.08em", fontWeight: 700,
              }}>
                {node.children!.nodes.length}
              </span>
            )}
            {isHitl && (
              <span title="Human-in-the-loop pause point" style={{
                background: "#dc2626", color: "#fff",
                padding: "1px 5px", borderRadius: 3,
                fontSize: 7.5, letterSpacing: "0.08em", fontWeight: 700,
              }}>
                HITL
              </span>
            )}
          </div>
          <div style={{
            fontSize: 13, fontWeight: 600, color: PALETTE.text,
            whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
            letterSpacing: "-0.005em",
            display: "flex", alignItems: "center", gap: 6,
          }}>
            <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {node.label}
            </span>
            <span title={`status: ${status}`} style={{
              flexShrink: 0,
              width: 8, height: 8, borderRadius: "50%",
              background: statusColor,
              boxShadow: `0 0 0 1.5px #fff, 0 0 0 2.5px ${statusColor}55`,
            }} />
          </div>
          {node.desc && (
            <div style={{
              fontSize: 10.5, color: PALETTE.textDim, marginTop: 2,
              whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
            }}>
              {node.desc.split(".")[0]}
            </div>
          )}
        </div>

        {hasChildren && (
          <div
            onClick={(e) => { e.stopPropagation(); onDoubleClick(e); }}
            style={{
              position: "absolute", top: -7, right: -7,
              width: 22, height: 22,
              background: PALETTE.panel,
              border: `1.5px solid ${layer.color}`,
              borderRadius: 5,
              display: "flex", alignItems: "center", justifyContent: "center",
              cursor: "pointer",
              boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
            }}
            title="Open sub-graph"
          >
            <Maximize2 size={11} color={layer.color} strokeWidth={2.4} />
          </div>
        )}

        {hasError && (
          <div title="Has error or warning" style={{
            position: "absolute", top: -4, left: -4,
            width: 12, height: 12, borderRadius: "50%",
            background: "#dc2626", border: "2px solid #fff",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <AlertTriangle size={6} color="#fff" strokeWidth={3} />
          </div>
        )}
      </div>
    </foreignObject>
  );
}

const Canvas = forwardRef<CanvasHandle, CanvasProps>(function Canvas({
  graph, layout,
  selectedNodeId, selectedEdgeId, hovered, hoveredEdgeId,
  query, layerFilter, pathFilter, issuesOnly, showSkillCoverage,
  onSelectNode, onSelectEdge, onHoverNode, onHoverEdge, onDrillDown,
}, ref) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [transform, setTransform] = useState({ x: 0, y: 0, k: 1 });
  const [size, setSize] = useState({ w: 1000, h: 600 });
  const [didFit, setDidFit] = useState(false);
  const drag = useRef<{ x: number; y: number; t: typeof transform } | null>(null);
  const [edgeTooltip, setEdgeTooltip] = useState<{ x: number; y: number; edge: ProjectEdge } | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver(() => {
      const r = containerRef.current!.getBoundingClientRect();
      setSize({ w: r.width, h: r.height });
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  const fitView = useCallback(() => {
    const padding = 60;
    const kx = (size.w - padding * 2) / Math.max(layout.width, 1);
    const ky = (size.h - padding * 2) / Math.max(layout.height, 1);
    const k = Math.min(kx, ky, 1);
    const x = (size.w - layout.width * k) / 2;
    const y = (size.h - layout.height * k) / 2;
    setTransform({ x, y, k });
  }, [size.w, size.h, layout.width, layout.height]);

  useEffect(() => {
    if (didFit || size.w < 100) return;
    fitView();
    setDidFit(true);
  }, [didFit, fitView, size.w]);

  // Re-fit when the underlying graph identity changes (e.g. drill-down)
  useEffect(() => {
    setDidFit(false);
  }, [layout.width, layout.height]);

  useImperativeHandle(ref, () => ({
    centerOn: (nodeId: string) => {
      const pos = layout.positions[nodeId];
      if (!pos) return;
      const k = Math.max(transform.k, 0.85);
      const x = size.w / 2 - (pos.x + NODE_W / 2) * k;
      const y = size.h / 2 - (pos.y + NODE_H / 2) * k;
      setTransform({ x, y, k });
    },
    resetView: () => fitView(),
  }), [layout.positions, transform.k, size.w, size.h, fitView]);

  const onWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const rect = containerRef.current!.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const factor = e.deltaY < 0 ? 1.12 : 0.89;
    setTransform((t) => {
      const k = Math.max(0.25, Math.min(2.5, t.k * factor));
      const x = mx - ((mx - t.x) * k) / t.k;
      const y = my - ((my - t.y) * k) / t.k;
      return { x, y, k };
    });
  }, []);

  const onMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest("[data-node]")) return;
    if ((e.target as HTMLElement).closest("[data-edge]")) return;
    drag.current = { x: e.clientX, y: e.clientY, t: transform };
  };
  const onMouseMove = (e: React.MouseEvent) => {
    if (!drag.current) return;
    const dx = e.clientX - drag.current.x;
    const dy = e.clientY - drag.current.y;
    setTransform({ ...drag.current.t, x: drag.current.t.x + dx, y: drag.current.t.y + dy });
  };
  const onMouseUp = () => { drag.current = null; };

  const issueNodeIds = useMemo(() => {
    const ids = new Set<string>();
    (graph.errors || []).forEach((e) => ids.add(e.nodeId));
    graph.nodes.forEach((n) => {
      if (n.status === "error" || n.status === "warn") ids.add(n.id);
    });
    return ids;
  }, [graph]);

  const visibleNodeIds = useMemo(() => {
    const q = query.trim().toLowerCase();
    return new Set(
      graph.nodes
        .filter((n) => layerFilter.size === 0 || layerFilter.has(n.layer))
        .filter((n) => !issuesOnly || issueNodeIds.has(n.id))
        .filter((n) => !q || n.label.toLowerCase().includes(q) || n.id.toLowerCase().includes(q) || (n.desc || "").toLowerCase().includes(q))
        .map((n) => n.id),
    );
  }, [graph, layerFilter, query, issuesOnly, issueNodeIds]);

  const matchingHighlight = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return new Set<string>();
    return new Set(
      graph.nodes
        .filter((n) => n.label.toLowerCase().includes(q) || n.id.toLowerCase().includes(q) || (n.desc || "").toLowerCase().includes(q))
        .map((n) => n.id),
    );
  }, [graph, query]);

  // Adjacency for hover-dim — when a node is hovered, fade everything not directly connected.
  const adjacency = useMemo(() => {
    const adjNodes = new Set<string>();
    const adjEdges = new Set<string>();
    const focus = hovered ?? selectedNodeId;
    if (!focus) return { adjNodes, adjEdges };
    adjNodes.add(focus);
    graph.edges.forEach((e) => {
      if (e.source === focus) { adjEdges.add(e.id); adjNodes.add(e.target); }
      if (e.target === focus) { adjEdges.add(e.id); adjNodes.add(e.source); }
    });
    return { adjNodes, adjEdges };
  }, [graph.edges, hovered, selectedNodeId]);

  const renderEdge = (edge: ProjectEdge) => {
    const a = layout.positions[edge.source];
    const b = layout.positions[edge.target];
    if (!a || !b) return null;
    if (!visibleNodeIds.has(edge.source) || !visibleNodeIds.has(edge.target)) return null;
    if (edge.kind === "covers" && !showSkillCoverage) return null;
    if (edge.kind !== "covers" && pathFilter.size > 0 && (!edge.path_class || !pathFilter.has(edge.path_class))) return null;

    const ax = a.x + NODE_W;
    const ay = a.y + NODE_H / 2;
    const bx = b.x;
    const by = b.y + NODE_H / 2;

    const style = getEdgeStyle(edge.kind);
    const focus = hovered ?? selectedNodeId;
    const isAdjacent = focus ? adjacency.adjEdges.has(edge.id) : false;
    const isHoveredEdge = hoveredEdgeId === edge.id;
    const isSelectedEdge = selectedEdgeId === edge.id;
    const isActive = isAdjacent || isHoveredEdge || isSelectedEdge;
    const fadedByFocus = !!focus && !isAdjacent;
    const fadedByQuery =
      matchingHighlight.size > 0 && !matchingHighlight.has(edge.source) && !matchingHighlight.has(edge.target);
    const opacity = fadedByQuery ? 0.08 : fadedByFocus ? 0.18 : isActive ? 1 : 0.5;

    const dx = Math.max(60, (bx - ax) * 0.55);
    const path = `M ${ax} ${ay} C ${ax + dx} ${ay}, ${bx - dx} ${by}, ${bx} ${by}`;
    const strokeWidth = isSelectedEdge ? style.width + 1.6 : isActive ? style.width + 0.8 : style.width;

    return (
      <g key={edge.id} data-edge={edge.id} style={{ opacity, transition: "opacity 0.15s, stroke-width 0.15s", cursor: "pointer" }}
         onClick={(e) => { e.stopPropagation(); onSelectEdge(edge.id); }}
         onMouseEnter={(e) => {
           onHoverEdge(edge.id);
           const rect = containerRef.current!.getBoundingClientRect();
           setEdgeTooltip({ x: e.clientX - rect.left, y: e.clientY - rect.top, edge });
         }}
         onMouseMove={(e) => {
           const rect = containerRef.current!.getBoundingClientRect();
           setEdgeTooltip({ x: e.clientX - rect.left, y: e.clientY - rect.top, edge });
         }}
         onMouseLeave={() => { onHoverEdge(null); setEdgeTooltip(null); }}>
        {/* invisible thick path for easier hovering */}
        <path d={path} fill="none" stroke="transparent" strokeWidth={14} pointerEvents="stroke" />
        <path d={path} fill="none" stroke={style.color} strokeWidth={strokeWidth} strokeDasharray={style.dash} markerEnd={`url(#arrow-${edge.kind})`} />
        <circle cx={ax} cy={ay} r={isActive ? 4 : 3} fill={style.color} stroke={PALETTE.bg} strokeWidth="1.5" />
        <circle cx={bx} cy={by} r={isActive ? 4 : 3} fill={style.color} stroke={PALETTE.bg} strokeWidth="1.5" />
        {edge.label && (
          <g transform={`translate(${(ax + bx) / 2}, ${(ay + by) / 2})`}>
            <rect x="-30" y="-9" width="60" height="18" rx="3" fill={PALETTE.bg} stroke={style.color} strokeWidth="1" />
            <text fontSize="9" fill={style.color} textAnchor="middle" y="3.5" style={{ fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.1em", fontWeight: 600 }}>
              {edge.label.toUpperCase()}
            </text>
          </g>
        )}
      </g>
    );
  };

  const renderNode = (node: ProjectNode) => {
    const pos = layout.positions[node.id];
    if (!pos) return null;
    if (!visibleNodeIds.has(node.id)) return null;

    const isSelected = selectedNodeId === node.id;
    const isHovered = hovered === node.id;
    const isMatching = matchingHighlight.has(node.id);
    const focus = hovered ?? selectedNodeId;
    const isAdjacent = focus ? adjacency.adjNodes.has(node.id) && node.id !== focus : false;
    const fadedByFocus = !!focus && focus !== node.id && !adjacency.adjNodes.has(node.id);
    const fadedByQuery = matchingHighlight.size > 0 && !isMatching;
    const isDimmed = fadedByFocus || fadedByQuery;
    const hasError = !!graph.errors?.some((e) => e.nodeId === node.id && (e.severity === "error" || e.severity === "warn"));

    return (
      <g key={node.id} transform={`translate(${pos.x}, ${pos.y})`}>
        <NodeCard
          node={node}
          isSelected={isSelected}
          isHovered={isHovered}
          isAdjacent={isAdjacent}
          isDimmed={isDimmed}
          hasError={hasError}
          onClick={(e) => { e.stopPropagation(); onSelectNode(node.id); }}
          onDoubleClick={(e) => {
            e.stopPropagation();
            if (node.children && node.children.nodes.length > 0) onDrillDown(node);
          }}
          onMouseEnter={() => onHoverNode(node.id)}
          onMouseLeave={() => onHoverNode(null)}
        />
      </g>
    );
  };

  return (
    <div
      ref={containerRef}
      onWheel={onWheel}
      onMouseDown={onMouseDown}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseUp}
      onClick={() => { onSelectNode(null); onSelectEdge(null); }}
      style={{
        width: "100%", height: "100%", position: "relative",
        background: PALETTE.bg,
        cursor: drag.current ? "grabbing" : "grab",
        overflow: "hidden",
      }}
    >
      <svg width={size.w} height={size.h} style={{ display: "block" }}>
        <defs>
          {Object.entries(EDGE_STYLE).map(([kind, s]) => (
            <marker key={kind} id={`arrow-${kind}`} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 0 L 8 4 L 0 8 z" fill={s.color} />
            </marker>
          ))}
          <pattern id="grid-dots" width="22" height="22" patternUnits="userSpaceOnUse">
            <circle cx="0.5" cy="0.5" r="0.6" fill="#d4d4d0" />
          </pattern>
        </defs>

        <rect width="100%" height="100%" fill="url(#grid-dots)" />

        <g transform={`translate(${transform.x}, ${transform.y}) scale(${transform.k})`}>
          {layout.cols.map((layerKey, i) => {
            const layer = LAYERS[layerKey];
            const x = 60 + i * layout.colW - 30;
            return (
              <rect key={layerKey} x={x} y={50} width={NODE_W + 60} height={Math.max(layout.height - 100, 0)}
                fill={layer.soft} opacity="0.18"
                stroke={layer.color} strokeOpacity="0.12" strokeWidth="1" strokeDasharray="2 4" />
            );
          })}

          {layout.cols.map((layerKey, i) => {
            const layer = LAYERS[layerKey];
            const x = 60 + i * layout.colW;
            const count = layout.buckets[layerKey].length;
            const HeaderIcon = layer.Icon;
            return (
              <g key={layerKey} transform={`translate(${x}, 32)`}>
                <foreignObject width={NODE_W} height={28} style={{ overflow: "visible" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: "'JetBrains Mono', monospace" }}>
                    <div style={{ width: 22, height: 22, borderRadius: 4, background: layer.soft, border: `1px solid ${layer.color}33`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <HeaderIcon size={12} color={layer.color} strokeWidth={2} />
                    </div>
                    <div style={{ fontSize: 10, letterSpacing: "0.25em", fontWeight: 700, color: layer.color }}>
                      {layer.name.toUpperCase()}
                    </div>
                    <div style={{ fontSize: 9, color: PALETTE.textMute, letterSpacing: "0.1em" }}>
                      / {String(count).padStart(2, "0")}
                    </div>
                  </div>
                </foreignObject>
                <line x1="-20" y1="32" x2={NODE_W + 20} y2="32" stroke={layer.color} strokeOpacity="0.3" strokeWidth="0.5" />
              </g>
            );
          })}

          {graph.edges.map(renderEdge)}
          {graph.nodes.map(renderNode)}
        </g>
      </svg>

      {/* Edge tooltip */}
      {edgeTooltip && (
        <div style={{
          position: "absolute",
          top: edgeTooltip.y + 14,
          left: edgeTooltip.x + 14,
          pointerEvents: "none",
          background: PALETTE.panel,
          border: `1px solid ${PALETTE.rule}`,
          borderLeft: `3px solid ${getEdgeStyle(edgeTooltip.edge.kind).color}`,
          padding: "8px 12px", borderRadius: 4,
          fontSize: 11, lineHeight: 1.5,
          color: PALETTE.text, maxWidth: 280,
          boxShadow: "0 6px 18px rgba(0,0,0,0.08)",
          fontFamily: "'Inter', sans-serif",
          zIndex: 20,
        }}>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 9, letterSpacing: "0.18em", fontWeight: 700,
            color: getEdgeStyle(edgeTooltip.edge.kind).color, marginBottom: 4,
          }}>
            {edgeTooltip.edge.kind.toUpperCase()}
            {edgeTooltip.edge.label ? ` · ${edgeTooltip.edge.label}` : ""}
          </div>
          <div>
            <span style={{ color: PALETTE.textDim }}>{edgeTooltip.edge.source}</span>
            <span style={{ color: PALETTE.textMute, margin: "0 6px" }}>→</span>
            <span style={{ color: PALETTE.textDim }}>{edgeTooltip.edge.target}</span>
          </div>
          {edgeTooltip.edge.desc && (
            <div style={{ marginTop: 4, color: PALETTE.textDim }}>{edgeTooltip.edge.desc}</div>
          )}
        </div>
      )}

      {/* Zoom + reset */}
      <div style={{ position: "absolute", bottom: 16, left: 16, display: "flex", gap: 6 }}>
        <div style={{
          fontSize: 10, fontFamily: "'JetBrains Mono', monospace",
          color: PALETTE.textDim, letterSpacing: "0.15em",
          background: PALETTE.panel, padding: "4px 8px",
          border: `1px solid ${PALETTE.rule}`, borderRadius: 4,
        }}>
          {(transform.k * 100).toFixed(0)}%
        </div>
        <button onClick={fitView} title="Fit to view" style={{
          fontSize: 10, fontFamily: "'JetBrains Mono', monospace",
          color: PALETTE.text, letterSpacing: "0.15em",
          background: PALETTE.panel, padding: "4px 8px",
          border: `1px solid ${PALETTE.rule}`, borderRadius: 4,
          cursor: "pointer", fontWeight: 600,
          display: "flex", alignItems: "center", gap: 5,
        }}>
          <Hand size={11} />
          FIT
        </button>
      </div>
    </div>
  );
});

export default Canvas;
