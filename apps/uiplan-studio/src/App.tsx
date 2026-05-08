import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, Loader2, RefreshCw, Sparkles } from "lucide-react";

import Canvas, { type CanvasHandle } from "./components/Canvas";
import UiplanCanvas from "./components/UiplanCanvas";
import SkillsCanvas from "./components/SkillsCanvas";
import LeftRail from "./components/LeftRail";
import Inspector from "./components/Inspector";
import Breadcrumb from "./components/Breadcrumb";
import { findFileNodeId } from "./components/UiplanInspector";
import { LAYERS, PALETTE } from "./theme";
import { computeLayout } from "./layout";
import {
  loadProjectGraph,
  loadWorktrees,
  type LoadGraphResult,
} from "./projectGraph/api";
import type { PathClass, ProjectGraph, ProjectNode, Worktree } from "./projectGraph/types";

import "./styles.css";

const EMPTY_GRAPH: ProjectGraph = { projectType: "—", nodes: [], edges: [], errors: [] };

export default function App() {
  // ---- Worktrees + active project ----
  const [worktrees, setWorktrees] = useState<Worktree[]>([]);
  const [worktreeId, setWorktreeId] = useState<string>(() => {
    // Boot URL may carry ?worktree=<path>, set by `uipath-claude explore`.
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const fromUrl = params.get("worktree");
      if (fromUrl) return fromUrl;
    }
    return "demo";
  });
  const [worktreesLoading, setWorktreesLoading] = useState(true);

  // ---- Graph state ----
  const [rootGraph, setRootGraph] = useState<ProjectGraph>(EMPTY_GRAPH);
  const [graphSource, setGraphSource] = useState<"api" | "sample" | "loading" | "error">("loading");
  const [graphError, setGraphError] = useState<string | undefined>();

  // ---- View state ----
  const [trail, setTrail] = useState<ProjectNode[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [hoveredEdgeId, setHoveredEdgeId] = useState<string | null>(null);
  const [layerFilter, setLayerFilter] = useState<Set<string>>(new Set());
  const [pathFilter, setPathFilter] = useState<Set<PathClass>>(new Set());
  const [issuesOnly, setIssuesOnly] = useState(false);
  const [showSkillCoverage, setShowSkillCoverage] = useState(false);
  const [query, setQuery] = useState("");
  const [inspectorCollapsed, setInspectorCollapsed] = useState(false);
  const [skillsView, setSkillsView] = useState(false);
  const [selectedSkillId, setSelectedSkillId] = useState<string | null>(null);

  const canvasRef = useRef<CanvasHandle | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  // Tracks whether the boot-time "auto-switch off the default sample fixture
  // when the API has real worktrees" has already fired. Without this guard,
  // the worktrees-load effect would re-bounce the user every time they
  // manually picked "Solution · order-to-cash" or any sample fixture from
  // the dropdown.
  const autoSwitchedRef = useRef(false);

  // ---- Load worktrees once ----
  useEffect(() => {
    let cancelled = false;
    loadWorktrees().then((res) => {
      if (cancelled) return;
      const seen = new Set<string>();
      const items: Worktree[] = [];
      for (const w of res.items) {
        if (seen.has(w.id)) continue;
        seen.add(w.id);
        items.push(w);
      }
      // Preserve a worktree the URL pointed at even if the API didn't list it.
      setWorktreeId((current) => {
        if (current && !seen.has(current)) {
          items.push({ id: current, label: current, path: current });
        }
        return current;
      });
      setWorktrees(items);
      setWorktreesLoading(false);

      // First-mount only: if we booted on the default "demo" fixture and the
      // API returned real worktrees, jump to the first real one so the user
      // sees live data without a manual click. After this fires once, never
      // again - so picking any fixture from the dropdown stays sticky.
      if (autoSwitchedRef.current) return;
      autoSwitchedRef.current = true;
      const SAMPLE_IDS = new Set(["demo", "solution", "empty"]);
      setWorktreeId((current) => {
        if (res.source !== "api") return current;
        if (!SAMPLE_IDS.has(current)) return current;
        const firstReal = items.find((w) => !SAMPLE_IDS.has(w.id));
        return firstReal ? firstReal.id : current;
      });
    });
    return () => { cancelled = true; };
  }, []);

  // ---- Load graph when worktreeId changes ----
  const loadGraph = useCallback(async (id: string) => {
    setGraphSource("loading");
    setGraphError(undefined);
    const res: LoadGraphResult = await loadProjectGraph(id);
    setRootGraph(res.graph);
    setGraphSource(res.source);
    setGraphError(res.error);
    setTrail([]);
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setHovered(null);
    setHoveredEdgeId(null);
    setSelectedSkillId(null);
    setSkillsView(false);
  }, []);

  useEffect(() => {
    void loadGraph(worktreeId);
  }, [worktreeId, loadGraph]);

  // ---- Current graph at the active drill-down depth ----
  const currentGraph: ProjectGraph = useMemo(() => {
    if (trail.length === 0) return rootGraph;
    const parent = trail[trail.length - 1];
    return {
      ...rootGraph,
      nodes: parent.children?.nodes ?? [],
      edges: parent.children?.edges ?? [],
      errors: [],
    };
  }, [trail, rootGraph]);

  // Active drill-in bundle, if any. When set, the canvas shows the UiPlan
  // task experience instead of the layered graph.
  const activeBundle: ProjectNode | null = useMemo(() => {
    const head = trail[trail.length - 1];
    return head && head.kind === "uiplan_bundle" ? head : null;
  }, [trail]);

  // Layered-canvas view: filter uiplan_* nodes out so they don't pollute the
  // technical graph. The new UiplanCanvas owns the uiplan view entirely.
  const layeredGraph: ProjectGraph = useMemo(() => {
    const nodes = currentGraph.nodes.filter((n) => !String(n.kind).startsWith("uiplan_"));
    const ids = new Set(nodes.map((n) => n.id));
    const edges = currentGraph.edges.filter((e) => ids.has(e.source) && ids.has(e.target));
    return { ...currentGraph, nodes, edges };
  }, [currentGraph]);

  const layout = useMemo(() => computeLayout(layeredGraph), [layeredGraph]);

  // Bundles for the pinned left-rail section: top-level uiplan_bundle nodes
  // (and any nested bundles inside the active drill-in).
  const bundles: ProjectNode[] = useMemo(() => {
    const seen = new Map<string, ProjectNode>();
    for (const n of rootGraph.nodes) {
      if (n.kind === "uiplan_bundle") seen.set(n.id, n);
    }
    if (activeBundle && !seen.has(activeBundle.id)) {
      seen.set(activeBundle.id, activeBundle);
    }
    return Array.from(seen.values());
  }, [rootGraph, activeBundle]);

  // ---- Drill-down helpers ----
  const drillInto = useCallback((node: ProjectNode) => {
    setTrail((t) => [...t, node]);
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setHovered(null);
    setHoveredEdgeId(null);
    setQuery("");
  }, []);

  const popOne = useCallback(() => {
    setTrail((t) => t.slice(0, -1));
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setHovered(null);
    setHoveredEdgeId(null);
    setQuery("");
  }, []);

  const navigateTo = useCallback((depth: number) => {
    setTrail((t) => t.slice(0, depth));
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setHovered(null);
    setHoveredEdgeId(null);
    setQuery("");
  }, []);

  // ---- Search-driven navigation ----
  const submitSearch = useCallback(() => {
    const q = query.trim().toLowerCase();
    if (!q) return;
    const match = currentGraph.nodes.find((n) =>
      n.label.toLowerCase().includes(q) ||
      n.id.toLowerCase().includes(q) ||
      (n.desc || "").toLowerCase().includes(q));
    if (match) {
      setSelectedNodeId(match.id);
      canvasRef.current?.centerOn(match.id);
    }
  }, [query, currentGraph.nodes]);

  // ---- Keyboard navigation ----
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      // ignore typing in inputs/textareas
      const target = e.target as HTMLElement | null;
      const isTyping = target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable);

      if (e.key === "Escape" && !isTyping) {
        if (selectedEdgeId) { setSelectedEdgeId(null); return; }
        if (selectedNodeId) { setSelectedNodeId(null); return; }
        if (trail.length > 0) { popOne(); return; }
      }
      if (e.key === "/" && !isTyping) {
        e.preventDefault();
        searchInputRef.current?.focus();
        searchInputRef.current?.select();
      }
      if (e.key === "Enter" && selectedNodeId && !isTyping) {
        const node = currentGraph.nodes.find((n) => n.id === selectedNodeId);
        if (node?.children && node.children.nodes.length > 0) {
          drillInto(node);
        }
      }
      // Arrow navigation between connected nodes
      if (!isTyping && (e.key === "ArrowRight" || e.key === "ArrowLeft" || e.key === "ArrowUp" || e.key === "ArrowDown") && selectedNodeId) {
        e.preventDefault();
        const outgoing = currentGraph.edges.filter((edge) => edge.source === selectedNodeId);
        const incoming = currentGraph.edges.filter((edge) => edge.target === selectedNodeId);
        let nextId: string | undefined;
        if (e.key === "ArrowRight" && outgoing[0]) nextId = outgoing[0].target;
        else if (e.key === "ArrowLeft" && incoming[0]) nextId = incoming[0].source;
        else if (e.key === "ArrowDown") {
          // move to next node in same column
          const cur = currentGraph.nodes.find((n) => n.id === selectedNodeId);
          if (cur) {
            const col = currentGraph.nodes.filter((n) => n.layer === cur.layer);
            const idx = col.findIndex((n) => n.id === cur.id);
            nextId = col[Math.min(idx + 1, col.length - 1)]?.id;
          }
        } else if (e.key === "ArrowUp") {
          const cur = currentGraph.nodes.find((n) => n.id === selectedNodeId);
          if (cur) {
            const col = currentGraph.nodes.filter((n) => n.layer === cur.layer);
            const idx = col.findIndex((n) => n.id === cur.id);
            nextId = col[Math.max(idx - 1, 0)]?.id;
          }
        }
        if (nextId && nextId !== selectedNodeId) {
          setSelectedNodeId(nextId);
          canvasRef.current?.centerOn(nextId);
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedNodeId, selectedEdgeId, trail.length, popOne, drillInto, currentGraph]);

  // Selecting a node clears edge selection and vice-versa
  const handleSelectNode = (id: string | null) => {
    setSelectedNodeId(id);
    if (id) {
      setSelectedEdgeId(null);
      setSelectedSkillId(null);
    }
  };
  const selectNodeAndCenter = (id: string) => {
    handleSelectNode(id);
    canvasRef.current?.centerOn(id);
  };
  const handleSelectEdge = (id: string | null) => {
    setSelectedEdgeId(id);
    if (id) setSelectedNodeId(null);
  };

  // ---- UiPlan-specific navigation ----
  const onSelectBundle = useCallback((bundleId: string) => {
    const bundle = rootGraph.nodes.find((n) => n.id === bundleId);
    if (!bundle) return;
    setTrail([bundle]);
    setSelectedNodeId(bundleId);
    setSelectedEdgeId(null);
  }, [rootGraph]);

  const onSelectTask = useCallback((taskId: string, bundleId: string) => {
    const bundle = rootGraph.nodes.find((n) => n.id === bundleId);
    if (bundle) setTrail([bundle]);
    setSelectedNodeId(taskId);
    setSelectedEdgeId(null);
  }, [rootGraph]);

  const onJumpToFile = useCallback((path: string) => {
    const id = findFileNodeId(rootGraph, path);
    if (!id) return;
    setTrail([]);
    setSelectedNodeId(id);
    setSelectedEdgeId(null);
    // Defer until the layered canvas mounts.
    setTimeout(() => canvasRef.current?.centerOn(id), 0);
  }, [rootGraph]);

  const toggleLayer = (layer: string) => {
    setLayerFilter((f) => {
      const next = new Set(f);
      if (next.has(layer)) next.delete(layer);
      else next.add(layer);
      return next;
    });
  };
  const togglePath = (p: PathClass) => {
    setPathFilter((f) => {
      const next = new Set(f);
      if (next.has(p)) next.delete(p);
      else next.add(p);
      return next;
    });
  };

  const skillCount = useMemo(
    () => rootGraph.nodes.filter((n) => n.kind === "skill").length,
    [rootGraph.nodes],
  );

  const onJumpToSkillNode = useCallback((nodeId: string) => {
    setSelectedSkillId(null);
    setSkillsView(false);
    setTrail([]);
    setSelectedNodeId(nodeId);
    setSelectedEdgeId(null);
    setTimeout(() => canvasRef.current?.centerOn(nodeId), 0);
  }, []);

  const handleSelectSkill = useCallback((id: string | null) => {
    setSelectedSkillId(id);
    if (id) setSelectedNodeId(null);
  }, []);

  const activeWorktree = worktrees.find((w) => w.id === worktreeId);
  const meta = rootGraph.meta;
  const errorCount = rootGraph.errors?.filter((e) => e.severity === "error").length ?? 0;
  const warnCount = rootGraph.errors?.filter((e) => e.severity === "warn").length ?? 0;

  return (
    <div style={{
      width: "100%", height: "100vh",
      background: PALETTE.bg, color: PALETTE.text,
      display: "flex", flexDirection: "column", overflow: "hidden",
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Newsreader:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet" />

      {/* TOP STRIP — real metadata, worktree selector */}
      <div style={{
        height: 44, borderBottom: `1px solid ${PALETTE.rule}`,
        background: PALETTE.panel,
        display: "flex", alignItems: "center", padding: "0 16px", flexShrink: 0, gap: 16,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ display: "flex", gap: 2 }}>
            {Object.values(LAYERS).slice(0, 4).map((l, i) => (
              <div key={i} style={{ width: 5, height: 14, background: l.color, borderRadius: 1 }} />
            ))}
          </div>
          <div style={{
            fontSize: 11, letterSpacing: "0.32em", fontWeight: 700, color: PALETTE.text,
            fontFamily: "'JetBrains Mono', monospace",
          }}>
            UIPLAN&nbsp;·&nbsp;EXPLORER
          </div>
        </div>

        {/* Worktree dropdown */}
        <div style={{ position: "relative" }}>
          <select
            value={worktreeId}
            onChange={(e) => setWorktreeId(e.target.value)}
            disabled={worktreesLoading}
            style={{
              appearance: "none",
              background: PALETTE.bg,
              border: `1px solid ${PALETTE.rule}`,
              borderRadius: 4,
              padding: "6px 28px 6px 10px",
              fontSize: 11, fontFamily: "'JetBrains Mono', monospace",
              color: PALETTE.text, fontWeight: 600,
              cursor: worktreesLoading ? "wait" : "pointer",
              minWidth: 180,
            }}
          >
            {worktreesLoading && <option>loading…</option>}
            {worktrees.map((w) => (
              <option key={w.id} value={w.id}>
                {w.label} {w.branch ? `(${w.branch})` : ""}
              </option>
            ))}
          </select>
          <ChevronDown size={12} style={{
            position: "absolute", right: 8, top: "50%", transform: "translateY(-50%)",
            color: PALETTE.textDim, pointerEvents: "none",
          }} />
        </div>

        <button
          onClick={() => loadGraph(worktreeId)}
          title="Re-index"
          style={{
            background: PALETTE.bg,
            border: `1px solid ${PALETTE.rule}`,
            borderRadius: 4, padding: "6px 10px",
            cursor: "pointer", color: PALETTE.text,
            display: "flex", alignItems: "center", gap: 6,
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 10, letterSpacing: "0.15em", fontWeight: 600,
          }}
        >
          {graphSource === "loading"
            ? <Loader2 size={11} className="spin" style={{ animation: "spin 1s linear infinite" }} />
            : <RefreshCw size={11} />}
          REFRESH
        </button>

        <button
          onClick={() => {
            setSkillsView((v) => {
              const next = !v;
              if (next) setSelectedSkillId(null);
              return next;
            });
          }}
          title={skillsView ? "Back to graph" : "Open skills view"}
          style={{
            background: skillsView ? "#ccfbf1" : PALETTE.bg,
            border: `1px solid ${skillsView ? "#0f766e" : PALETTE.rule}`,
            borderRadius: 4, padding: "6px 10px",
            cursor: "pointer",
            color: skillsView ? "#0f766e" : PALETTE.text,
            display: "flex", alignItems: "center", gap: 6,
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 10, letterSpacing: "0.15em", fontWeight: 700,
          }}
        >
          <Sparkles size={11} />
          SKILLS
          <span style={{
            background: skillsView ? "#0f766e22" : PALETTE.panel,
            color: skillsView ? "#0f766e" : PALETTE.textDim,
            padding: "1px 6px", borderRadius: 3,
            fontSize: 9.5, letterSpacing: "0.05em",
          }}>
            {String(skillCount).padStart(2, "0")}
          </span>
        </button>

        <div style={{ flex: 1 }} />

        {/* Real metadata strip */}
        <div style={{
          display: "flex", gap: 18, fontSize: 10,
          color: PALETTE.textDim, letterSpacing: "0.12em",
          fontFamily: "'JetBrains Mono', monospace",
          alignItems: "center",
        }}>
          {activeWorktree?.branch && (
            <span title="Git branch">BRANCH&nbsp;·&nbsp;<span style={{ color: PALETTE.text, fontWeight: 600 }}>{activeWorktree.branch}</span></span>
          )}
          {meta?.revision && (
            <span title="Indexer revision">REV&nbsp;·&nbsp;<span style={{ color: PALETTE.text, fontWeight: 600 }}>{meta.revision}</span></span>
          )}
          <span title="Source of the loaded graph" style={{
            color: graphSource === "api" ? "#059669" : graphSource === "sample" ? "#d97706" : PALETTE.textDim,
            fontWeight: 700,
          }}>
            {graphSource === "loading" ? "LOADING" : graphSource === "api" ? "LIVE" : graphSource === "error" ? "ERROR" : "SAMPLE"}
          </span>
          {errorCount > 0 && (
            <span style={{ color: "#dc2626", fontWeight: 700 }}>{errorCount} ERR</span>
          )}
          {warnCount > 0 && (
            <span style={{ color: "#d97706", fontWeight: 700 }}>{warnCount} WARN</span>
          )}
        </div>
      </div>

      {/* MAIN */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden", minHeight: 0 }}>
        <LeftRail
          graph={layeredGraph}
          bundles={bundles}
          selectedNodeId={selectedNodeId}
          query={query} setQuery={setQuery}
          layerFilter={layerFilter} toggleLayer={toggleLayer}
          pathFilter={pathFilter} togglePath={togglePath}
          issuesOnly={issuesOnly} setIssuesOnly={setIssuesOnly}
          showSkillCoverage={showSkillCoverage}
          setShowSkillCoverage={setShowSkillCoverage}
          onSelectNode={selectNodeAndCenter}
          onSelectBundle={onSelectBundle}
          onSelectTask={onSelectTask}
          searchInputRef={searchInputRef}
          onSubmitSearch={submitSearch}
        />

        <div style={{ flex: 1, position: "relative", minWidth: 0 }}>
          {graphSource === "loading" && (
            <LoadingOverlay />
          )}
          {graphSource !== "loading" && !skillsView && !activeBundle && layeredGraph.nodes.length === 0 && (
            <EmptyState worktreeId={worktreeId} onRefresh={() => loadGraph(worktreeId)} />
          )}
          {skillsView && (
            <SkillsCanvas
              graph={rootGraph}
              selectedSkillId={selectedSkillId}
              onSelectSkill={handleSelectSkill}
            />
          )}
          {!skillsView && activeBundle && (
            <UiplanCanvas
              key={activeBundle.id}
              bundle={activeBundle}
              selectedNodeId={selectedNodeId}
              onSelectNode={(id) => setSelectedNodeId(id)}
            />
          )}
          {!skillsView && !activeBundle && layeredGraph.nodes.length > 0 && (
            <Canvas
              ref={canvasRef}
              key={trail.map((t) => t.id).join("/") || worktreeId}
              graph={layeredGraph}
              layout={layout}
              selectedNodeId={selectedNodeId}
              selectedEdgeId={selectedEdgeId}
              hovered={hovered}
              hoveredEdgeId={hoveredEdgeId}
              query={query}
              layerFilter={layerFilter}
              pathFilter={pathFilter}
              issuesOnly={issuesOnly}
              showSkillCoverage={showSkillCoverage}
              onSelectNode={handleSelectNode}
              onSelectEdge={handleSelectEdge}
              onHoverNode={setHovered}
              onHoverEdge={setHoveredEdgeId}
              onDrillDown={drillInto}
            />
          )}
          <Breadcrumb trail={trail} onNavigate={navigateTo} onBack={popOne} />
          {graphError && graphSource === "sample" && (
            <div style={{
              position: "absolute", top: 12, right: 12,
              background: "#fffbeb", border: "1px solid #fde68a",
              borderLeft: "3px solid #d97706",
              padding: "8px 12px", borderRadius: 4,
              fontSize: 11, color: "#92400e",
              fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.1em",
              maxWidth: 320,
            }}>
              indexer offline ({graphError}) — showing sample graph
            </div>
          )}
        </div>

        <Inspector
          graph={currentGraph}
          rootGraph={rootGraph}
          selectedNodeId={selectedNodeId}
          selectedEdgeId={selectedEdgeId}
          selectedSkillId={selectedSkillId}
          worktreeId={worktreeId}
          collapsed={inspectorCollapsed}
          onToggleCollapsed={() => setInspectorCollapsed((c) => !c)}
          onSelectNode={handleSelectNode}
          onSelectEdge={handleSelectEdge}
          onSelectSkill={handleSelectSkill}
          onJumpToSkillNode={onJumpToSkillNode}
          onDrillDown={drillInto}
          onJumpToFile={onJumpToFile}
        />
      </div>

      {/* BOTTOM STATUS BAR — actionable signal only */}
      <div style={{
        height: 26, borderTop: `1px solid ${PALETTE.rule}`,
        background: PALETTE.panel,
        display: "flex", alignItems: "center", padding: "0 16px",
        fontSize: 9.5, color: PALETTE.textDim, letterSpacing: "0.14em", flexShrink: 0,
        fontFamily: "'JetBrains Mono', monospace", gap: 18,
      }}>
        <span>WORKTREE&nbsp;·&nbsp;<span style={{ color: PALETTE.text, fontWeight: 600 }}>{activeWorktree?.label ?? worktreeId}</span></span>
        {meta?.indexed_at && (
          <span>INDEXED&nbsp;·&nbsp;<span style={{ color: PALETTE.text }}>{formatTimestamp(meta.indexed_at)}</span></span>
        )}
        <span>NODES&nbsp;·&nbsp;<span style={{ color: PALETTE.text }}>{rootGraph.nodes.length}</span></span>
        <span>EDGES&nbsp;·&nbsp;<span style={{ color: PALETTE.text }}>{rootGraph.edges.length}</span></span>
        <span style={{ marginLeft: "auto", color: PALETTE.text, fontWeight: 600 }}>
          {selectedNodeId
            ? `→ ${selectedNodeId}`
            : selectedEdgeId
              ? `~ ${selectedEdgeId}`
              : trail.length > 0
                ? `INSIDE → ${trail[trail.length - 1].id}`
                : "—"}
        </span>
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

function LoadingOverlay() {
  return (
    <div style={{
      position: "absolute", inset: 0,
      display: "flex", alignItems: "center", justifyContent: "center",
      background: PALETTE.bg, zIndex: 5,
      flexDirection: "column", gap: 12,
      color: PALETTE.textDim,
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: 11, letterSpacing: "0.18em",
    }}>
      <Loader2 size={20} style={{ animation: "spin 1s linear infinite" }} />
      <span>INDEXING PROJECT…</span>
    </div>
  );
}

function EmptyState({ worktreeId, onRefresh }: { worktreeId: string; onRefresh: () => void }) {
  return (
    <div style={{
      position: "absolute", inset: 0,
      display: "flex", alignItems: "center", justifyContent: "center",
      flexDirection: "column", gap: 16,
      color: PALETTE.textDim, padding: 32,
    }}>
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11, letterSpacing: "0.22em", fontWeight: 700,
        color: PALETTE.text,
      }}>
        NO NODES IN THIS VIEW
      </div>
      <div style={{
        fontFamily: "'Newsreader', Georgia, serif",
        fontSize: 13, fontStyle: "italic", maxWidth: 360, textAlign: "center", lineHeight: 1.5,
      }}>
        The current worktree (<span style={{ color: PALETTE.text }}>{worktreeId}</span>) returned no graph.
        Either no project files matched the indexer, or the sub-graph has no children.
      </div>
      <button onClick={onRefresh} style={{
        background: PALETTE.panel, border: `1px solid ${PALETTE.rule}`,
        borderRadius: 4, padding: "8px 16px", cursor: "pointer",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 10, letterSpacing: "0.18em", fontWeight: 700,
        color: PALETTE.text,
        display: "flex", alignItems: "center", gap: 8,
      }}>
        <RefreshCw size={11} />
        RE-INDEX
      </button>
    </div>
  );
}

function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso);
    const diffMs = Date.now() - d.getTime();
    const sec = Math.floor(diffMs / 1000);
    if (sec < 5) return "just now";
    if (sec < 60) return `${sec}s ago`;
    if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
    if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
    return d.toLocaleDateString();
  } catch {
    return iso;
  }
}
