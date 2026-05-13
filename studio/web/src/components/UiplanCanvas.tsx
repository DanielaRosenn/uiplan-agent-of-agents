import React, { useMemo, useState, useEffect, useRef } from "react";
import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: false,
  theme: "default",
  themeVariables: {
    primaryColor: "#e0f2fe",
    primaryBorderColor: "#0284c7",
    primaryTextColor: "#0c4a6e",
    lineColor: "#64748b",
    fontFamily: "Inter, sans-serif",
    fontSize: "13px",
  },
  flowchart: { useMaxWidth: true, htmlLabels: true },
  sequence: { useMaxWidth: true },
});
import {
  BookOpen,
  CheckSquare,
  Circle,
  FileText,
  KeyRound,
  ListChecks,
  MinusSquare,
  RotateCcw,
  Settings2,
  Square,
  Target,
  Users,
  Workflow as WorkflowIcon,
} from "lucide-react";

import { PALETTE } from "../theme";
import type { ProjectNode, AsIsView, ToBeView } from "../projectGraph/types";
import AsIsCanvas from "./AsIsCanvas";
import ToBeCanvas from "./ToBeCanvas";

const TASK_STATUS_COLOR: Record<string, string> = {
  done: "#059669",
  in_progress: "#d97706",
  pending: "#6b7280",
  cancelled: "#9ca3af",
};

type View = "overview" | "as-is" | "to-be" | "compare" | "workflow" | "phase" | "kanban" | "list";
type Mode = "orient" | "decide" | "execute" | "verify";
type DrillLevel = "L0" | "L1" | "L2" | "L3";
type Density = "executive" | "detailed";

function modeForView(view: View): Mode {
  if (view === "kanban") return "execute";
  if (view === "compare") return "verify";
  if (view === "overview") return "orient";
  return "orient";
}

function defaultViewForMode(mode: Mode, hasViews: boolean, hasAsIs: boolean, hasToBe: boolean, hasTasks: boolean): View {
  if (mode === "execute" && hasTasks) return "kanban";
  if (mode === "verify" && hasViews) return "compare";
  if (mode === "decide" && hasViews) return "compare";
  if (mode === "orient") {
    if (hasAsIs) return "as-is";
    if (hasToBe) return "to-be";
  }
  return "overview";
}

function allowedViewsForMode(mode: Mode, hasViews: boolean, hasAsIs: boolean, hasToBe: boolean, hasTasks: boolean): View[] {
  if (mode === "orient") {
    return [
      "overview",
      ...(hasAsIs ? ["as-is" as View] : []),
      ...(hasToBe ? ["to-be" as View] : []),
      ...(hasViews ? ["compare" as View] : []),
    ];
  }
  if (mode === "decide") {
    return ["overview", ...(hasViews ? ["compare" as View] : [])];
  }
  if (mode === "execute") {
    return [
      ...(hasTasks ? ["kanban" as View] : []),
      ...(hasToBe ? ["to-be" as View] : []),
      "overview",
    ];
  }
  return [...(hasViews ? ["compare" as View] : []), "overview"];
}

interface Phase {
  index: number;
  title: string;
  /** Numeric token if any (e.g. "1" for "Phase 1"). */
  token: string | null;
}

interface UiplanCanvasProps {
  bundle: ProjectNode;
  selectedNodeId: string | null;
  onSelectNode: (id: string) => void;
}

export default function UiplanCanvas({ bundle, selectedNodeId, onSelectNode }: UiplanCanvasProps) {
  const initialView: View = (bundle.children?.nodes ?? []).some((node) => node.kind === "uiplan_doc" || node.kind === "uiplan_tasks")
    ? "overview"
    : (bundle.children?.nodes ?? []).some((node) => node.kind === "uiplan_view_to_be")
    ? "to-be"
    : "as-is";
  const [view, setView] = useState<View>(initialView);
  const [mode, setMode] = useState<Mode>(modeForView(initialView));
  const [selectedPhaseIdx, setSelectedPhaseIdx] = useState<number | null>(null);
  const [density, setDensity] = useState<Density>("executive");
  const [selectedActor, setSelectedActor] = useState<string | null>(null);
  const [selectedBucketType, setSelectedBucketType] = useState<string | null>(null);
  const [selectedToBePlayer, setSelectedToBePlayer] = useState<string | null>(null);
  const [showRawMetadata, setShowRawMetadata] = useState(false);

  const tasks = useMemo(() => collectTasks(bundle), [bundle]);
  const phases = useMemo(() => extractPhases(bundle), [bundle]);
  const docs = useMemo(() => collectBundleDocs(bundle), [bundle]);

  // Extract AS-IS and TO-BE views from bundle children
  const asIsView = useMemo((): AsIsView | null => {
    const viewNode = bundle.children?.nodes?.find((n: any) => n.kind === "uiplan_view_as_is");
    return viewNode?.meta?.view || null;
  }, [bundle]);

  const toBeView = useMemo((): ToBeView | null => {
    const viewNode = bundle.children?.nodes?.find((n: any) => n.kind === "uiplan_view_to_be");
    return viewNode?.meta?.view || null;
  }, [bundle]);

  const hasViews = asIsView || toBeView;
  const actorOptions = asIsView?.swimlanes ?? [];
  const bucketOptions = (toBeView?.buckets ?? []).map((b) => b.bucket_type);
  const toBePlayerOptions = useMemo(() => {
    const source = toBeView?.workflows ?? [];
    const allPlayers = source.map((workflow) => inferWorkflowPlayer(workflow));
    return Array.from(new Set(allPlayers));
  }, [toBeView]);
  const profile = useMemo(
    () => buildPlanProfile(bundle, docs, tasks, phases, asIsView, toBeView),
    [bundle, docs, tasks, phases, asIsView, toBeView],
  );
  const traceParts = [
    mode.toUpperCase(),
    view === "overview" ? "PROJECT PLAN TEMPLATE" : view.toUpperCase(),
    selectedActor ? `ACTOR:${selectedActor}` : null,
    selectedBucketType ? `BUCKET:${selectedBucketType}` : null,
    selectedPhaseIdx !== null ? `PHASE:${selectedPhaseIdx + 1}` : null,
    density.toUpperCase(),
  ].filter(Boolean);

  const resetCleanView = () => {
    setView(initialView);
    setMode(modeForView(initialView));
    setDensity("executive");
    setSelectedPhaseIdx(null);
    setSelectedActor(null);
    setSelectedBucketType(null);
    setSelectedToBePlayer(null);
    setShowRawMetadata(false);
    onSelectNode(bundle.id);
  };

  useEffect(() => {
    const allowed = allowedViewsForMode(mode, hasViews, !!asIsView, !!toBeView, tasks.length > 0);
    if (!allowed.includes(view)) {
      setView(defaultViewForMode(mode, hasViews, !!asIsView, !!toBeView, tasks.length > 0));
    }
  }, [mode, view, hasViews, asIsView, toBeView, tasks.length]);

  const blockers = Math.max(profile.taskSummary.pending, profile.decisions.length);
  const nextTask = tasks.find((task) => taskStatus(task) === "pending" || taskStatus(task) === "in_progress");
  const nextAction = nextTask?.label ?? "Review compare delta and confirm readiness gates";
  const approvalState = blockers > 0 ? "IN REVIEW" : "READY";
  const currentPhase = mode[0].toUpperCase() + mode.slice(1);
  const modeViews = allowedViewsForMode(mode, hasViews, !!asIsView, !!toBeView, tasks.length > 0);
  const openView = (nextView: View) => {
    setView(nextView);
    setMode(modeForView(nextView));
    setShowRawMetadata(false);
  };

  const drill = useMemo(() => {
    return buildDrillState({
      view,
      selectedNodeId,
      selectedActor,
      selectedBucketType,
      selectedToBePlayer,
      showRawMetadata,
      asIsView,
      toBeView,
    });
  }, [view, selectedNodeId, selectedActor, selectedBucketType, selectedToBePlayer, showRawMetadata, asIsView, toBeView]);

  const stepBackDrill = () => {
    if (drill.level === "L3") {
      setShowRawMetadata(false);
      return;
    }
    if (drill.level === "L2") {
      onSelectNode(bundle.id);
      return;
    }
    if (drill.level === "L1") {
      if (view === "as-is") setSelectedActor(null);
      if (view === "to-be") {
        setSelectedBucketType(null);
        setSelectedToBePlayer(null);
      }
    }
  };

  return (
    <div style={{
      position: "absolute", inset: 0,
      display: "flex", flexDirection: "column",
      background: PALETTE.bg, overflow: "hidden",
    }}>
      <div style={{
        minHeight: 52, flexShrink: 0,
        borderBottom: `1px solid ${PALETTE.rule}`,
        background: PALETTE.panel,
        display: "flex", alignItems: "center", padding: "7px 16px", gap: 14,
      }}>
        <div style={{ minWidth: 260 }}>
          <div style={{
            fontSize: 12, letterSpacing: "0.16em", fontWeight: 800,
            color: PALETTE.textDim, fontFamily: "'JetBrains Mono', monospace",
          }}>
            UIPLAN WORKFLOW BUILDER
          </div>
          <div style={{
            marginTop: 2,
            fontSize: 15,
            fontWeight: 700,
            color: PALETTE.text,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}>
            {profile.title}
          </div>
        </div>
        <div style={{ flex: 1 }} />
        <div style={{ position: "relative", zIndex: 50, display: "flex", gap: 8, alignItems: "center" }}>
          <Segmented
            value={mode}
            ariaLabel="UiPlan lifecycle mode"
            onChange={(nextMode) => {
              setMode(nextMode as Mode);
              setShowRawMetadata(false);
            }}
            options={[
              { value: "orient" as Mode, label: "ORIENT", Icon: BookOpen },
              { value: "decide" as Mode, label: "DECIDE", Icon: Target },
              { value: "execute" as Mode, label: "EXECUTE", Icon: ListChecks },
              { value: "verify" as Mode, label: "VERIFY", Icon: CheckSquare },
            ]}
          />
          <button
            onClick={resetCleanView}
            aria-label="Reset clean view"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              border: `1px solid ${PALETTE.rule}`,
              background: PALETTE.bg,
              color: PALETTE.textDim,
              borderRadius: 8,
              padding: "8px 12px",
              cursor: "pointer",
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 12,
              letterSpacing: "0.08em",
              fontWeight: 700,
            }}
          >
            <RotateCcw size={11} />
            RESET CLEAN VIEW
          </button>
        </div>
      </div>
      <div style={{
        minHeight: 40,
        borderBottom: `1px solid ${PALETTE.rule}`,
        background: PALETTE.panel,
        display: "grid",
        gridTemplateColumns: "repeat(4, minmax(120px, 1fr))",
        gap: 8,
        padding: "6px 14px",
      }}>
        {[
          { k: "CURRENT PHASE", v: currentPhase, active: true },
          { k: "BLOCKER COUNT", v: String(blockers), active: blockers > 0 },
          { k: "NEXT ACTION", v: nextAction, active: true },
          { k: "APPROVAL STATE", v: approvalState, active: approvalState !== "READY" },
        ].map((metric) => (
          <div key={metric.k} title={metric.v} style={{ minWidth: 0 }}>
            <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, letterSpacing: "0.1em", color: PALETTE.textMute }}>
              {metric.k}
            </div>
            <div style={{
              marginTop: 2,
              fontSize: 12,
              fontWeight: metric.active ? 700 : 600,
              color: metric.active ? PALETTE.text : PALETTE.textDim,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}>
              {metric.v}
            </div>
          </div>
        ))}
      </div>
      <div
        style={{
          minHeight: 44,
          borderBottom: `1px solid ${PALETTE.rule}`,
          background: PALETTE.bg,
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "6px 14px",
          overflowX: "auto",
        }}
      >
        <div style={{ display: "flex", gap: 6, alignItems: "center", minWidth: 0, overflowX: "auto" }}>
          {modeViews.map((surface) => (
            <Chip
              key={surface}
              active={view === surface}
              onClick={() => openView(surface)}
              label={surface.replace("-", " ").toUpperCase()}
            />
          ))}
        </div>
        {view !== "overview" && (
          <>
            <Chip
              active={density === "executive"}
              onClick={() => setDensity("executive")}
              label="EXEC"
            />
            <Chip
              active={density === "detailed"}
              onClick={() => setDensity("detailed")}
              label="DETAIL"
            />
          </>
        )}
        {view === "overview" && (
          <>
            <Chip
              active
              onClick={() => undefined}
              label={`${profile.docs.length} plan files`}
            />
            <Chip
              active={profile.taskSummary.pending > 0}
              onClick={() => openView("kanban")}
              label={`${profile.taskSummary.pending} open tasks`}
            />
            <Chip
              active={!!asIsView}
              onClick={() => {
                if (asIsView) {
                  openView("as-is");
                }
              }}
              label="actual state"
            />
            <Chip
              active={!!toBeView}
              onClick={() => {
                if (toBeView) {
                  openView("to-be");
                }
              }}
              label="target state"
            />
          </>
        )}
        {view === "as-is" && actorOptions.map((actor) => (
          <Chip
            key={actor}
            active={selectedActor === actor}
            onClick={() => setSelectedActor((prev) => (prev === actor ? null : actor))}
            label={actor}
          />
        ))}
        {view === "to-be" && bucketOptions.map((bucket) => (
          <Chip
            key={bucket}
            active={selectedBucketType === bucket}
            onClick={() => setSelectedBucketType((prev) => (prev === bucket ? null : bucket))}
            label={bucket}
          />
        ))}
        {view === "to-be" && toBePlayerOptions.map((player) => (
          <Chip
            key={player}
            active={selectedToBePlayer === player}
            onClick={() => setSelectedToBePlayer((prev) => (prev === player ? null : player))}
            label={player}
          />
        ))}
        <div style={{ marginLeft: "auto", whiteSpace: "nowrap", fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: PALETTE.textDim }}>
          VIEW: {traceParts.join(" / ")}
        </div>
      </div>
      {view === "as-is" && (
        <div style={{
          minHeight: 38,
          borderBottom: `1px solid ${PALETTE.rule}`,
          background: PALETTE.panel,
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "6px 14px",
        }}>
          <button
            onClick={stepBackDrill}
            disabled={drill.level === "L0"}
            style={{
              border: `1px solid ${PALETTE.rule}`,
              background: drill.level === "L0" ? PALETTE.bg : "#ccfbf1",
              color: drill.level === "L0" ? PALETTE.textMute : "#0f766e",
              borderRadius: 6,
              padding: "6px 10px",
              cursor: drill.level === "L0" ? "not-allowed" : "pointer",
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 12,
              letterSpacing: "0.08em",
              fontWeight: 700,
            }}
          >
            DRILL BACK
          </button>
          <div style={{ display: "flex", gap: 6, alignItems: "center", minWidth: 0, overflowX: "auto" }}>
            {drill.breadcrumbs.map((crumb, idx) => (
              <button
                key={`${crumb}-${idx}`}
                onClick={() => {
                  if (idx === 0) {
                    setSelectedActor(null);
                    setSelectedBucketType(null);
                    onSelectNode(bundle.id);
                    setShowRawMetadata(false);
                  } else if (idx === 1) {
                    onSelectNode(bundle.id);
                    setShowRawMetadata(false);
                  } else if (idx === 2) {
                    setShowRawMetadata(false);
                  }
                }}
                style={{
                  border: `1px solid ${idx === drill.breadcrumbs.length - 1 ? "#0f766e55" : PALETTE.rule}`,
                  background: idx === drill.breadcrumbs.length - 1 ? "#ccfbf1" : PALETTE.bg,
                  color: idx === drill.breadcrumbs.length - 1 ? "#0f766e" : PALETTE.textDim,
                  borderRadius: 999,
                  padding: "4px 10px",
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 12,
                  letterSpacing: "0.08em",
                  whiteSpace: "nowrap",
                  cursor: "pointer",
                }}
              >
                {crumb}
              </button>
            ))}
          </div>
          <div style={{ marginLeft: "auto", fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: PALETTE.textDim }}>
            DRILL LEVEL: {drill.level}
          </div>
        </div>
      )}

      <div style={{ flex: 1, overflow: "auto", position: "relative", minHeight: 0 }}>
        {view === "overview" && (
          <PlanOverview
            profile={profile}
            onOpenView={openView}
            onSelectNode={onSelectNode}
          />
        )}
        {view === "as-is" && asIsView && (
          <AsIsCanvas
            asIsView={asIsView}
            onSelectHandoff={onSelectNode}
            selectedHandoffId={selectedNodeId}
            density={density}
            selectedActor={selectedActor}
            selectedPhase={selectedPhaseIdx}
            onSelectActor={setSelectedActor}
          />
        )}
        {view === "to-be" && toBeView && (
          <ToBeCanvas
            toBeView={toBeView}
            onSelectNode={onSelectNode}
            selectedNodeId={selectedNodeId}
            density={density}
            selectedBucketType={selectedBucketType}
            selectedPlayer={selectedToBePlayer}
          />
        )}
        {view === "compare" && asIsView && toBeView && (
          <AsIsToBeComparePanel
            asIsView={asIsView}
            toBeView={toBeView}
            selectedActor={selectedActor}
            selectedBucketType={selectedBucketType}
            onSelectActor={setSelectedActor}
            onSelectBucket={setSelectedBucketType}
          />
        )}
        {view === "kanban" && (
          <TasksView
            tasks={tasks}
            compactMode={density === "executive"}
            selectedNodeId={selectedNodeId}
            onSelectNode={onSelectNode}
            docs={docs}
            toBeView={toBeView}
            mode={mode}
          />
        )}
      </div>
      {view === "as-is" && drill.focus && (
        <div style={{
          borderTop: `1px solid ${PALETTE.rule}`,
          background: PALETTE.panel,
          padding: "10px 14px",
          display: "flex",
          gap: 10,
          alignItems: "flex-start",
        }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, letterSpacing: "0.12em", color: PALETTE.textDim }}>
              {view === "to-be" ? "BUILD CONTRACT" : "WHY THIS MATTERS"}
            </div>
            <div style={{ marginTop: 4, color: PALETTE.text, fontSize: 13 }}>
              {drill.focus.why}
            </div>
            <div style={{ marginTop: 8, fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: PALETTE.textDim }}>
              {view === "to-be" ? "READINESS" : "WHAT IS BLOCKED"}: {drill.focus.blocker}
            </div>
            <div style={{ marginTop: 4, fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: PALETTE.textDim }}>
              NEXT ACTION: {drill.focus.next}
            </div>
          </div>
          <button
            onClick={() => setShowRawMetadata((v) => !v)}
            style={{
              border: `1px solid ${showRawMetadata ? "#0f766e55" : PALETTE.rule}`,
              borderRadius: 6,
              background: showRawMetadata ? "#ccfbf1" : PALETTE.bg,
              color: showRawMetadata ? "#0f766e" : PALETTE.textDim,
              padding: "8px 10px",
              cursor: "pointer",
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 12,
              letterSpacing: "0.08em",
              fontWeight: 700,
            }}
          >
            RAW METADATA
          </button>
          {showRawMetadata && (
            <div style={{
              minWidth: 320,
              maxWidth: 460,
              border: `1px solid ${PALETTE.rule}`,
              borderRadius: 8,
              background: PALETTE.bg,
              padding: 10,
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 12,
              color: PALETTE.textDim,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}>
              {drill.focus.raw}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function AsIsToBeComparePanel({
  asIsView,
  toBeView,
  selectedActor,
  selectedBucketType,
  onSelectActor,
  onSelectBucket,
}: {
  asIsView: AsIsView;
  toBeView: ToBeView;
  selectedActor: string | null;
  selectedBucketType: string | null;
  onSelectActor: (value: string | null) => void;
  onSelectBucket: (value: string | null) => void;
}) {
  const actorCounts = new Map<string, number>();
  for (const handoff of asIsView.handoffs) {
    actorCounts.set(handoff.from_actor, (actorCounts.get(handoff.from_actor) ?? 0) + 1);
  }
  const bucketCounts = new Map<string, number>();
  for (const bucket of toBeView.buckets) {
    bucketCounts.set(bucket.bucket_type, bucket.node_ids.length);
  }

  return (
    <div style={{ padding: 24, height: "100%", overflowY: "auto" }}>
      <NarrativeDeltaStrip
        asIsCount={asIsView.handoffs.length}
        toBeCount={toBeView.workflows.length + toBeView.integrations.length + toBeView.orchestrator.length + toBeView.hitl.length}
      />
      <div style={{
        marginBottom: 16,
        border: `1px solid ${PALETTE.rule}`,
        borderRadius: 10,
        background: "#f0f9ff",
        padding: 16,
        color: "#1e40af",
        fontSize: 14,
        fontWeight: 500,
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center"
      }}>
        <div>
          <strong style={{ display: "block", marginBottom: 4, color: "#1e3a8a", fontSize: 16 }}>Transformation Summary</strong>
          Converting {asIsView.handoffs.length} manual handoffs into {toBeView.workflows.length + toBeView.integrations.length + toBeView.orchestrator.length + toBeView.hitl.length} automated assets.
        </div>
        <div style={{ display: "flex", gap: 16, textAlign: "center" }}>
          <div>
            <div style={{ fontSize: 24, fontWeight: 800, color: "#1d4ed8" }}>{asIsView.handoffs.length}</div>
            <div style={{ fontSize: 12, fontWeight: 600, color: "#3b82f6", textTransform: "uppercase" }}>Manual Steps</div>
          </div>
          <div style={{ fontSize: 24, fontWeight: 300, color: "#93c5fd" }}>→</div>
          <div>
            <div style={{ fontSize: 24, fontWeight: 800, color: "#059669" }}>{toBeView.workflows.length}</div>
            <div style={{ fontSize: 12, fontWeight: 600, color: "#10b981", textTransform: "uppercase" }}>Workflows</div>
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 40px 1fr", gap: 16, alignItems: "start" }}>
        {/* CURRENT STATE (LEFT) */}
        <section style={{ border: `1px solid ${PALETTE.rule}`, borderRadius: 10, background: PALETTE.panel, overflow: "hidden" }}>
          <div style={{ background: "#f8fafc", padding: "12px 16px", borderBottom: `1px solid ${PALETTE.rule}` }}>
            <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, letterSpacing: "0.14em", color: "#475569", fontWeight: 700 }}>
              CURRENT STATE (AS-IS)
            </div>
            <div style={{ fontSize: 13, color: PALETTE.textDim, marginTop: 4 }}>
              Human actors and manual handoffs
            </div>
          </div>
          
          <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
            {asIsView.swimlanes.map((actor) => (
              <div key={actor} style={{ border: `1px solid ${PALETTE.ruleSoft}`, borderRadius: 8, overflow: "hidden" }}>
                <button
                  onClick={() => onSelectActor(selectedActor === actor ? null : actor)}
                  style={{
                    width: "100%",
                    border: "none",
                    borderLeft: `4px solid ${selectedActor === actor ? "#8b5cf6" : "#cbd5e1"}`,
                    background: selectedActor === actor ? "#ede9fe" : "#f1f5f9",
                    padding: "10px 14px",
                    cursor: "pointer",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span style={{ fontSize: 14, fontWeight: 600, color: PALETTE.text }}>{actor}</span>
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", color: PALETTE.textDim, fontSize: 12, background: "#e2e8f0", padding: "2px 8px", borderRadius: 12 }}>
                    {actorCounts.get(actor) ?? 0} steps
                  </span>
                </button>
                
                {(selectedActor === actor || !selectedActor) && (
                  <div style={{ padding: "8px 14px", display: "flex", flexDirection: "column", gap: 6, background: PALETTE.panel }}>
                    {asIsView.handoffs.filter(h => h.from_actor === actor || h.to_actor === actor).length > 0 ? (
                      asIsView.handoffs.filter(h => h.from_actor === actor || h.to_actor === actor).map(handoff => (
                        <div key={handoff.id} style={{ fontSize: 13, color: PALETTE.text, padding: "6px", background: "#f8fafc", borderRadius: 4, display: "flex", gap: 8 }}>
                          <span style={{ color: "#8b5cf6" }}>•</span>
                          <div>
                            <div style={{ fontWeight: 500 }}>{handoff.artifact}</div>
                            {handoff.pain && <div style={{ fontSize: 12, color: "#ef4444", marginTop: 2 }}>Pain: {handoff.pain}</div>}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div style={{ fontSize: 12, color: PALETTE.textMute, fontStyle: "italic" }}>No specific handoffs</div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* MAPPING ARROWS (CENTER) */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", color: "#cbd5e1", paddingTop: 80 }}>
          <svg width="40" height="100" viewBox="0 0 40 100">
            <path d="M 5 50 L 35 50" stroke="#cbd5e1" strokeWidth="3" strokeDasharray="6 4" fill="none" />
            <path d="M 25 40 L 35 50 L 25 60" stroke="#cbd5e1" strokeWidth="3" fill="none" />
          </svg>
        </div>

        {/* TARGET STATE (RIGHT) */}
        <section style={{ border: `1px solid ${PALETTE.rule}`, borderRadius: 10, background: PALETTE.panel, overflow: "hidden" }}>
          <div style={{ background: "#f0fdf4", padding: "12px 16px", borderBottom: `1px solid #d1fae5` }}>
            <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, letterSpacing: "0.14em", color: "#047857", fontWeight: 700 }}>
              TARGET STATE (TO-BE)
            </div>
            <div style={{ fontSize: 13, color: "#059669", marginTop: 4 }}>
              Automated workflows and components
            </div>
          </div>
          
          <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
            {toBeView.buckets.map((bucket) => (
              <div key={bucket.id} style={{ border: `1px solid ${PALETTE.ruleSoft}`, borderRadius: 8, overflow: "hidden" }}>
                <button
                  onClick={() => onSelectBucket(selectedBucketType === bucket.bucket_type ? null : bucket.bucket_type)}
                  style={{
                    width: "100%",
                    border: "none",
                    borderLeft: `4px solid ${selectedBucketType === bucket.bucket_type ? "#059669" : "#6ee7b7"}`,
                    background: selectedBucketType === bucket.bucket_type ? "#d1fae5" : "#ecfdf5",
                    padding: "10px 14px",
                    cursor: "pointer",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span style={{ fontSize: 14, fontWeight: 600, color: "#064e3b" }}>{bucket.bucket_type}</span>
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", color: "#059669", fontSize: 12, background: "#a7f3d0", padding: "2px 8px", borderRadius: 12 }}>
                    {bucket.node_ids.length} nodes
                  </span>
                </button>
                
                {(selectedBucketType === bucket.bucket_type || !selectedBucketType) && (
                  <div style={{ padding: "8px 14px", display: "flex", flexDirection: "column", gap: 6, background: PALETTE.panel }}>
                    {bucket.node_ids.map(nodeId => {
                      const w = toBeView.workflows.find(w => w.id === nodeId.replace("subflow-", ""));
                      const i = toBeView.integrations.find(i => i.id === nodeId);
                      const o = toBeView.orchestrator.find(o => o.id === nodeId);
                      const h = toBeView.hitl.find(h => h.id === nodeId);
                      
                      const label = w?.label || i?.label || o?.label || h?.label || nodeId;
                      const type = w ? "Workflow" : i ? "Integration" : o ? "Data/Queue" : h ? "Human-in-loop" : "Node";
                      const color = w ? "#059669" : i ? "#2563eb" : o ? "#475569" : h ? "#dc2626" : "#64748b";
                      
                      return (
                        <div key={nodeId} style={{ fontSize: 13, color: PALETTE.text, padding: "6px", background: "#f8fafc", borderRadius: 4, display: "flex", gap: 8 }}>
                          <span style={{ color }}>•</span>
                          <div>
                            <div style={{ fontWeight: 500 }}>{label}</div>
                            <div style={{ fontSize: 12, color: PALETTE.textDim, marginTop: 2, fontFamily: "'JetBrains Mono', monospace" }}>{type}</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function NarrativeDeltaStrip({ asIsCount, toBeCount }: { asIsCount: number; toBeCount: number }) {
  return (
    <div style={{
      marginBottom: 12,
      border: "1px solid #bfdbfe",
      borderRadius: 8,
      background: "linear-gradient(90deg, #eff6ff 0%, #ecfeff 100%)",
      padding: "8px 12px",
      display: "flex",
      gap: 10,
      alignItems: "center",
      flexWrap: "wrap",
    }}>
      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#1e3a8a", letterSpacing: "0.1em", fontWeight: 800 }}>
          AS-IS -&gt; TO-BE NARRATIVE
      </span>
      <span style={{ fontSize: 12, color: "#1e40af" }}>
        {asIsCount} manual handoffs become {toBeCount} orchestrated building blocks with explicit ownership and evidence.
      </span>
    </div>
  );
}

function buildDrillState({
  view,
  selectedNodeId,
  selectedActor,
  selectedBucketType,
  selectedToBePlayer,
  showRawMetadata,
  asIsView,
  toBeView,
}: {
  view: View;
  selectedNodeId: string | null;
  selectedActor: string | null;
  selectedBucketType: string | null;
  selectedToBePlayer: string | null;
  showRawMetadata: boolean;
  asIsView: AsIsView | null;
  toBeView: ToBeView | null;
}): {
  level: DrillLevel;
  breadcrumbs: string[];
  focus: null | { why: string; blocker: string; next: string; raw: string };
} {
  if (view === "as-is" && asIsView) {
    const handoff = asIsView.handoffs.find((item) => item.id === selectedNodeId) ?? null;
    const base: string[] = ["L0 System AS-IS"];
    let level: DrillLevel = "L0";
    if (selectedActor) {
      base.push(`L1 ${selectedActor}`);
      level = "L1";
    }
    if (handoff) {
      base.push(`L2 ${handoff.from_actor} -> ${handoff.to_actor}`);
      level = "L2";
    }
    if (showRawMetadata && handoff) {
      base.push("L3 Raw metadata");
      level = "L3";
    }
    return {
      level,
      breadcrumbs: base,
      focus: handoff ? {
        why: handoff.artifact,
        blocker: handoff.pain || "No blocker marked",
        next: `Reduce latency from ${handoff.channel} handoff.`,
        raw: JSON.stringify(handoff, null, 2),
      } : null,
    };
  }
  if (view === "to-be" && toBeView) {
    const conceptualSelection = selectedNodeId?.startsWith("plan:")
      ? toBeConceptualSelection(selectedNodeId.slice("plan:".length), toBeView)
      : null;
    const allNodes = [
      ...toBeView.workflows.map((item) => ({ kind: "workflow", item })),
      ...toBeView.integrations.map((item) => ({ kind: "integration", item })),
      ...toBeView.orchestrator.map((item) => ({ kind: "orchestrator", item })),
      ...toBeView.hitl.map((item) => ({ kind: "hitl", item })),
    ];
    const selected = allNodes.find((entry) => entry.item.id === selectedNodeId) ?? null;
    const base: string[] = ["L0 System TO-BE"];
    let level: DrillLevel = "L0";
    if (selectedToBePlayer) {
      base.push(`L1 ${selectedToBePlayer}`);
      level = "L1";
    }
    if (selectedBucketType) {
      base.push(`${selectedToBePlayer ? "L2" : "L1"} ${selectedBucketType}`);
      if (!selectedToBePlayer) {
        level = "L1";
      }
    }
    if (selectedToBePlayer && selectedBucketType) {
      level = "L2";
    }
    if (conceptualSelection) {
      base.push(`L2 ${conceptualSelection.label}`);
      level = "L2";
    }
    if (selected) {
      base.push(`L2 ${selected.item.label}`);
      level = "L2";
    }
    if (showRawMetadata && selected) {
      base.push("L3 Raw metadata");
      level = "L3";
    }
    return {
      level,
      breadcrumbs: base,
      focus: conceptualSelection ? {
        why: conceptualSelection.contract,
        blocker: "Planning only - not connected to generated code",
        next: "Confirm the workflow contract, then generate UiPath implementation.",
        raw: JSON.stringify(conceptualSelection, null, 2),
      } : selected ? {
        why: selected.kind === "workflow"
          ? `Planned workflow: ${selected.item.label}`
          : selected.item.label,
        blocker: selected.kind === "hitl" ? "Needs callback contract validation" : "Designed - ready for generation review",
        next: selected.kind === "workflow" ? "Validate workflow inputs, outputs, credentials, and coverage." : "Validate integration contracts.",
        raw: JSON.stringify(selected.item, null, 2),
      } : null,
    };
  }
  return { level: "L0", breadcrumbs: ["L0"], focus: null };
}

function toBeConceptualSelection(id: string, toBeView: ToBeView): null | {
  id: string;
  label: string;
  contract: string;
  level: "stage" | "subflow";
} {
  const stageLabels: Record<string, string> = {
    "solution-trigger": "Slack request received",
    "solution-intake": "Normalize renewal request",
    "solution-policy": "Route approval policy",
    "solution-human-decision": "Create approval task",
    "solution-system-update": "Update Salesforce quote",
    "solution-evidence": "Write audit evidence",
    "solution-outcome": "Reply in Slack",
  };
  if (id in stageLabels) {
    return {
      id,
      label: stageLabels[id],
      contract: `Pre-build UiPath contract for ${stageLabels[id]}: purpose, input, output, owner, validators, readiness, and blockers.`,
      level: "stage",
    };
  }
  if (id.startsWith("subflow-")) {
    const workflowId = id.slice("subflow-".length);
    const workflow = toBeView.workflows.find((item) => item.id === workflowId);
    if (!workflow) return null;
    const player = inferWorkflowPlayer(workflow);
    return {
      id,
      label: workflow.bucket === "intake" ? "Intake and routing workflow" : `${player} approval workflow`,
      contract: `${workflow.internal_steps.length} planned steps for ${player}; this is a pre-build contract, not an implementation file.`,
      level: "subflow",
    };
  }
  return null;
}

function inferWorkflowPlayer(workflow: ToBeView["workflows"][number]): string {
  const label = workflow.label.toLowerCase();
  if (label.includes("salesrep") || label.includes("sales rep")) return "Sales Rep";
  if (label.includes("manager")) return "Manager";
  if (label.includes("finance")) return "Finance";
  if (label.includes("revops") || label.includes("rev ops")) return "RevOps";
  if (workflow.bucket === "intake") return "Request Intake";
  return "Shared";
}

function Chip({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      style={{
        border: `1px solid ${active ? "#0f766e" : PALETTE.rule}`,
        background: active ? "#ccfbf1" : PALETTE.panel,
        color: active ? "#0f766e" : PALETTE.textDim,
        borderRadius: 999,
        padding: "6px 12px",
        cursor: "pointer",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 12,
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        fontWeight: 700,
      }}
    >
      {label}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Segmented control
// ---------------------------------------------------------------------------

interface SegOpt<V extends string> {
  value: V;
  label: string;
  Icon: React.ComponentType<{ size?: number; color?: string; strokeWidth?: number }>;
}

function Segmented<V extends string>({ value, onChange, options, ariaLabel }: {
  value: V; onChange: (v: V) => void; options: SegOpt<V>[]; ariaLabel?: string;
}) {
  return (
    <div style={{
      display: "flex",
      border: `1px solid ${PALETTE.rule}`,
      borderRadius: 8, overflow: "hidden",
      background: PALETTE.bg,
    }}
    aria-label={ariaLabel}
    >
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "8px 14px", border: "none",
              borderRight: `1px solid ${PALETTE.rule}`,
              background: active ? PALETTE.panel : "transparent",
              cursor: "pointer",
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 12, letterSpacing: "0.08em", fontWeight: 700,
              color: active ? PALETTE.text : PALETTE.textDim,
            }}
          >
            <opt.Icon size={12} />
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Plan overview
// ---------------------------------------------------------------------------

interface PlanProfile {
  title: string;
  summary: string;
  docs: BundleDoc[];
  phases: Phase[];
  taskSummary: TaskSummary;
  asIsCount: number;
  toBeCount: number;
  decisions: string[];
}

interface TaskSummary {
  total: number;
  done: number;
  pending: number;
  in_progress: number;
  cancelled: number;
}

type PlanningCardStatus = "ready" | "active" | "blocked" | "review";

interface ProjectPlanningCard {
  id: string;
  title: string;
  eyebrow: string;
  summary: string;
  meta: string[];
  status: PlanningCardStatus;
  doc?: BundleDoc;
  onClick: () => void;
}

interface ProjectPlanningColumn {
  title: string;
  subtitle: string;
  status: string;
  color: string;
  cards: ProjectPlanningCard[];
}

function PlanOverview({ profile, onOpenView, onSelectNode }: {
  profile: PlanProfile;
  onOpenView: (view: View) => void;
  onSelectNode: (id: string) => void;
}) {
  const donePct = profile.taskSummary.total === 0
    ? 0
    : Math.round((profile.taskSummary.done / profile.taskSummary.total) * 100);
  const docByName = new Map(profile.docs.map((doc) => [doc.label.toLowerCase(), doc]));
  const specDoc = docByName.get("spec.md") ?? profile.docs[0];
  const planDoc = docByName.get("plan.md") ?? profile.docs[1] ?? profile.docs[0];
  const tasksDoc = docByName.get("tasks.md") ?? profile.docs.find((doc) => doc.kind === "uiplan_tasks") ?? profile.docs[2] ?? profile.docs[0];
  const specDiagrams = extractMermaidBlocks(specDoc?.body ?? "").length;
  const planDiagrams = extractMermaidBlocks(planDoc?.body ?? "").length;
  const taskDiagrams = extractMermaidBlocks(tasksDoc?.body ?? "").length;
  const [selectedDocId, setSelectedDocId] = useState<string | null>(specDoc?.id ?? null);
  const selectedDoc = profile.docs.find((doc) => doc.id === selectedDocId) ?? specDoc ?? planDoc ?? tasksDoc;
  const selectedDocFlow = buildPlanningDocFlow(selectedDoc, profile);
  const docFlowWidth = Math.max(990, 46 + selectedDocFlow.length * 205);

  const selectPlanningDoc = (doc: BundleDoc | undefined) => {
    if (!doc) return;
    setSelectedDocId(doc.id);
    onSelectNode(doc.id);
  };

  const columns: ProjectPlanningColumn[] = [
    {
      title: "DEFINE",
      subtitle: "Problem, actors, current state",
      status: "READY",
      color: "#d97706",
      cards: [
        {
          id: "spec",
          title: "spec.md",
          eyebrow: "PROJECT BRIEF",
          summary: "Scope, acceptance, actors, AS-IS business process.",
          meta: [`${specDiagrams} diagrams`, "template input"],
          status: "ready",
          doc: specDoc,
          onClick: () => selectPlanningDoc(specDoc),
        },
        {
          id: "asis",
          title: "AS-IS diagram",
          eyebrow: "CURRENT STATE",
          summary: `${profile.asIsCount} manual handoffs and pain points to validate.`,
          meta: ["manual flow", "drill-down"],
          status: "ready",
          onClick: () => onOpenView("as-is"),
        },
      ],
    },
    {
      title: "DESIGN",
      subtitle: "Architecture and target workflow",
      status: "ACTIVE",
      color: "#2563eb",
      cards: [
        {
          id: "plan",
          title: "plan.md",
          eyebrow: "SOLUTION DESIGN",
          summary: `${profile.decisions.length || 0} decisions, runtime sequence, assets, and contracts.`,
          meta: [`${planDiagrams} diagrams`, `${profile.phases.length || 0} phases`],
          status: "active",
          doc: planDoc,
          onClick: () => selectPlanningDoc(planDoc),
        },
        {
          id: "tobe",
          title: "TO-BE diagram",
          eyebrow: "UIPATH TARGET",
          summary: `${profile.toBeCount} workflow and platform nodes to build.`,
          meta: ["subflows", "HITL + evidence"],
          status: "active",
          onClick: () => onOpenView("to-be"),
        },
      ],
    },
    {
      title: "BUILD",
      subtitle: "Backlog and execution plan",
      status: `${profile.taskSummary.pending} OPEN`,
      color: "#7c3aed",
      cards: [
        {
          id: "tasks",
          title: "tasks.md",
          eyebrow: "BUILD BACKLOG",
          summary: `${profile.taskSummary.done}/${profile.taskSummary.total} complete, ${profile.taskSummary.pending} still open.`,
          meta: [`${profile.taskSummary.in_progress} active`, `${taskDiagrams} diagrams`],
          status: profile.taskSummary.pending > 0 ? "blocked" : "ready",
          doc: tasksDoc,
          onClick: () => selectPlanningDoc(tasksDoc),
        },
        {
          id: "open-tasks",
          title: "Open planning work",
          eyebrow: "TASK BOARD",
          summary: "Grouped implementation phases from tasks.md.",
          meta: [`${profile.taskSummary.pending} pending`, `${profile.taskSummary.done} done`],
          status: "active",
          onClick: () => onOpenView("kanban"),
        },
      ],
    },
    {
      title: "VALIDATE",
      subtitle: "Evidence and review gates",
      status: "REVIEW",
      color: "#0f766e",
      cards: [
        {
          id: "evidence",
          title: "Evidence loop",
          eyebrow: "ACCEPTANCE",
          summary: "Every task needs test, screenshot, or reviewer evidence.",
          meta: ["coverage map", "review notes"],
          status: "review",
          onClick: () => selectPlanningDoc(tasksDoc),
        },
        {
          id: "compare",
          title: "AS-IS / TO-BE gap",
          eyebrow: "DELTA REVIEW",
          summary: "Confirm manual handoffs are covered by the target design.",
          meta: ["compare view", "sign-off"],
          status: "review",
          onClick: () => onOpenView("compare"),
        },
      ],
    },
    {
      title: "TEMPLATE",
      subtitle: "Reusable planning contract",
      status: "KEEP",
      color: "#475569",
      cards: [
        {
          id: "template",
          title: "Template contract",
          eyebrow: "REUSABLE UIPLAN",
          summary: "spec.md, plan.md, tasks.md, diagrams, and views stay linked.",
          meta: ["template", "next project"],
          status: "ready",
          onClick: () => onOpenView("compare"),
        },
      ],
    },
  ];

  return (
    <div style={projectPlanRootStyle}>
      <div style={{ maxWidth: 1220, margin: "0 auto 10px" }}>
        <NarrativeDeltaStrip asIsCount={profile.asIsCount} toBeCount={profile.toBeCount} />
      </div>
      <div style={projectPlanHeaderStyle}>
        <div>
          <div style={projectPlanEyebrowStyle}>PROJECT PLANNING KANBAN</div>
          <div style={projectPlanTitleStyle}>{profile.title}</div>
          <div style={projectPlanSubtitleStyle}>{profile.summary}</div>
        </div>
        <div style={projectPlanMetricsStyle}>
          <span>{profile.docs.length} plan files</span>
          <span>{specDiagrams + planDiagrams + taskDiagrams} embedded diagrams</span>
          <span>{donePct}% task progress</span>
        </div>
      </div>

      <div style={projectKanbanStyle}>
        {columns.map((column) => (
          <section key={column.title} style={{ ...projectKanbanColumnStyle, borderTopColor: column.color }}>
            <div style={projectKanbanColumnHeaderStyle}>
              <div>
                <div style={{ ...projectKanbanColumnTitleStyle, color: column.color }}>{column.title}</div>
                <div style={projectKanbanColumnSubtitleStyle}>{column.subtitle}</div>
              </div>
              <span style={{ ...projectKanbanStatusStyle, color: column.color, background: `${column.color}18` }}>{column.status}</span>
            </div>
            <div style={projectKanbanCardsStyle}>
              {column.cards.map((card) => (
                <button
                  key={card.id}
                  type="button"
                  onClick={card.onClick}
                  aria-label={`${card.title} ${card.eyebrow}`}
                  title={`${card.title}\n${card.summary}\n${card.meta.join("\n")}`}
                  style={{
                    ...projectKanbanCardStyle,
                    borderLeftColor: statusColorForPlanningCard(card.status),
                    outline: card.doc?.id === selectedDocId ? `2px solid ${column.color}` : "none",
                    outlineOffset: 2,
                  }}
                >
                  <span style={planningNodeEyebrowStyle}>{card.eyebrow}</span>
                  <span style={planningNodeTitleStyle}>{card.title}</span>
                  <span style={planningNodeSummaryStyle}>{card.summary}</span>
                  <span style={projectKanbanMetaStyle}>
                    {card.meta.map((item) => <span key={item}>{item}</span>)}
                  </span>
                </button>
              ))}
            </div>
          </section>
        ))}
      </div>

      <div style={templateStripStyle}>
        {["spec.md: project brief", "plan.md: solution design", "tasks.md: kanban backlog", "AS-IS/TO-BE: drill-down workflow views"].map((item) => (
          <span key={item}>{item}</span>
        ))}
      </div>

      {selectedDoc && (
        <div style={docDrilldownStyle}>
          <div style={docDrilldownHeaderStyle}>
            <div>
              <div style={projectPlanEyebrowStyle}>{selectedDoc.label.toUpperCase()} CARD DETAIL</div>
              <div style={docDrilldownTitleStyle}>Planning checklist</div>
            </div>
            <div style={docDrilldownMetaStyle}>
              <span>{selectedDocFlow.length} planning nodes</span>
              <span>{extractMermaidBlocks(selectedDoc.body).length} embedded diagrams</span>
            </div>
          </div>
          <div style={docFlowRailStyle}>
            <div style={{ position: "relative", width: docFlowWidth, minHeight: 124 }}>
            <svg width={docFlowWidth} height="124" viewBox={`0 0 ${docFlowWidth} 124`} preserveAspectRatio="xMinYMid meet" style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
              <defs>
                <marker id="doc-flow-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
                  <path d="M 0 0 L 8 4 L 0 8 z" fill="#64748b" />
                </marker>
              </defs>
              {selectedDocFlow.slice(0, -1).map((_, index) => (
                <path
                  key={index}
                  d={`M ${166 + index * 205} 62 L ${222 + index * 205} 62`}
                  fill="none"
                  stroke="#64748b"
                  strokeWidth={2}
                  strokeDasharray={index % 2 === 0 ? undefined : "4 4"}
                  markerEnd="url(#doc-flow-arrow)"
                />
              ))}
            </svg>
            {selectedDocFlow.map((step, index) => (
              <button
                key={`${selectedDoc.id}-${step.title}-${index}`}
                type="button"
                title={`${step.title}\n${step.summary}`}
                style={{ ...docFlowNodeStyle, left: 26 + index * 205, borderTopColor: step.color }}
              >
                <span style={planningNodeEyebrowStyle}>{step.eyebrow}</span>
                <span style={docFlowNodeTitleStyle}>{step.title}</span>
                <span style={docFlowNodeSummaryStyle}>{step.summary}</span>
              </button>
            ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const projectPlanRootStyle: React.CSSProperties = {
  minHeight: "100%",
  padding: "18px 24px 24px",
  background: "#f8fafc",
  overflow: "auto",
};

const projectPlanHeaderStyle: React.CSSProperties = {
  maxWidth: 1220,
  margin: "0 auto 12px",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-end",
  gap: 18,
  border: `1px solid ${PALETTE.rule}`,
  background: PALETTE.panel,
  padding: "12px 14px",
};

const projectPlanEyebrowStyle: React.CSSProperties = {
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 12,
  letterSpacing: "0.16em",
  fontWeight: 800,
  color: "#0f766e",
};

const projectPlanTitleStyle: React.CSSProperties = {
  marginTop: 4,
  fontSize: 18,
  fontWeight: 800,
  color: PALETTE.text,
};

const projectPlanSubtitleStyle: React.CSSProperties = {
  marginTop: 4,
  maxWidth: 680,
  fontSize: 12.5,
  lineHeight: 1.35,
  color: PALETTE.textDim,
};

const projectPlanMetricsStyle: React.CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  justifyContent: "flex-end",
  gap: 6,
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 12,
  color: PALETTE.textDim,
};

const projectKanbanStyle: React.CSSProperties = {
  maxWidth: 1220,
  margin: "0 auto",
  display: "grid",
  gridTemplateColumns: "repeat(5, minmax(190px, 1fr))",
  gap: 12,
  alignItems: "stretch",
};

const projectKanbanColumnStyle: React.CSSProperties = {
  minHeight: 356,
  display: "flex",
  flexDirection: "column",
  gap: 10,
  border: `1px solid ${PALETTE.rule}`,
  borderTop: "4px solid",
  background: "rgba(255,255,255,0.82)",
  padding: 10,
  boxSizing: "border-box",
};

const projectKanbanColumnHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  gap: 8,
  minHeight: 48,
};

const projectKanbanColumnTitleStyle: React.CSSProperties = {
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 12,
  letterSpacing: "0.16em",
  fontWeight: 900,
};

const projectKanbanColumnSubtitleStyle: React.CSSProperties = {
  marginTop: 4,
  fontSize: 12,
  lineHeight: 1.25,
  color: PALETTE.textDim,
};

const projectKanbanStatusStyle: React.CSSProperties = {
  flexShrink: 0,
  padding: "3px 6px",
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 12,
  letterSpacing: "0.08em",
  fontWeight: 800,
  whiteSpace: "nowrap",
};

const projectKanbanCardsStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 9,
};

const projectKanbanCardStyle: React.CSSProperties = {
  minHeight: 124,
  display: "flex",
  flexDirection: "column",
  gap: 6,
  border: `1px solid ${PALETTE.rule}`,
  borderLeft: "4px solid",
  borderRadius: 7,
  background: "#fffdfa",
  color: PALETTE.text,
  textAlign: "left",
  cursor: "pointer",
  padding: "10px",
  boxSizing: "border-box",
  overflow: "hidden",
  boxShadow: "0 4px 12px rgba(15, 23, 42, 0.06)",
};

const planningNodeEyebrowStyle: React.CSSProperties = {
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 12,
  letterSpacing: "0.1em",
  fontWeight: 800,
  color: PALETTE.textMute,
  textTransform: "uppercase",
};

const planningNodeTitleStyle: React.CSSProperties = {
  fontSize: 14,
  fontWeight: 800,
  color: PALETTE.text,
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
};

const planningNodeSummaryStyle: React.CSSProperties = {
  fontSize: 12,
  lineHeight: 1.28,
  color: PALETTE.textDim,
  display: "-webkit-box",
  WebkitLineClamp: 2,
  WebkitBoxOrient: "vertical",
  overflow: "hidden",
};

const projectKanbanMetaStyle: React.CSSProperties = {
  marginTop: "auto",
  display: "flex",
  flexWrap: "wrap",
  gap: 5,
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 12,
  letterSpacing: "0.05em",
  color: "#0f766e",
  fontWeight: 800,
  textTransform: "uppercase",
};

const templateStripStyle: React.CSSProperties = {
  maxWidth: 1220,
  margin: "12px auto 0",
  display: "flex",
  flexWrap: "wrap",
  gap: 8,
  border: `1px solid ${PALETTE.rule}`,
  background: PALETTE.panel,
  padding: 10,
  color: PALETTE.textDim,
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 12,
};

const docDrilldownStyle: React.CSSProperties = {
  maxWidth: 1220,
  margin: "14px auto 0",
  borderTop: `1px solid ${PALETTE.rule}`,
  paddingTop: 12,
};

const docDrilldownHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-end",
  gap: 14,
  marginBottom: 10,
};

const docDrilldownTitleStyle: React.CSSProperties = {
  marginTop: 2,
  fontSize: 14,
  fontWeight: 800,
  color: PALETTE.text,
};

const docDrilldownMetaStyle: React.CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  justifyContent: "flex-end",
  gap: 8,
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 12,
  color: PALETTE.textDim,
};

const docFlowRailStyle: React.CSSProperties = {
  position: "relative",
  height: 124,
  borderTop: `1px solid ${PALETTE.rule}`,
  borderBottom: `1px solid ${PALETTE.rule}`,
  background: "linear-gradient(180deg, rgba(255,255,255,0.72), rgba(248,250,252,0.88))",
  overflowX: "auto",
  overflowY: "hidden",
};

const docFlowNodeStyle: React.CSSProperties = {
  position: "absolute",
  top: 18,
  width: 160,
  height: 88,
  display: "flex",
  flexDirection: "column",
  gap: 4,
  border: `1px solid ${PALETTE.rule}`,
  borderTop: "3px solid",
  borderRadius: 7,
  background: "#ffffff",
  textAlign: "left",
  padding: "8px 9px",
  boxSizing: "border-box",
  overflow: "hidden",
  cursor: "help",
};

const docFlowNodeTitleStyle: React.CSSProperties = {
  fontSize: 12,
  lineHeight: 1.15,
  fontWeight: 800,
  color: PALETTE.text,
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
};

const docFlowNodeSummaryStyle: React.CSSProperties = {
  fontSize: 12,
  lineHeight: 1.25,
  color: PALETTE.textDim,
  display: "-webkit-box",
  WebkitLineClamp: 2,
  WebkitBoxOrient: "vertical",
  overflow: "hidden",
};

function statusColorForPlanningCard(status: PlanningCardStatus): string {
  if (status === "ready") return "#059669";
  if (status === "active") return "#2563eb";
  if (status === "blocked") return "#d97706";
  return "#0f766e";
}

interface PlanningDocFlowStep {
  eyebrow: string;
  title: string;
  summary: string;
  color: string;
}

function buildPlanningDocFlow(doc: BundleDoc | undefined, profile: PlanProfile): PlanningDocFlowStep[] {
  if (!doc) return [];
  const label = doc.label.toLowerCase();
  const diagrams = extractMermaidBlocks(doc.body);
  const diagramStep: PlanningDocFlowStep = {
    eyebrow: "DIAGRAMS",
    title: `${diagrams.length} embedded`,
    summary: diagrams.length === 0
      ? "Diagram slot reserved for this template."
      : diagrams.map(inferMermaidKind).slice(0, 2).join(" and "),
    color: "#0f766e",
  };

  if (label === "spec.md") {
    return [
      { eyebrow: "01 SCOPE", title: "Business need", summary: "Actors, request channel, goal, constraints, and acceptance.", color: "#d97706" },
      { eyebrow: "02 AS-IS", title: "Current process", summary: `${profile.asIsCount} manual handoff nodes feed the AS-IS diagram.`, color: "#78716c" },
      { eyebrow: "03 RULES", title: "Decision logic", summary: "Routing, thresholds, exceptions, and policy branches.", color: "#2563eb" },
      diagramStep,
      { eyebrow: "OUTPUT", title: "Plan input", summary: "Clear requirements move forward into solution design.", color: "#475569" },
    ];
  }

  if (label === "plan.md") {
    return [
      { eyebrow: "01 DECIDE", title: "Architecture", summary: `${profile.decisions.length || 0} design decisions anchor the target flow.`, color: "#2563eb" },
      { eyebrow: "02 MODEL", title: "Runtime flow", summary: `${profile.toBeCount} target-state workflow and platform nodes feed TO-BE.`, color: "#0f766e" },
      diagramStep,
      { eyebrow: "03 PHASE", title: "Build sequence", summary: `${profile.phases.length || 0} implementation phases define the order of work.`, color: "#7c3aed" },
      { eyebrow: "OUTPUT", title: "Task input", summary: "Solution decisions become executable project tasks.", color: "#475569" },
    ];
  }

  if (label === "tasks.md" || doc.kind === "uiplan_tasks") {
    return [
      { eyebrow: "01 BREAKDOWN", title: "Task map", summary: `${profile.taskSummary.total} total template tasks across build phases.`, color: "#7c3aed" },
      { eyebrow: "02 STATUS", title: "Progress", summary: `${profile.taskSummary.done} done, ${profile.taskSummary.pending} pending, ${profile.taskSummary.in_progress} active.`, color: "#d97706" },
      diagramStep,
      { eyebrow: "03 EVIDENCE", title: "Validation loop", summary: "Tests, screenshots, and review notes prove each workflow decision.", color: "#0f766e" },
      { eyebrow: "OUTPUT", title: "Build ready", summary: "The template remains reusable for the next UiPath project.", color: "#475569" },
    ];
  }

  return extractMarkdownHeadings(doc.body)
    .slice(0, 4)
    .map((title, index) => ({
      eyebrow: `SECTION ${index + 1}`,
      title,
      summary: "Planning content used by the reusable UiPlan template.",
      color: ["#d97706", "#2563eb", "#0f766e", "#7c3aed"][index] ?? "#475569",
    }))
    .concat(diagramStep)
    .slice(0, 5);
}

// ---------------------------------------------------------------------------
// Task collection / phase parsing
// ---------------------------------------------------------------------------

function collectTasks(bundle: ProjectNode): ProjectNode[] {
  const out: ProjectNode[] = [];
  for (const child of bundle.children?.nodes ?? []) {
    if (child.kind === "uiplan_tasks") {
      for (const t of child.children?.nodes ?? []) {
        if (t.kind === "uiplan_task") out.push(t);
      }
    } else if (child.kind === "uiplan_task") {
      out.push(child);
    }
  }
  return out;
}

function findPlanBody(bundle: ProjectNode): string {
  for (const child of bundle.children?.nodes ?? []) {
    if (child.kind === "uiplan_doc" && /plan\.md$/i.test(child.label)) {
      return String(child.meta?.body ?? "");
    }
  }
  // Fallback: any uiplan_doc body.
  for (const child of bundle.children?.nodes ?? []) {
    if (child.kind === "uiplan_doc") return String(child.meta?.body ?? "");
  }
  return "";
}

const PHASE_HEADING_RE = /^(?:phase|step|stage)\s+(\d+|[A-Z])\b/i;

function extractPhases(bundle: ProjectNode): Phase[] {
  const body = findPlanBody(bundle);
  if (!body) return [];
  const lines = body.split(/\r?\n/);
  const h2: { title: string; isPhase: boolean; token: string | null }[] = [];
  for (const raw of lines) {
    const m = /^##\s+(.+?)\s*$/.exec(raw);
    if (!m) continue;
    const title = m[1].trim();
    const ph = PHASE_HEADING_RE.exec(title);
    h2.push({ title, isPhase: !!ph, token: ph ? ph[1] : null });
  }
  const phaseHeadings = h2.filter((h) => h.isPhase);
  const headings = phaseHeadings.length > 0 ? phaseHeadings : h2;
  return headings.map((h, i) => ({ index: i, title: h.title, token: h.token }));
}

function taskMatchesPhase(task: ProjectNode, phase: Phase): boolean {
  const hay = (task.label + " " + (task.desc ?? "") + " " + String(task.meta?.task_section ?? "")).toLowerCase();
  if (phase.token && hay.includes(phase.token.toLowerCase())) return true;
  // Match the title's first significant word.
  const word = phase.title.replace(PHASE_HEADING_RE, "").trim().split(/\s+/)[0];
  if (word && word.length >= 4 && hay.includes(word.toLowerCase())) return true;
  // Check task_section equals or contains the phase title
  const section = String(task.meta?.task_section ?? "").toLowerCase();
  if (section && phase.title.toLowerCase().includes(section)) return true;
  return false;
}

function taskStatus(task: ProjectNode): string {
  return String(task.meta?.task_status ?? "pending");
}

function suggestSkillForTask(task: ProjectNode | undefined): string {
  if (!task) return "uipath-platform";
  const hay = `${task.label} ${task.desc ?? ""} ${String(task.meta?.task_section ?? "")}`.toLowerCase();
  if (/\bagent|langgraph|llm|prompt|ai\b/.test(hay)) return "uipath-agents";
  if (/\bflow|bpmn|maestro\b/.test(hay)) return "uipath-maestro-flow";
  if (/\bcase|caseplan\b/.test(hay)) return "uipath-maestro-case";
  if (/\basset|queue|orchestrator|workflow|xaml|robot\b/.test(hay)) return "uipath-rpa";
  if (/\bapp|action app|coded app\b/.test(hay)) return "uipath-coded-apps";
  if (/\bpolicy|governance|guardrail\b/.test(hay)) return "uipath-governance";
  if (/\bdeploy|publish|release|package\b/.test(hay)) return "uipath-deployment-readiness";
  return "uipath-platform";
}

// ---------------------------------------------------------------------------
// n8n-style workflow flow
// ---------------------------------------------------------------------------

interface BundleDoc {
  id: string;
  label: string;
  kind: string;
  body: string;
  path: string;
}

interface NodeProperty {
  displayName: string;
  name: string;
  value: string;
}

interface N8nNodeDescriptor {
  id: string;
  displayName: string;
  name: string;
  group: string[];
  description: string;
  defaults: { name: string; color: string };
  inputs: string[];
  outputs: string[];
  credentials: { name: string; required: boolean }[];
  properties: NodeProperty[];
  sourceNodeId?: string;
  taskIds?: string[];
  upstreamIds: string[];
  x: number;
  y: number;
}

function collectBundleDocs(bundle: ProjectNode): BundleDoc[] {
  return (bundle.children?.nodes ?? [])
    .filter((child) => child.kind === "uiplan_doc" || child.kind === "uiplan_tasks")
    .map((child) => ({
      id: child.id,
      label: child.label,
      kind: child.kind,
      body: String(child.meta?.body ?? ""),
      path: String(child.meta?.full_path ?? child.code?.path ?? child.label),
    }));
}

function buildPlanProfile(
  bundle: ProjectNode,
  docs: BundleDoc[],
  tasks: ProjectNode[],
  phases: Phase[],
  asIsView: AsIsView | null,
  toBeView: ToBeView | null,
): PlanProfile {
  const specDoc = docs.find((doc) => /^spec\.md$/i.test(doc.label));
  const planDoc = docs.find((doc) => /^plan\.md$/i.test(doc.label));
  const taskNode = docs.find((doc) => doc.kind === "uiplan_tasks");
  const taskSummary = summarizeTasks(bundle, taskNode, tasks);

  return {
    title: extractFrontMatterValue(specDoc?.body, "name")
      ?? extractFrontMatterValue(planDoc?.body, "name")
      ?? bundle.label,
    summary: extractFrontMatterValue(specDoc?.body, "overview")
      ?? extractFrontMatterValue(planDoc?.body, "overview")
      ?? firstUsefulParagraph(specDoc?.body)
      ?? bundle.desc
      ?? "UiPlan bundle overview.",
    docs,
    phases,
    taskSummary,
    asIsCount: asIsView?.handoffs.length ?? 0,
    toBeCount: (toBeView?.workflows.length ?? 0)
      + (toBeView?.integrations.length ?? 0)
      + (toBeView?.orchestrator.length ?? 0)
      + (toBeView?.hitl.length ?? 0),
    decisions: extractDecisionBullets(planDoc?.body),
  };
}

function summarizeTasks(bundle: ProjectNode, taskDoc: BundleDoc | undefined, tasks: ProjectNode[]): TaskSummary {
  const taskNode = (bundle.children?.nodes ?? []).find((child) => child.id === taskDoc?.id);
  const meta = taskNode?.meta ?? {};
  const explicitTotal = Number(meta.tasks_total ?? taskNode?.task_summary?.total ?? 0);
  if (explicitTotal > 0) {
    return {
      total: explicitTotal,
      done: Number(meta.tasks_done ?? taskNode?.task_summary?.done ?? 0),
      pending: Number(meta.tasks_pending ?? taskNode?.task_summary?.pending ?? 0),
      in_progress: Number(meta.tasks_in_progress ?? taskNode?.task_summary?.in_progress ?? 0),
      cancelled: Number(meta.tasks_cancelled ?? taskNode?.task_summary?.cancelled ?? 0),
    };
  }

  const summary: TaskSummary = { total: 0, done: 0, pending: 0, in_progress: 0, cancelled: 0 };
  for (const task of tasks) {
    const status = taskStatus(task) as keyof TaskSummary;
    summary.total += 1;
    if (status in summary && status !== "total") {
      summary[status] += 1;
    } else {
      summary.pending += 1;
    }
  }
  return summary;
}

function extractFrontMatterValue(body: string | undefined, key: string): string | null {
  if (!body) return null;
  const match = new RegExp(`^${key}:\\s*"?([^"\\n]+)"?\\s*$`, "im").exec(body);
  return match?.[1]?.trim() || null;
}

function firstUsefulParagraph(body: string | undefined): string | null {
  if (!body) return null;
  const paragraphs = body
    .replace(/^---[\s\S]*?---/, "")
    .split(/\n\s*\n/)
    .map((part) => part.trim())
    .filter((part) => part && !part.startsWith("#") && !part.startsWith("```"));
  return paragraphs[0]?.replace(/\s+/g, " ") ?? null;
}

// ---------------------------------------------------------------------------
// Template-aware markdown extraction helpers
// ---------------------------------------------------------------------------

interface MarkdownTableRow {
  [col: string]: string;
}

/** Extract rows from the first markdown table under a heading that matches `headingPattern`. */
function extractTableUnderHeading(body: string, headingPattern: RegExp): MarkdownTableRow[] {
  if (!body) return [];
  const lines = body.split(/\r?\n/);
  let inTarget = false;
  let headers: string[] = [];
  const rows: MarkdownTableRow[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    // Check for heading
    const hm = /^#{1,4}\s+(.+?)\s*$/.exec(line);
    if (hm) {
      if (headingPattern.test(hm[1])) {
        inTarget = true;
        headers = [];
        continue;
      } else if (inTarget) {
        break; // moved to next section
      }
    }
    if (!inTarget) continue;
    // Parse table
    if (line.trim().startsWith("|")) {
      const cells = line.split("|").map((c) => c.trim()).filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
      if (cells.length === 0) continue;
      if (headers.length === 0) {
        headers = cells;
        continue;
      }
      // Skip separator row (--|--|--)
      if (cells.every((c) => /^[-:]+$/.test(c))) continue;
      const row: MarkdownTableRow = {};
      cells.forEach((val, idx) => {
        row[headers[idx] ?? `col${idx}`] = val;
      });
      if (Object.values(row).some((v) => v && v !== "—" && !v.startsWith("_"))) {
        rows.push(row);
      }
    }
  }
  return rows;
}

/** Extract bullet list items under a heading. */
function extractBulletsUnderHeading(body: string, headingPattern: RegExp): string[] {
  if (!body) return [];
  const lines = body.split(/\r?\n/);
  let inTarget = false;
  const items: string[] = [];

  for (const line of lines) {
    const hm = /^#{1,4}\s+(.+?)\s*$/.exec(line);
    if (hm) {
      if (headingPattern.test(hm[1])) { inTarget = true; continue; }
      else if (inTarget) break;
    }
    if (!inTarget) continue;
    const bm = /^\s*[-*+]\s+(.+?)\s*$/.exec(line);
    if (bm) items.push(bm[1].replace(/\*\*/g, "").trim());
  }
  return items;
}

/** Parse plan.md for template-defined resources (Queues, Assets, Connections, Workflows). */
interface PlanResources {
  queues: Array<{ name: string; folder: string; notes: string }>;
  assets: Array<{ name: string; type: string; notes: string }>;
  connections: Array<{ name: string; system: string; surface: string }>;
  workflows: Array<{ file: string; type: string; deps: string }>;
  hitl: Array<{ label: string; channel: string; detail: string }>;
}

function extractPlanResources(planBody: string | undefined): PlanResources {
  if (!planBody) return { queues: [], assets: [], connections: [], workflows: [], hitl: [] };

  const queues = extractTableUnderHeading(planBody, /^queues?$/i).map((r) => ({
    name: r["Name"] ?? r["Queue"] ?? Object.values(r)[0] ?? "",
    folder: r["Target Folder"] ?? r["Folder"] ?? "",
    notes: r["Notes"] ?? "",
  })).filter((q) => q.name);

  const assets = extractTableUnderHeading(planBody, /^assets?$/i).map((r) => ({
    name: r["Name"] ?? r["Asset"] ?? Object.values(r)[0] ?? "",
    type: r["Type"] ?? "",
    notes: r["Notes"] ?? "",
  })).filter((a) => a.name);

  const connections = extractTableUnderHeading(planBody, /^connections?/i).map((r) => ({
    name: r["Name/id"] ?? r["Name"] ?? Object.values(r)[0] ?? "",
    system: r["Resource type"] ?? r["Type"] ?? "",
    surface: r["Owner surface"] ?? r["Surface"] ?? "",
  })).filter((c) => c.name);

  const workflows = extractTableUnderHeading(planBody, /^workflow catalog$/i).map((r) => ({
    file: r["Workflow file"] ?? r["Workflow"] ?? Object.values(r)[0] ?? "",
    type: r["Type"] ?? "",
    deps: r["Dependencies"] ?? "",
  })).filter((w) => w.file);

  // HITL from the Workflow Catalog where type hints human, or from a HITL-specific table
  const hitlRows = extractTableUnderHeading(planBody, /^hitl|human.*(in.the.loop|task|review)/i).map((r) => ({
    label: r["Name"] ?? Object.values(r)[0] ?? "",
    channel: r["Channel"] ?? r["Type"] ?? "",
    detail: r["Notes"] ?? r["Actor"] ?? "",
  })).filter((h) => h.label);

  return { queues, assets, connections, workflows, hitl: hitlRows };
}

function extractDecisionBullets(body: string | undefined): string[] {
  if (!body) return [];
  const decisions = body.match(/##\s+Decisions\s*\n([\s\S]*?)(?=\n##\s+|\s*$)/i)?.[1] ?? "";
  return decisions
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.startsWith("- "))
    .map((line) => line.slice(2).replace(/\*\*/g, "").trim())
    .filter(Boolean);
}

function extractMermaidBlocks(body: string): string[] {
  const blocks: string[] = [];
  const re = /```mermaid\s*([\s\S]*?)```/gi;
  let match: RegExpExecArray | null;
  while ((match = re.exec(body)) !== null) {
    blocks.push(match[1].trim());
  }
  return blocks;
}

function inferMermaidKind(block: string): string {
  const firstLine = block.split(/\r?\n/).map((line) => line.trim()).find(Boolean) ?? "diagram";
  if (/^flowchart\b/i.test(firstLine)) return "flowchart";
  if (/^sequenceDiagram\b/i.test(firstLine)) return "sequence";
  if (/^stateDiagram/i.test(firstLine)) return "state diagram";
  if (/^journey\b/i.test(firstLine)) return "journey map";
  if (/^gantt\b/i.test(firstLine)) return "gantt";
  if (/^classDiagram\b/i.test(firstLine)) return "class diagram";
  return "Mermaid diagram";
}

function extractMarkdownHeadings(body: string): string[] {
  return body
    .split(/\r?\n/)
    .map((line) => /^#{2,3}\s+(.+?)\s*$/.exec(line)?.[1]?.trim() ?? "")
    .filter(Boolean)
    .map((title) => title.replace(/^\d+\.\s*/, ""))
    .filter((title, index, all) => all.indexOf(title) === index);
}

function descriptorName(label: string): string {
  return label
    .replace(/\.[^.]+$/, "")
    .replace(/[^a-zA-Z0-9]+(.)/g, (_, chr: string) => chr.toUpperCase())
    .replace(/^[A-Z]/, (chr) => chr.toLowerCase()) || "node";
}

function buildN8nDescriptors(
  bundle: ProjectNode,
  docs: BundleDoc[],
  sections: SectionBucket[],
): N8nNodeDescriptor[] {
  const descriptors: N8nNodeDescriptor[] = [];
  const bundleId = `${bundle.id}:workflow-node`;
  descriptors.push({
    id: bundleId,
    displayName: bundle.label,
    name: descriptorName(bundle.label),
    group: ["input"],
    description: bundle.desc ?? "UiPlan bundle entry point.",
    defaults: { name: bundle.label, color: "#0f766e" },
    inputs: [],
    outputs: ["main"],
    credentials: [],
    properties: [
      { displayName: "Documents", name: "documents", value: String(docs.length) },
      { displayName: "Tasks", name: "tasks", value: String(sections.reduce((acc, s) => acc + s.counts.total, 0)) },
    ],
    sourceNodeId: bundle.id,
    upstreamIds: [],
    x: 24,
    y: 44,
  });

  let previousId = bundleId;
  docs.forEach((doc, index) => {
    const id = `${doc.id}:workflow-node`;
    const isTasks = doc.kind === "uiplan_tasks";
    descriptors.push({
      id,
      displayName: doc.label,
      name: descriptorName(doc.label),
      group: [isTasks ? "transform" : "input"],
      description: isTasks ? "Task checklist parsed into executable work nodes." : "Planning document used as node configuration.",
      defaults: { name: doc.label, color: isTasks ? "#7c3aed" : "#2563eb" },
      inputs: ["main"],
      outputs: ["main"],
      credentials: [],
      properties: [
        { displayName: "Path", name: "path", value: doc.path },
        { displayName: "Lines", name: "lines", value: String(doc.body.split(/\r?\n/).filter(Boolean).length) },
      ],
      sourceNodeId: doc.id,
      upstreamIds: [previousId],
      x: 340 + index * 316,
      y: 44,
    });
    previousId = id;
  });

  const sectionStartX = 180;
  const sectionStartY = 232;
  const colWidth = 316;
  const rowHeight = 174;
  const upstream = docs.length > 0 ? previousId : bundleId;
  sections.forEach((section, index) => {
    const col = index % 3;
    const row = Math.floor(index / 3);
    const title = section.section || "Unsectioned tasks";
    const firstTask = section.tasks[0];
    descriptors.push({
      id: `${bundle.id}:section:${section.order}`,
      displayName: title,
      name: descriptorName(title),
      group: ["transform"],
      description: "Task section node with n8n-style inputs, outputs, credentials, and properties.",
      defaults: { name: title, color: TASK_STATUS_COLOR[section.bucket] ?? "#6b7280" },
      inputs: ["main"],
      outputs: ["main"],
      credentials: [],
      properties: [
        { displayName: "Resource", name: "resource", value: "UiPlan Task Section" },
        { displayName: "Operation", name: "operation", value: section.bucket.replace("_", " ") },
        { displayName: "Tasks", name: "tasks", value: String(section.counts.total) },
        { displayName: "Done", name: "done", value: `${section.counts.done}/${section.counts.total}` },
      ],
      sourceNodeId: firstTask?.id,
      taskIds: section.tasks.map((task) => task.id),
      upstreamIds: [upstream],
      x: sectionStartX + col * colWidth,
      y: sectionStartY + row * rowHeight,
    });
  });

  return descriptors;
}

// Retained for developer-mode experiments; UiPlan default uses the TO-BE architecture canvas.
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function N8nWorkflowFlow({ bundle, tasks, selectedNodeId, onSelectNode }: {
  bundle: ProjectNode;
  tasks: ProjectNode[];
  selectedNodeId: string | null;
  onSelectNode: (id: string) => void;
}) {
  const docs = useMemo(() => collectBundleDocs(bundle), [bundle]);
  const sections = useMemo(() => bucketSectionsByStatus(tasks), [tasks]);
  const descriptors = useMemo(
    () => buildN8nDescriptors(bundle, docs, sections),
    [bundle, docs, sections],
  );
  const byId = useMemo(() => new Map(descriptors.map((node) => [node.id, node])), [descriptors]);
  const width = Math.max(980, ...descriptors.map((node) => node.x + 292));
  const height = Math.max(520, ...descriptors.map((node) => node.y + 136));

  return (
    <div style={{
      position: "relative",
      minWidth: width,
      minHeight: height,
      background: "radial-gradient(circle at 1px 1px, #ddd 1px, transparent 0)",
      backgroundSize: "22px 22px",
      border: `1px solid ${PALETTE.rule}`,
      borderRadius: 8,
      overflow: "hidden",
    }}>
      <svg
        width={width}
        height={height}
        style={{ position: "absolute", inset: 0, pointerEvents: "none" }}
      >
        <defs>
          <marker id="uiplan-node-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M 0 0 L 8 4 L 0 8 z" fill="#94a3b8" />
          </marker>
        </defs>
        {descriptors.flatMap((target) => target.upstreamIds.map((sourceId) => {
          const source = byId.get(sourceId);
          if (!source) return null;
          const ax = source.x + 268;
          const ay = source.y + 58;
          const bx = target.x;
          const by = target.y + 58;
          const midX = ax + Math.max(54, Math.floor((bx - ax) * 0.45));
          // Orthogonal corridor routing keeps edges readable in dense plans.
          const path = `M ${ax} ${ay} L ${midX} ${ay} L ${midX} ${by} L ${bx} ${by}`;
          return (
            <path
              key={`${sourceId}->${target.id}`}
              d={path}
              fill="none"
              stroke="#94a3b8"
              strokeWidth={2}
              markerEnd="url(#uiplan-node-arrow)"
            />
          );
        }))}
      </svg>

      <div style={{
        position: "absolute", top: 12, left: 16,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 12, letterSpacing: "0.16em", fontWeight: 700,
        color: PALETTE.textDim,
      }}>
        WORKFLOW FLOW MAP
      </div>

      {descriptors.map((node) => {
        const selected = node.sourceNodeId === selectedNodeId || !!node.taskIds?.includes(selectedNodeId ?? "");
        return (
          <N8nNodeCard
            key={node.id}
            node={node}
            selected={selected}
            onClick={() => {
              const target = node.sourceNodeId ?? node.taskIds?.[0] ?? bundle.id;
              onSelectNode(target);
            }}
          />
        );
      })}
    </div>
  );
}

function N8nNodeCard({ node, selected, onClick }: {
  node: N8nNodeDescriptor;
  selected: boolean;
  onClick: () => void;
}) {
  const Icon = node.group.includes("input") ? FileText : ListChecks;
  return (
    <button
      onClick={onClick}
      style={{
        position: "absolute",
        left: node.x,
        top: node.y,
        width: 268,
        minHeight: 92,
        padding: 0,
        background: PALETTE.panel,
        border: `2px solid ${selected ? node.defaults.color : PALETTE.rule}`,
        borderRadius: 10,
        cursor: "pointer",
        textAlign: "left",
        boxShadow: selected
          ? `0 0 0 4px ${node.defaults.color}22, 0 10px 28px rgba(15, 23, 42, 0.16)`
          : "0 4px 14px rgba(15, 23, 42, 0.08)",
        fontFamily: "'Inter', sans-serif",
        color: PALETTE.text,
      }}
    >
      {node.inputs.map((input, index) => (
        <span
          key={input}
          title={`input: ${input}`}
          style={{
            position: "absolute", left: -7, top: 48 + index * 16,
            width: 12, height: 12, borderRadius: "50%",
            background: PALETTE.panel,
            border: "2px solid #94a3b8",
          }}
        />
      ))}
      {node.outputs.map((output, index) => (
        <span
          key={output}
          title={`output: ${output}`}
          style={{
            position: "absolute", right: -7, top: 48 + index * 16,
            width: 12, height: 12, borderRadius: "50%",
            background: "#94a3b8",
            border: `2px solid ${PALETTE.panel}`,
          }}
        />
      ))}

      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "11px 12px 9px",
        borderBottom: `1px solid ${PALETTE.ruleSoft}`,
      }}>
        <div style={{
          width: 34, height: 34,
          display: "flex", alignItems: "center", justifyContent: "center",
          background: `${node.defaults.color}18`,
          border: `1px solid ${node.defaults.color}55`,
          borderRadius: 8,
          flexShrink: 0,
        }}>
          <Icon size={17} color={node.defaults.color} strokeWidth={2.2} />
        </div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{
            fontSize: 13, fontWeight: 700,
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
          }}>
            {node.displayName}
          </div>
          <div style={{
            marginTop: 2,
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 12, letterSpacing: "0.12em",
            color: node.defaults.color, fontWeight: 700,
            textTransform: "uppercase",
          }}>
            {node.group.join(", ")}
          </div>
        </div>
      </div>

      <div style={{ padding: "9px 12px 11px" }}>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <NodePill Icon={Settings2} label={`${node.properties.length} props`} />
          <NodePill
            Icon={KeyRound}
            label={node.credentials.length > 0 ? `${node.credentials.length} creds` : "no creds"}
          />
          <NodePill label={`${node.inputs.length} in / ${node.outputs.length} out`} />
        </div>
      </div>
    </button>
  );
}

function NodePill({ Icon, label }: {
  Icon?: React.ComponentType<{ size?: number; color?: string; strokeWidth?: number }>;
  label: string;
}) {
  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 4,
      padding: "2px 6px",
      border: `1px solid ${PALETTE.rule}`,
      borderRadius: 999,
      background: PALETTE.bg,
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: 12,
      letterSpacing: "0.08em",
      color: PALETTE.textDim,
      textTransform: "uppercase",
    }}>
      {Icon && <Icon size={9} color={PALETTE.textDim} strokeWidth={2.4} />}
      {label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Phase Flow
// ---------------------------------------------------------------------------

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function PhaseFlow({ phases, tasks, selectedPhaseIdx, onSelectPhase }: {
  phases: Phase[];
  tasks: ProjectNode[];
  selectedPhaseIdx: number | null;
  compactMode: boolean;
  onSelectPhase: (idx: number) => void;
}) {
  if (phases.length === 0) {
    return (
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "center",
        height: "100%", flexDirection: "column", gap: 12,
      }}>
        <div style={{
          padding: "16px 20px", background: PALETTE.panel,
          border: `1px solid ${PALETTE.rule}`, borderRadius: 6,
          fontFamily: "'JetBrains Mono', monospace", fontWeight: 700,
          fontSize: 12, letterSpacing: "0.2em", color: PALETTE.text,
        }}>
          PLAN
        </div>
        <div style={{
          fontSize: 12, color: PALETTE.textDim,
          fontFamily: "'Newsreader', Georgia, serif", fontStyle: "italic",
        }}>
          No phases were detected in this bundle's plan.md.
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 16, alignItems: "stretch" }}>
      {phases.map((p, i) => {
        const count = tasks.filter((t) => taskMatchesPhase(t, p)).length;
        const active = selectedPhaseIdx === i;
        return (
          <React.Fragment key={p.index}>
            <button
              onClick={() => onSelectPhase(i)}
              style={{
                width: 220, padding: compactMode ? "10px 12px" : "14px 16px",
                background: active ? "#ccfbf1" : PALETTE.panel,
                border: `1px solid ${active ? "#0f766e" : PALETTE.rule}`,
                borderLeft: `4px solid ${active ? "#0f766e" : "#0f766e88"}`,
                borderRadius: 6, cursor: "pointer", textAlign: "left",
                display: "flex", flexDirection: "column", gap: 8,
                fontFamily: "'Inter', sans-serif",
              }}
            >
              <div style={{
                fontSize: 12, letterSpacing: "0.22em", fontWeight: 700,
                color: "#0f766e", fontFamily: "'JetBrains Mono', monospace",
              }}>
                PHASE {String(i + 1).padStart(2, "0")}
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: PALETTE.text, lineHeight: 1.35 }}>
                {p.title}
              </div>
              {!compactMode && (
                <div style={{
                  marginTop: "auto", fontSize: 12,
                  fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.1em",
                  color: PALETTE.textDim,
                }}>
                  {count} TASK{count === 1 ? "" : "S"}
                </div>
              )}
              {count === 0 && (
                <div style={{
                  marginTop: "auto",
                  fontSize: 12,
                  color: PALETTE.textMute,
                  fontFamily: "'JetBrains Mono', monospace",
                  letterSpacing: "0.08em",
                }}>
                  NO TASKS YET
                </div>
              )}
            </button>
            {i < phases.length - 1 && (
              <div style={{ display: "flex", alignItems: "center", color: PALETTE.textMute, fontSize: 18 }}>
                →
              </div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

function StatusIcon({ status }: { status: string }) {
  const color = TASK_STATUS_COLOR[status] ?? PALETTE.textDim;
  const Icon = status === "done" ? CheckSquare
    : status === "cancelled" ? MinusSquare
    : status === "in_progress" ? Circle
    : Square;
  return <Icon size={14} color={color} strokeWidth={2} />;
}

// ---------------------------------------------------------------------------
// Kanban
// ---------------------------------------------------------------------------

interface SectionBucket {
  /** Section heading text from `tasks.md` (e.g. "Phase 1 — Setup"). Empty
   * string means tasks that aren't under any heading; rendered as "(no section)". */
  section: string;
  /** Sequential index in declaration order — used to keep stable section ordering. */
  order: number;
  tasks: ProjectNode[];
  counts: { pending: number; in_progress: number; done: number; cancelled: number; total: number };
  /** Where the section card lands. Rule:
   *   - all tasks done (or done+cancelled) → "done"
   *   - any in_progress, OR a mix of done + pending → "in_progress"
   *   - otherwise → "pending"
   *   - 100% cancelled → "cancelled"
   */
  bucket: "pending" | "in_progress" | "done" | "cancelled";
}

function bucketSectionsByStatus(tasks: ProjectNode[]): SectionBucket[] {
  const map = new Map<string, SectionBucket>();
  let order = 0;
  for (const t of tasks) {
    const section = String(t.meta?.task_section ?? "").trim();
    let entry = map.get(section);
    if (!entry) {
      entry = {
        section,
        order: order++,
        tasks: [],
        counts: { pending: 0, in_progress: 0, done: 0, cancelled: 0, total: 0 },
        bucket: "pending",
      };
      map.set(section, entry);
    }
    entry.tasks.push(t);
    const s = taskStatus(t) as keyof SectionBucket["counts"];
    entry.counts[s] = (entry.counts[s] ?? 0) + 1;
    entry.counts.total += 1;
  }
  for (const entry of map.values()) {
    const c = entry.counts;
    const active = c.total - c.cancelled;
    if (active === 0) {
      entry.bucket = "cancelled";
    } else if (c.in_progress > 0 || (c.done > 0 && c.done < active)) {
      entry.bucket = "in_progress";
    } else if (c.done >= active) {
      entry.bucket = "done";
    } else {
      entry.bucket = "pending";
    }
  }
  return Array.from(map.values()).sort((a, b) => a.order - b.order);
}

// ---------------------------------------------------------------------------
// 3-pane TasksView: FileNavigator | DocContent | ContextKnowledgePanel
// ---------------------------------------------------------------------------

interface TaskWithDoc {
  task: ProjectNode;
  docId: string;
  docLabel: string;
}

function collectTasksWithDocs(bundle: ProjectNode): TaskWithDoc[] {
  const out: TaskWithDoc[] = [];
  for (const child of bundle.children?.nodes ?? []) {
    if (child.kind === "uiplan_tasks") {
      const docLabel = child.label || "tasks.md";
      const docId = child.id;
      for (const t of child.children?.nodes ?? []) {
        if (t.kind === "uiplan_task") {
          out.push({ task: t, docId, docLabel });
        }
      }
    } else if (child.kind === "uiplan_task") {
      out.push({ task: child, docId: bundle.id, docLabel: "tasks.md" });
    }
  }
  return out;
}

function TasksView({ tasks, compactMode, selectedNodeId, onSelectNode, docs, toBeView, mode }: {
  tasks: ProjectNode[];
  compactMode: boolean;
  selectedNodeId: string | null;
  onSelectNode: (id: string) => void;
  docs: BundleDoc[];
  toBeView: ToBeView | null;
  mode: Mode;
}) {
  // Default to tasks.md, then plan.md, then whatever's first
  const defaultDocId = (
    docs.find((d) => /tasks\.md$/i.test(d.label)) ??
    docs.find((d) => /plan\.md$/i.test(d.label)) ??
    docs[0]
  )?.id ?? null;
  const [selectedDocId, setSelectedDocId] = useState<string | null>(defaultDocId);
  const [contextOpen, setContextOpen] = useState(true);

  const selectedDoc = docs.find((d) => d.id === selectedDocId) ?? docs[0] ?? null;
  const isTasksDoc = selectedDoc != null && /tasks\.md$/i.test(selectedDoc.label);

  return (
    <div style={{ display: "flex", height: "100%", overflow: "hidden" }}>
      {/* LEFT: file navigator */}
      <FileNavigator
        docs={docs}
        tasks={tasks}
        selectedDocId={selectedDocId}
        onSelectDoc={setSelectedDocId}
      />

      {/* CENTER: doc content */}
      <div style={{ flex: 1, overflow: "auto", minWidth: 0, borderRight: `1px solid ${PALETTE.rule}` }}>
        {selectedDoc ? (
          isTasksDoc ? (
            <TasksDocView
              doc={selectedDoc}
              tasks={tasks}
              compactMode={compactMode}
              selectedNodeId={selectedNodeId}
              onSelectNode={onSelectNode}
              mode={mode}
            />
          ) : (
            <PlanDocView doc={selectedDoc} />
          )
        ) : (
          <div style={{ padding: 32, color: PALETTE.textDim, fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>
            SELECT A PLAN FILE
          </div>
        )}
      </div>

      {/* RIGHT: context panel (collapsible) */}
      {contextOpen ? (
        <ContextKnowledgePanel
          mode={mode}
          selectedTask={tasks.find((t) => t.id === selectedNodeId) ?? null}
          toBeView={toBeView}
          docs={docs}
          tasks={tasks}
          onClose={() => setContextOpen(false)}
        />
      ) : (
        <button
          onClick={() => setContextOpen(true)}
          title="Open context panel"
          style={{
            width: 24,
            flexShrink: 0,
            border: "none",
            borderLeft: `1px solid ${PALETTE.rule}`,
            background: PALETTE.panel,
            color: PALETTE.textDim,
            cursor: "pointer",
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 10,
            writingMode: "vertical-rl",
            letterSpacing: "0.1em",
            padding: "12px 0",
          }}
        >
          ◀ CONTEXT
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// File Navigator (left panel)
// ---------------------------------------------------------------------------

function docIcon(label: string): string {
  const lower = label.toLowerCase();
  if (lower.includes("spec")) return "📋";
  if (lower.includes("plan")) return "🗺";
  if (lower.includes("task")) return "✅";
  return "📄";
}

function docAccentColor(label: string): string {
  const lower = label.toLowerCase();
  if (lower.includes("spec")) return "#d97706";
  if (lower.includes("plan")) return "#2563eb";
  if (lower.includes("task")) return "#7c3aed";
  return "#0f766e";
}

function FileNavigator({ docs, tasks, selectedDocId, onSelectDoc }: {
  docs: BundleDoc[];
  tasks: ProjectNode[];
  selectedDocId: string | null;
  onSelectDoc: (id: string) => void;
}) {
  const tasksByDocId = useMemo(() => {
    const m = new Map<string, number>();
    for (const t of tasks) {
      const key = String(t.meta?.doc_id ?? "");
      if (key) m.set(key, (m.get(key) ?? 0) + 1);
    }
    return m;
  }, [tasks]);

  const totalTasks = tasks.length;
  const doneTasks = tasks.filter((t) => taskStatus(t) === "done").length;
  const donePct = totalTasks === 0 ? 0 : Math.round((doneTasks / totalTasks) * 100);

  return (
    <div style={{
      width: 220,
      flexShrink: 0,
      background: PALETTE.panel,
      borderRight: `1px solid ${PALETTE.rule}`,
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
    }}>
      <div style={{
        padding: "12px 14px 10px",
        borderBottom: `1px solid ${PALETTE.rule}`,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
        letterSpacing: "0.18em",
        fontWeight: 800,
        color: PALETTE.textDim,
      }}>
        PLAN FILES
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "8px 0" }}>
        {docs.map((doc) => {
          const isSelected = doc.id === selectedDocId;
          const diagrams = extractMermaidBlocks(doc.body).length;
          const isTasksDoc = /tasks\.md$/i.test(doc.label);
          const accent = docAccentColor(doc.label);
          const taskCount = isTasksDoc ? totalTasks : (tasksByDocId.get(doc.id) ?? 0);

          return (
            <button
              key={doc.id}
              onClick={() => onSelectDoc(doc.id)}
              style={{
                width: "100%",
                textAlign: "left",
                border: "none",
                borderLeft: `3px solid ${isSelected ? accent : "transparent"}`,
                background: isSelected ? `${accent}12` : "transparent",
                padding: "10px 12px 10px 11px",
                cursor: "pointer",
                display: "flex",
                flexDirection: "column",
                gap: 4,
                fontFamily: "'Inter', sans-serif",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                <span style={{ fontSize: 13 }}>{docIcon(doc.label)}</span>
                <span style={{
                  fontSize: 13,
                  fontWeight: isSelected ? 700 : 500,
                  color: isSelected ? accent : PALETTE.text,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  flex: 1,
                }}>
                  {doc.label}
                </span>
              </div>
              <div style={{
                display: "flex",
                gap: 6,
                paddingLeft: 20,
                flexWrap: "wrap",
              }}>
                {diagrams > 0 && (
                  <span style={{
                    fontSize: 10,
                    fontFamily: "'JetBrains Mono', monospace",
                    color: "#0f766e",
                    background: "#ccfbf1",
                    padding: "1px 5px",
                    borderRadius: 3,
                    fontWeight: 700,
                    letterSpacing: "0.05em",
                  }}>
                    {diagrams} diagram{diagrams !== 1 ? "s" : ""}
                  </span>
                )}
                {isTasksDoc && totalTasks > 0 && (
                  <span style={{
                    fontSize: 10,
                    fontFamily: "'JetBrains Mono', monospace",
                    color: accent,
                    background: `${accent}18`,
                    padding: "1px 5px",
                    borderRadius: 3,
                    fontWeight: 700,
                    letterSpacing: "0.05em",
                  }}>
                    {donePct}% done
                  </span>
                )}
                {!isTasksDoc && taskCount > 0 && (
                  <span style={{
                    fontSize: 10,
                    fontFamily: "'JetBrains Mono', monospace",
                    color: PALETTE.textDim,
                    padding: "1px 5px",
                    borderRadius: 3,
                  }}>
                    {taskCount} tasks
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {/* Summary footer */}
      {totalTasks > 0 && (
        <div style={{
          borderTop: `1px solid ${PALETTE.rule}`,
          padding: "10px 14px",
          display: "flex",
          flexDirection: "column",
          gap: 5,
        }}>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 10,
            letterSpacing: "0.14em",
            color: PALETTE.textDim,
            fontWeight: 700,
          }}>
            OVERALL PROGRESS
          </div>
          <div style={{
            height: 4,
            background: PALETTE.rule,
            borderRadius: 2,
            overflow: "hidden",
          }}>
            <div style={{
              height: "100%",
              width: `${donePct}%`,
              background: donePct === 100 ? "#059669" : "#0f766e",
              borderRadius: 2,
              transition: "width 0.3s",
            }} />
          </div>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 10,
            color: PALETTE.textDim,
          }}>
            {doneTasks}/{totalTasks} tasks done
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Mermaid diagram preview block
// ---------------------------------------------------------------------------

let _mermaidIdCounter = 0;

function MermaidDiagramBlock({ code, index }: { code: string; index: number }) {
  const [svgHtml, setSvgHtml] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSource, setShowSource] = useState(false);
  const idRef = useRef(`mermaid-${++_mermaidIdCounter}`);
  const kind = inferMermaidKind(code);

  useEffect(() => {
    let cancelled = false;
    setSvgHtml(null);
    setError(null);
    mermaid.render(idRef.current, code).then(({ svg }) => {
      if (!cancelled) setSvgHtml(svg);
    }).catch((err: unknown) => {
      if (!cancelled) setError(String(err).slice(0, 200));
    });
    return () => { cancelled = true; };
  }, [code]);

  return (
    <div style={{
      border: `1px solid #e2e8f0`,
      borderRadius: 8,
      overflow: "hidden",
      marginBottom: 16,
      background: "#fff",
      boxShadow: "0 1px 3px #0000000d",
    }}>
      {/* Header bar */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "7px 12px",
        background: "#f8fafc",
        borderBottom: "1px solid #e2e8f0",
      }}>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 10,
          letterSpacing: "0.14em",
          fontWeight: 800,
          color: "#0f766e",
          background: "#ccfbf1",
          padding: "2px 6px",
          borderRadius: 3,
        }}>
          DIAGRAM {index + 1}
        </span>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11,
          color: "#475569",
          fontWeight: 600,
        }}>
          {kind.toUpperCase()}
        </span>
        <div style={{ flex: 1 }} />
        <button
          onClick={() => setShowSource((v) => !v)}
          style={{
            border: "1px solid #e2e8f0",
            background: showSource ? "#f1f5f9" : "transparent",
            borderRadius: 4,
            padding: "2px 8px",
            cursor: "pointer",
            fontSize: 11,
            color: PALETTE.textDim,
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          {showSource ? "hide source" : "source"}
        </button>
      </div>

      {/* Rendered SVG */}
      {!error && (
        <div style={{
          padding: "16px",
          overflowX: "auto",
          background: "#fff",
          minHeight: svgHtml ? undefined : 60,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}>
          {svgHtml ? (
            <div
              style={{ maxWidth: "100%", lineHeight: 0 }}
              dangerouslySetInnerHTML={{ __html: svgHtml }}
            />
          ) : (
            <div style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 11,
              color: PALETTE.textMute,
              padding: "12px 0",
            }}>
              rendering…
            </div>
          )}
        </div>
      )}

      {/* Error fallback */}
      {error && (
        <div style={{ padding: "12px 14px" }}>
          <div style={{
            fontSize: 11,
            color: "#dc2626",
            fontFamily: "'JetBrains Mono', monospace",
            marginBottom: 8,
          }}>
            Render error — showing source
          </div>
          <pre style={{
            margin: 0,
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            lineHeight: 1.6,
            color: "#334155",
            overflowX: "auto",
            whiteSpace: "pre",
          }}>
            {code}
          </pre>
        </div>
      )}

      {/* Source toggle */}
      {showSource && !error && (
        <div style={{ borderTop: "1px solid #e2e8f0" }}>
          <pre style={{
            margin: 0,
            padding: "12px 14px",
            background: "#f8fafc",
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            lineHeight: 1.6,
            color: "#334155",
            overflowX: "auto",
            whiteSpace: "pre",
          }}>
            {code}
          </pre>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// TasksDocView: for tasks.md — sections + tasks + embedded diagrams
// ---------------------------------------------------------------------------

function TasksDocView({ doc, tasks, compactMode, selectedNodeId, onSelectNode, mode }: {
  doc: BundleDoc;
  tasks: ProjectNode[];
  compactMode: boolean;
  selectedNodeId: string | null;
  onSelectNode: (id: string) => void;
  mode: Mode;
}) {
  const sections = useMemo(() => bucketSectionsByStatus(tasks), [tasks]);
  const diagrams = useMemo(() => extractMermaidBlocks(doc.body), [doc.body]);
  const [viewMode, setViewMode] = useState<"sections" | "kanban">("sections");

  const total = tasks.length;
  const done = tasks.filter((t) => taskStatus(t) === "done").length;
  const inProgress = tasks.filter((t) => taskStatus(t) === "in_progress").length;
  const pending = tasks.filter((t) => taskStatus(t) === "pending").length;
  const donePct = total === 0 ? 0 : Math.round((done / total) * 100);

  return (
    <div style={{ padding: "20px 24px", minHeight: "100%" }}>
      {/* Header */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        marginBottom: 16,
        paddingBottom: 12,
        borderBottom: `1px solid ${PALETTE.rule}`,
      }}>
        <div style={{ flex: 1 }}>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            letterSpacing: "0.18em",
            fontWeight: 800,
            color: "#7c3aed",
            marginBottom: 2,
          }}>
            BUILD BACKLOG
          </div>
          <div style={{ fontSize: 16, fontWeight: 800, color: PALETTE.text }}>
            {doc.label}
          </div>
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <div style={{ display: "flex", gap: 6 }}>
            {[
              { label: "done", count: done, color: "#059669" },
              { label: "wip", count: inProgress, color: "#d97706" },
              { label: "open", count: pending, color: "#6b7280" },
            ].map((s) => (
              <div key={s.label} style={{
                textAlign: "center",
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 11,
              }}>
                <div style={{ fontSize: 18, fontWeight: 800, color: s.color }}>{s.count}</div>
                <div style={{ color: PALETTE.textDim, letterSpacing: "0.1em" }}>{s.label.toUpperCase()}</div>
              </div>
            ))}
          </div>
          {/* progress ring */}
          <svg width={48} height={48}>
            <circle cx={24} cy={24} r={20} fill="none" stroke={PALETTE.rule} strokeWidth={4} />
            <circle
              cx={24} cy={24} r={20}
              fill="none"
              stroke={donePct === 100 ? "#059669" : "#7c3aed"}
              strokeWidth={4}
              strokeDasharray={`${(donePct / 100) * 125.7} 125.7`}
              strokeLinecap="round"
              transform="rotate(-90 24 24)"
            />
            <text x={24} y={29} textAnchor="middle" fontSize={11} fontWeight={800} fill={PALETTE.text}
              fontFamily="'JetBrains Mono', monospace">
              {donePct}%
            </text>
          </svg>
        </div>
        <div style={{ display: "flex", gap: 4 }}>
          {(["sections", "kanban"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setViewMode(m)}
              style={{
                background: viewMode === m ? "#7c3aed" : PALETTE.bg,
                color: viewMode === m ? "#fff" : PALETTE.textDim,
                border: `1px solid ${viewMode === m ? "#7c3aed" : PALETTE.rule}`,
                borderRadius: 5,
                padding: "6px 10px",
                cursor: "pointer",
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 11,
                letterSpacing: "0.08em",
                fontWeight: 700,
              }}
            >
              {m.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Embedded diagrams */}
      {diagrams.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            letterSpacing: "0.14em",
            color: PALETTE.textDim,
            marginBottom: 8,
            fontWeight: 700,
          }}>
            EMBEDDED DIAGRAMS ({diagrams.length})
          </div>
          {diagrams.map((code, i) => (
            <MermaidDiagramBlock key={i} code={code} index={i} />
          ))}
        </div>
      )}

      {/* Tasks content */}
      {viewMode === "sections" ? (
        <TaskSectionsList
          sections={sections}
          selectedNodeId={selectedNodeId}
          onSelectNode={onSelectNode}
          mode={mode}
        />
      ) : (
        <KanbanBoard
          sections={sections}
          selectedNodeId={selectedNodeId}
          onSelectNode={onSelectNode}
          mode={mode}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// PlanDocView: for spec.md / plan.md — sections + diagrams
// ---------------------------------------------------------------------------

/** A heading entry paired with its diagram heading title (for diagram nav). */
interface DiagramEntry {
  code: string;
  section: string;
  diagramIdx: number;
}

function PlanDocView({ doc }: { doc: BundleDoc }) {
  const diagrams = useMemo(() => extractMermaidBlocks(doc.body), [doc.body]);
  const headings = useMemo(() => extractMarkdownHeadingsWithContent(doc.body), [doc.body]);
  const isSpec = /spec\.md$/i.test(doc.label);
  const isPlan = /plan\.md$/i.test(doc.label);
  const accent = docAccentColor(doc.label);
  const [tab, setTab] = useState<"sections" | "diagrams">(diagrams.length > 0 ? "diagrams" : "sections");

  // Build flat list of diagrams with their section title
  const diagramEntries = useMemo<DiagramEntry[]>(() => {
    const entries: DiagramEntry[] = [];
    let globalIdx = 0;
    for (const h of headings) {
      for (const code of h.diagrams) {
        entries.push({ code, section: h.title, diagramIdx: globalIdx++ });
      }
    }
    // orphan diagrams not captured by headings
    if (entries.length === 0 && diagrams.length > 0) {
      diagrams.forEach((code, i) => entries.push({ code, section: doc.label, diagramIdx: i }));
    }
    return entries;
  }, [headings, diagrams, doc.label]);

  const tabs: Array<{ id: "sections" | "diagrams"; label: string }> = [
    { id: "diagrams", label: `DIAGRAMS (${diagrams.length})` },
    { id: "sections", label: `SECTIONS (${headings.length})` },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Sticky header + tabs */}
      <div style={{
        padding: "16px 24px 0",
        background: "#fff",
        borderBottom: `1px solid ${PALETTE.rule}`,
        flexShrink: 0,
      }}>
        <div style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 10,
          letterSpacing: "0.18em",
          fontWeight: 800,
          color: accent,
          marginBottom: 2,
        }}>
          {isSpec ? "PROJECT BRIEF" : isPlan ? "SOLUTION DESIGN" : "PLAN DOCUMENT"}
        </div>
        <div style={{ fontSize: 15, fontWeight: 800, color: PALETTE.text, marginBottom: 10 }}>
          {doc.label}
        </div>

        {/* Tab bar */}
        <div style={{ display: "flex", gap: 2 }}>
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              style={{
                border: "none",
                borderBottom: tab === t.id ? `2px solid ${accent}` : "2px solid transparent",
                background: "transparent",
                padding: "6px 14px",
                cursor: "pointer",
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: "0.1em",
                color: tab === t.id ? accent : PALETTE.textDim,
              }}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Scrollable content */}
      <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>

        {tab === "diagrams" && (
          <div>
            {diagramEntries.length === 0 ? (
              <div style={{ color: PALETTE.textMute, fontFamily: "'JetBrains Mono', monospace", fontSize: 12, padding: "20px 0" }}>
                No diagrams found in this file.
              </div>
            ) : (
              diagramEntries.map((entry) => (
                <div key={entry.diagramIdx} style={{ marginBottom: 28 }}>
                  <div style={{
                    fontSize: 12,
                    fontWeight: 600,
                    color: PALETTE.textDim,
                    fontFamily: "'Inter', sans-serif",
                    marginBottom: 8,
                    paddingBottom: 4,
                    borderBottom: `1px solid ${PALETTE.ruleSoft}`,
                  }}>
                    {entry.section}
                  </div>
                  <MermaidDiagramBlock code={entry.code} index={entry.diagramIdx} />
                </div>
              ))
            )}
          </div>
        )}

        {tab === "sections" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {headings.map((heading, i) => (
              <div key={i}>
                <div style={{
                  padding: "8px 0 6px",
                  borderBottom: `1px solid ${PALETTE.ruleSoft}`,
                  marginBottom: 8,
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}>
                  <span style={{
                    fontSize: heading.level === 2 ? 14 : 13,
                    fontWeight: heading.level === 2 ? 700 : 600,
                    color: heading.level === 2 ? PALETTE.text : PALETTE.textDim,
                    fontFamily: "'Inter', sans-serif",
                  }}>
                    {heading.title}
                  </span>
                  {heading.diagrams.length > 0 && (
                    <span style={{
                      fontSize: 10,
                      fontFamily: "'JetBrains Mono', monospace",
                      color: "#0f766e",
                      background: "#ccfbf1",
                      padding: "1px 5px",
                      borderRadius: 3,
                      fontWeight: 700,
                    }}>
                      {heading.diagrams.length} diagram{heading.diagrams.length > 1 ? "s" : ""}
                    </span>
                  )}
                </div>
                {heading.diagrams.map((code, di) => (
                  <MermaidDiagramBlock key={di} code={code} index={di} />
                ))}
                {heading.body.trim() && (
                  <div style={{
                    fontSize: 13,
                    color: PALETTE.textDim,
                    lineHeight: 1.6,
                    whiteSpace: "pre-wrap",
                    fontFamily: "'Inter', sans-serif",
                  }}>
                    {heading.body.replace(/```[\s\S]*?```/g, "").trim().slice(0, 400)}
                    {heading.body.length > 400 && <span style={{ color: PALETTE.textMute }}> …</span>}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface HeadingWithContent {
  title: string;
  level: 2 | 3;
  body: string;
  diagrams: string[];
}

function extractMarkdownHeadingsWithContent(body: string): HeadingWithContent[] {
  const lines = body.split(/\r?\n/);
  const out: HeadingWithContent[] = [];
  let current: HeadingWithContent | null = null;
  let inCode = false;

  for (const line of lines) {
    if (line.startsWith("```")) {
      inCode = !inCode;
      if (current) current.body += line + "\n";
      continue;
    }
    if (inCode) {
      if (current) current.body += line + "\n";
      continue;
    }

    const h2 = /^##\s+(.+?)\s*$/.exec(line);
    const h3 = !h2 && /^###\s+(.+?)\s*$/.exec(line);

    if (h2 || h3) {
      if (current) {
        current.diagrams = extractMermaidBlocks(current.body);
        out.push(current);
      }
      current = {
        title: (h2 ?? h3)![1].trim(),
        level: h2 ? 2 : 3,
        body: "",
        diagrams: [],
      };
    } else if (current) {
      current.body += line + "\n";
    }
  }
  if (current) {
    current.diagrams = extractMermaidBlocks(current.body);
    out.push(current);
  }
  return out.slice(0, 20); // cap for performance
}

// ---------------------------------------------------------------------------
// Task sections list (the main tasks view)
// ---------------------------------------------------------------------------

function TaskSectionsList({ sections, selectedNodeId, onSelectNode, mode }: {
  sections: SectionBucket[];
  selectedNodeId: string | null;
  onSelectNode: (id: string) => void;
  mode: Mode;
}) {
  if (sections.length === 0) {
    return (
      <div style={{
        padding: "32px 0", textAlign: "center",
        color: PALETTE.textDim,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 12,
        letterSpacing: "0.14em",
      }}>
        NO TASKS FOUND IN THIS FILE
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {sections.map((s) => (
        <TaskSectionBlock
          key={`${s.section || "unsectioned"}-${s.order}`}
          section={s}
          selectedNodeId={selectedNodeId}
          onSelectNode={onSelectNode}
          mode={mode}
        />
      ))}
    </div>
  );
}

function TaskSectionBlock({ section, selectedNodeId, onSelectNode, mode }: {
  section: SectionBucket;
  selectedNodeId: string | null;
  onSelectNode: (id: string) => void;
  mode: Mode;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const c = section.counts;
  const color = TASK_STATUS_COLOR[section.bucket] ?? PALETTE.textDim;
  const donePct = c.total === 0 ? 0 : Math.round((c.done / c.total) * 100);
  const title = section.section || "Unsectioned Tasks";

  return (
    <div style={{
      border: `1px solid ${PALETTE.rule}`,
      borderTop: `3px solid ${color}`,
      borderRadius: 6,
      overflow: "hidden",
      background: "#fff",
    }}>
      {/* Section header */}
      <button
        onClick={() => setCollapsed((v) => !v)}
        style={{
          width: "100%",
          border: "none",
          background: "#f8fafc",
          padding: "10px 14px",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: 10,
          textAlign: "left",
        }}
      >
        <span style={{
          fontSize: 12,
          color: PALETTE.textMute,
          fontFamily: "'JetBrains Mono', monospace",
        }}>
          {collapsed ? "▸" : "▾"}
        </span>
        <span style={{
          flex: 1,
          fontSize: 13,
          fontWeight: 700,
          color: PALETTE.text,
          fontFamily: "'Inter', sans-serif",
        }}>
          {title}
        </span>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11,
          color: color,
          fontWeight: 700,
        }}>
          {donePct}%
        </span>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11,
          color: PALETTE.textDim,
        }}>
          {c.done}/{c.total}
        </span>
        {c.in_progress > 0 && (
          <span style={{
            background: `${TASK_STATUS_COLOR.in_progress}22`,
            color: TASK_STATUS_COLOR.in_progress,
            padding: "1px 6px",
            borderRadius: 10,
            fontSize: 10,
            fontFamily: "'JetBrains Mono', monospace",
            fontWeight: 700,
          }}>
            {c.in_progress} WIP
          </span>
        )}
      </button>

      {/* Tasks list */}
      {!collapsed && (
        <div>
          {section.tasks.map((t, idx) => {
            const status = taskStatus(t);
            const statusColor = TASK_STATUS_COLOR[status] ?? PALETTE.textDim;
            const detail = String(t.meta?.description ?? t.meta?.task_detail ?? "");
            const isSelected = t.id === selectedNodeId;
            const isDone = status === "done" || status === "cancelled";
            const skill = suggestSkillForTask(t);

            return (
              <div
                key={t.id}
                onClick={() => onSelectNode(t.id)}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 10,
                  padding: "10px 14px",
                  borderTop: idx === 0 ? `1px solid ${PALETTE.rule}` : `1px solid ${PALETTE.ruleSoft}`,
                  cursor: "pointer",
                  background: isSelected ? "#ccfbf1" : "transparent",
                  transition: "background 0.1s",
                }}
              >
                <div style={{ marginTop: 2, flexShrink: 0 }}>
                  <StatusIcon status={status} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize: 13,
                    fontWeight: isSelected ? 600 : 500,
                    color: isDone ? PALETTE.textDim : PALETTE.text,
                    textDecoration: isDone ? "line-through" : "none",
                    lineHeight: 1.4,
                    fontFamily: "'Inter', sans-serif",
                  }}>
                    {t.label}
                  </div>
                  {mode === "execute" && (
                    <div title={`Suggested skill: ${skill}`} style={{
                      marginTop: 4,
                      display: "inline-flex",
                      alignItems: "center",
                      width: "fit-content",
                      borderRadius: 12,
                      padding: "1px 8px",
                      background: "#eef2ff",
                      color: "#4338ca",
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 10,
                      letterSpacing: "0.04em",
                      fontWeight: 700,
                    }}>
                      {skill}
                    </div>
                  )}
                  {detail && (
                    <div style={{
                      marginTop: 3,
                      fontSize: 12,
                      color: PALETTE.textDim,
                      lineHeight: 1.4,
                      display: "-webkit-box",
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: "vertical",
                      overflow: "hidden",
                    }}>
                      {detail}
                    </div>
                  )}
                </div>
                <div style={{
                  flexShrink: 0,
                  background: `${statusColor}22`,
                  color: statusColor,
                  padding: "2px 7px",
                  borderRadius: 4,
                  fontSize: 10,
                  fontFamily: "'JetBrains Mono', monospace",
                  fontWeight: 800,
                  letterSpacing: "0.06em",
                  marginTop: 2,
                }}>
                  {status.replace("_", " ").toUpperCase()}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Kanban board (compact view)
// ---------------------------------------------------------------------------

function KanbanBoard({ sections, selectedNodeId, onSelectNode, mode }: {
  sections: SectionBucket[];
  selectedNodeId: string | null;
  onSelectNode: (id: string) => void;
  mode: Mode;
}) {
  const groups: Record<SectionBucket["bucket"], SectionBucket[]> = {
    pending: [], in_progress: [], done: [], cancelled: [],
  };
  for (const s of sections) groups[s.bucket].push(s);
  const [showCancelled, setShowCancelled] = useState(false);

  const columns = [
    { key: "pending" as const, label: "PENDING", color: TASK_STATUS_COLOR.pending },
    { key: "in_progress" as const, label: "IN PROGRESS", color: TASK_STATUS_COLOR.in_progress },
    { key: "done" as const, label: "DONE", color: TASK_STATUS_COLOR.done },
  ];

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
        {columns.map(({ key, label, color }) => (
          <div key={key} style={{
            background: PALETTE.panel,
            border: `1px solid ${PALETTE.rule}`,
            borderTop: `3px solid ${color}`,
            borderRadius: 6,
            padding: 10,
            display: "flex",
            flexDirection: "column",
            gap: 8,
            minHeight: 100,
          }}>
            <div style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 11,
              letterSpacing: "0.16em",
              fontWeight: 800,
              color,
              display: "flex",
              justifyContent: "space-between",
            }}>
              <span>{label}</span>
              <span style={{
                background: `${color}22`,
                padding: "0 6px",
                borderRadius: 8,
              }}>
                {groups[key].length}
              </span>
            </div>
            {groups[key].length === 0 ? (
              <div style={{ fontSize: 11, color: PALETTE.textMute, fontFamily: "'JetBrains Mono', monospace" }}>
                ∅ empty
              </div>
            ) : (
              groups[key].map((s) => {
                const hasSelected = s.tasks.some((t) => t.id === selectedNodeId);
                const donePct = s.counts.total === 0 ? 0 : Math.round((s.counts.done / s.counts.total) * 100);
                return (
                  <button
                    key={`${s.section}-${s.order}`}
                    onClick={() => {
                      const first = s.tasks[0];
                      if (first) onSelectNode(first.id);
                    }}
                    style={{
                      border: `1px solid ${hasSelected ? color : PALETTE.rule}`,
                      borderLeft: `3px solid ${color}`,
                      borderRadius: 4,
                      background: hasSelected ? `${color}12` : PALETTE.bg,
                      padding: "8px 10px",
                      cursor: "pointer",
                      textAlign: "left",
                      display: "flex",
                      flexDirection: "column",
                      gap: 4,
                      fontFamily: "'Inter', sans-serif",
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 600, color: PALETTE.text, lineHeight: 1.3 }}>
                      {s.section || "(no section)"}
                    </div>
                    {mode === "execute" && (
                      <div style={{
                        width: "fit-content",
                        borderRadius: 10,
                        background: "#ecfeff",
                        color: "#0e7490",
                        padding: "1px 7px",
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 10,
                        fontWeight: 700,
                      }}>
                        {suggestSkillForTask(s.tasks[0])}
                      </div>
                    )}
                    <div style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 10,
                      color: PALETTE.textDim,
                      display: "flex",
                      gap: 6,
                    }}>
                      <span style={{ color }}>{donePct}%</span>
                      <span>{s.counts.done}/{s.counts.total}</span>
                      {s.counts.in_progress > 0 && (
                        <span style={{ color: TASK_STATUS_COLOR.in_progress }}>{s.counts.in_progress} wip</span>
                      )}
                    </div>
                  </button>
                );
              })
            )}
          </div>
        ))}
      </div>
      {groups.cancelled.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <button
            onClick={() => setShowCancelled((v) => !v)}
            style={{
              border: `1px solid ${PALETTE.rule}`,
              background: "transparent",
              borderRadius: 4,
              padding: "4px 10px",
              cursor: "pointer",
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 11,
              color: PALETTE.textDim,
            }}
          >
            {showCancelled ? "▾" : "▸"} CANCELLED ({groups.cancelled.length})
          </button>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Context Knowledge Panel (right panel)
// ---------------------------------------------------------------------------

function ContextKnowledgePanel({ mode, selectedTask, toBeView, docs, tasks, onClose }: {
  mode: Mode;
  selectedTask: ProjectNode | null;
  toBeView: ToBeView | null;
  docs: BundleDoc[];
  tasks: ProjectNode[];
  onClose: () => void;
}) {
  const planDoc = docs.find((d) => /plan\.md$/i.test(d.label));
  const specDoc = docs.find((d) => /spec\.md$/i.test(d.label));
  const decisions = useMemo(() => extractDecisionBullets(planDoc?.body), [planDoc]);
  const planResources = useMemo(() => extractPlanResources(planDoc?.body), [planDoc]);
  const done = tasks.filter((t) => taskStatus(t) === "done").length;
  const total = tasks.length;
  const donePct = total === 0 ? 0 : Math.round((done / total) * 100);

  // Source-of-truth preference: template markdown tables > toBeView
  const workflows = planResources.workflows.length > 0
    ? planResources.workflows
    : toBeView?.workflows.map((w) => ({ file: w.label, type: w.bucket, deps: w.readiness ?? "" })) ?? [];
  const queues = planResources.queues;
  const assets = planResources.assets;
  const connections = planResources.connections.length > 0
    ? planResources.connections
    : toBeView?.integrations.map((i) => ({ name: i.label, system: i.system, surface: "" })) ?? [];
  const hitl = planResources.hitl.length > 0
    ? planResources.hitl
    : toBeView?.hitl.map((h) => ({ label: h.label, channel: h.channel, detail: h.actor })) ?? [];

  // Spec summary (first paragraph)
  const specSummary = useMemo(() => firstUsefulParagraph(specDoc?.body), [specDoc]);
  const selectedTaskSkill = selectedTask ? suggestSkillForTask(selectedTask) : null;
  const topologySummary = [
    `${workflows.length} workflows`,
    `${queues.length} queues`,
    `${assets.length} assets`,
    `${connections.length} connections`,
    `${hitl.length} HITL points`,
  ].join(" | ");

  return (
    <div style={{
      width: 280,
      flexShrink: 0,
      background: "#fafafa",
      borderLeft: `1px solid ${PALETTE.rule}`,
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
    }}>
      {/* Header */}
      <div style={{
        padding: "10px 14px",
        borderBottom: `1px solid ${PALETTE.rule}`,
        background: PALETTE.panel,
        display: "flex",
        alignItems: "center",
        gap: 8,
      }}>
        <div style={{
          flex: 1,
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11,
          letterSpacing: "0.18em",
          fontWeight: 800,
          color: PALETTE.textDim,
        }}>
          SKILLS & INTEGRATIONS HUB
        </div>
        <button
          onClick={onClose}
          title="Collapse context panel"
          style={{
            border: `1px solid ${PALETTE.rule}`,
            background: "transparent",
            borderRadius: 4,
            padding: "2px 6px",
            cursor: "pointer",
            fontSize: 11,
            color: PALETTE.textDim,
          }}
        >
          ▶
        </button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "12px 14px", display: "flex", flexDirection: "column", gap: 16 }}>

        {(mode === "orient" || mode === "verify") && (
          <ContextSection title="SOLUTION TOPOLOGY" color="#0f766e">
            <div title={topologySummary} style={{
              fontSize: 12,
              color: PALETTE.text,
              lineHeight: 1.45,
              background: "#ecfeff",
              border: "1px solid #a5f3fc",
              borderRadius: 6,
              padding: "8px 10px",
            }}>
              {topologySummary}
            </div>
            <div style={{
              fontSize: 11,
              color: PALETTE.textDim,
              fontFamily: "'JetBrains Mono', monospace",
            }}>
              Orchestrator and integration resources are sourced from `plan.md` first, then TO-BE graph fallback.
            </div>
          </ContextSection>
        )}

        {mode === "execute" && (
          <ContextSection title="EXECUTION GUIDANCE" color="#4338ca">
            <ContextItem
              dot="#4338ca"
              label={selectedTask ? selectedTask.label : "Select a task for prescriptive guidance"}
              meta={selectedTaskSkill ? `suggested skill: ${selectedTaskSkill}` : "suggested skill: n/a"}
            />
            <ContextItem
              dot="#0f766e"
              label="Resource mapping"
              meta={`${queues.length} queues · ${assets.length} assets · ${connections.length} connections`}
            />
          </ContextSection>
        )}

        {/* Spec summary */}
        {specSummary && (
          <div style={{
            background: "#f0f9ff",
            border: "1px solid #bae6fd",
            borderRadius: 6,
            padding: "8px 10px",
            fontSize: 12,
            color: "#0c4a6e",
            lineHeight: 1.5,
          }}>
            {specSummary.length > 200 ? specSummary.slice(0, 200) + "…" : specSummary}
          </div>
        )}

        {/* Task progress */}
        {total > 0 && (
          <ContextSection title="TASK PROGRESS" color="#7c3aed">
            <div style={{ display: "flex", gap: 8, marginBottom: 6 }}>
              {[
                { label: "done", count: done, color: "#059669" },
                { label: "open", count: total - done, color: "#6b7280" },
              ].map((s) => (
                <div key={s.label} style={{
                  flex: 1, textAlign: "center",
                  background: `${s.color}12`,
                  border: `1px solid ${s.color}33`,
                  borderRadius: 6,
                  padding: "6px 0",
                }}>
                  <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 16, fontWeight: 800, color: s.color }}>
                    {s.count}
                  </div>
                  <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: PALETTE.textDim, letterSpacing: "0.1em" }}>
                    {s.label.toUpperCase()}
                  </div>
                </div>
              ))}
            </div>
            <ProgressBar pct={donePct} color={donePct === 100 ? "#059669" : "#7c3aed"} />
          </ContextSection>
        )}

        {/* Workflow catalog (from plan.md ## Workflow Catalog table) */}
        {workflows.length > 0 && (
          <ContextSection title="WORKFLOW CATALOG" color="#2563eb">
            {workflows.map((w, i) => (
              <ContextItem
                key={i}
                dot="#2563eb"
                label={w.file}
                meta={[w.type, w.deps].filter(Boolean).join(" · ")}
              />
            ))}
          </ContextSection>
        )}

        {/* Queues (from plan.md ## Queues table) */}
        {queues.length > 0 && (
          <ContextSection title="QUEUES" color="#475569">
            {queues.map((q, i) => (
              <ContextItem
                key={i}
                dot="#475569"
                label={q.name}
                meta={[q.folder, q.notes].filter(Boolean).join(" · ")}
              />
            ))}
          </ContextSection>
        )}

        {/* Assets (from plan.md ## Assets table) */}
        {assets.length > 0 && (
          <ContextSection title="ASSETS" color="#7c3aed">
            {assets.map((a, i) => (
              <ContextItem
                key={i}
                dot="#7c3aed"
                label={a.name}
                meta={[a.type, a.notes].filter(Boolean).join(" · ")}
              />
            ))}
          </ContextSection>
        )}

        {/* Connections / integrations (from plan.md ## Connections table) */}
        {connections.length > 0 && (
          <ContextSection title="CONNECTIONS" color="#0891b2">
            {connections.map((c, i) => (
              <ContextItem
                key={i}
                dot="#0891b2"
                label={c.name}
                meta={[c.system, c.surface].filter(Boolean).join(" · ")}
              />
            ))}
          </ContextSection>
        )}

        {/* HITL gates */}
        {hitl.length > 0 && (
          <ContextSection title="HUMAN-IN-THE-LOOP" color="#dc2626">
            {hitl.map((h, i) => (
              <ContextItem
                key={i}
                dot="#dc2626"
                label={h.label}
                meta={[h.channel, h.detail].filter(Boolean).join(" · ")}
              />
            ))}
          </ContextSection>
        )}

        {/* Decisions */}
        {decisions.length > 0 && (
          <ContextSection title="DESIGN DECISIONS" color="#d97706">
            {decisions.slice(0, 6).map((d, i) => (
              <ContextItem key={i} dot="#d97706" label={d} />
            ))}
            {decisions.length > 6 && (
              <div style={{ fontSize: 11, color: PALETTE.textMute, fontFamily: "'JetBrains Mono', monospace" }}>
                +{decisions.length - 6} more…
              </div>
            )}
          </ContextSection>
        )}

        {/* Plan file links */}
        <ContextSection title="PLAN FILES" color="#0f766e">
          {docs.map((doc) => {
            const diagrams = extractMermaidBlocks(doc.body).length;
            return (
              <div key={doc.id} style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "5px 0",
                borderBottom: `1px solid ${PALETTE.ruleSoft}`,
              }}>
                <span style={{ fontSize: 11 }}>{docIcon(doc.label)}</span>
                <span
                  title={doc.label}
                  style={{
                    flex: 1,
                    minWidth: 0,
                    fontSize: 12,
                    color: PALETTE.text,
                    fontWeight: 500,
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {doc.label}
                </span>
                {diagrams > 0 && (
                  <span style={{
                    fontSize: 10,
                    fontFamily: "'JetBrains Mono', monospace",
                    color: "#0f766e",
                    background: "#ccfbf1",
                    padding: "1px 5px",
                    borderRadius: 3,
                    fontWeight: 700,
                  }}>
                    {diagrams}⊞
                  </span>
                )}
              </div>
            );
          })}
        </ContextSection>
      </div>
    </div>
  );
}

function ContextSection({ title, color, children }: {
  title: string;
  color: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 10,
        letterSpacing: "0.16em",
        fontWeight: 800,
        color,
        marginBottom: 6,
        paddingBottom: 4,
        borderBottom: `1px solid ${color}33`,
      }}>
        {title}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {children}
      </div>
    </div>
  );
}

function ContextItem({ dot, label, meta }: { dot: string; label: string; meta?: string }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 6 }}>
      <span style={{
        width: 6,
        height: 6,
        borderRadius: "50%",
        background: dot,
        flexShrink: 0,
        marginTop: 5,
      }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div title={label} style={{
          fontSize: 12,
          color: PALETTE.text,
          lineHeight: 1.35,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}>
          {label}
        </div>
        {meta && (
          <div title={meta} style={{
            fontSize: 10,
            fontFamily: "'JetBrains Mono', monospace",
            color: PALETTE.textDim,
            marginTop: 1,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}>
            {meta}
          </div>
        )}
      </div>
    </div>
  );
}

function ProgressBar({ pct, color }: { pct: number; color: string }) {
  return (
    <div style={{ height: 5, background: PALETTE.rule, borderRadius: 3, overflow: "hidden" }}>
      <div style={{
        height: "100%",
        width: `${pct}%`,
        background: color,
        borderRadius: 3,
        transition: "width 0.3s",
      }} />
    </div>
  );
}
