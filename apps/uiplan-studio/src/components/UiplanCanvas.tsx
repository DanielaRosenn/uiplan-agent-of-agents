import React, { useMemo, useState } from "react";
import { CheckSquare, Circle, MinusSquare, Square, GitBranch, ListChecks, LayoutGrid } from "lucide-react";

import { PALETTE } from "../theme";
import type { ProjectNode } from "../projectGraph/types";

const TASK_STATUS_COLOR: Record<string, string> = {
  done: "#059669",
  in_progress: "#d97706",
  pending: "#6b7280",
  cancelled: "#9ca3af",
};

type View = "phase" | "task" | "kanban";

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
  const [view, setView] = useState<View>("task");
  const [selectedPhaseIdx, setSelectedPhaseIdx] = useState<number | null>(null);

  const tasks = useMemo(() => collectTasks(bundle), [bundle]);
  const phases = useMemo(() => extractPhases(bundle), [bundle]);

  const filteredTasks = useMemo(() => {
    if (view !== "task" || selectedPhaseIdx === null) return tasks;
    const phase = phases[selectedPhaseIdx];
    if (!phase) return tasks;
    return tasks.filter((t) => taskMatchesPhase(t, phase));
  }, [tasks, view, selectedPhaseIdx, phases]);

  return (
    <div style={{
      position: "absolute", inset: 0,
      display: "flex", flexDirection: "column",
      background: PALETTE.bg, overflow: "hidden",
    }}>
      <div style={{
        height: 44, flexShrink: 0,
        borderBottom: `1px solid ${PALETTE.rule}`,
        background: PALETTE.panel,
        display: "flex", alignItems: "center", padding: "0 16px", gap: 12,
      }}>
        <div style={{
          fontSize: 10, letterSpacing: "0.22em", fontWeight: 700,
          color: PALETTE.textDim, fontFamily: "'JetBrains Mono', monospace",
        }}>
          UIPLAN&nbsp;·&nbsp;{bundle.label.toUpperCase()}
        </div>
        <div style={{ flex: 1 }} />
        <div style={{ position: "relative", zIndex: 50 }}>
        <Segmented
          value={view}
          onChange={(v) => { setView(v); if (v !== "task") setSelectedPhaseIdx(null); }}
          options={[
            { value: "phase", label: "PHASE FLOW", Icon: GitBranch },
            { value: "task", label: "TASK FLOW", Icon: ListChecks },
            { value: "kanban", label: "KANBAN", Icon: LayoutGrid },
          ]}
        />
        </div>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: 24 }}>
        {view === "phase" && (
          <PhaseFlow
            phases={phases}
            tasks={tasks}
            selectedPhaseIdx={selectedPhaseIdx}
            onSelectPhase={(idx) => {
              setSelectedPhaseIdx(idx);
              setView("task");
            }}
          />
        )}
        {view === "task" && (
          <TaskFlow
            tasks={filteredTasks}
            allCount={tasks.length}
            phase={selectedPhaseIdx !== null ? phases[selectedPhaseIdx] : null}
            onClearPhase={() => setSelectedPhaseIdx(null)}
            selectedNodeId={selectedNodeId}
            onSelectNode={onSelectNode}
          />
        )}
        {view === "kanban" && (
          <Kanban tasks={tasks} selectedNodeId={selectedNodeId} onSelectNode={onSelectNode} />
        )}
      </div>
    </div>
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

function Segmented<V extends string>({ value, onChange, options }: {
  value: V; onChange: (v: V) => void; options: SegOpt<V>[];
}) {
  return (
    <div style={{
      display: "flex",
      border: `1px solid ${PALETTE.rule}`,
      borderRadius: 4, overflow: "hidden",
      background: PALETTE.bg,
    }}>
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "6px 12px", border: "none",
              borderRight: `1px solid ${PALETTE.rule}`,
              background: active ? PALETTE.panel : "transparent",
              cursor: "pointer",
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10, letterSpacing: "0.16em", fontWeight: 700,
              color: active ? PALETTE.text : PALETTE.textDim,
            }}
          >
            <opt.Icon size={11} />
            {opt.label}
          </button>
        );
      })}
    </div>
  );
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

// ---------------------------------------------------------------------------
// Phase Flow
// ---------------------------------------------------------------------------

function PhaseFlow({ phases, tasks, selectedPhaseIdx, onSelectPhase }: {
  phases: Phase[];
  tasks: ProjectNode[];
  selectedPhaseIdx: number | null;
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
          fontSize: 11, letterSpacing: "0.2em", color: PALETTE.text,
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
                width: 220, padding: "14px 16px",
                background: active ? "#ccfbf1" : PALETTE.panel,
                border: `1px solid ${active ? "#0f766e" : PALETTE.rule}`,
                borderLeft: `4px solid ${active ? "#0f766e" : "#0f766e88"}`,
                borderRadius: 6, cursor: "pointer", textAlign: "left",
                display: "flex", flexDirection: "column", gap: 8,
                fontFamily: "'Inter', sans-serif",
              }}
            >
              <div style={{
                fontSize: 9, letterSpacing: "0.22em", fontWeight: 700,
                color: "#0f766e", fontFamily: "'JetBrains Mono', monospace",
              }}>
                PHASE {String(i + 1).padStart(2, "0")}
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: PALETTE.text, lineHeight: 1.35 }}>
                {p.title}
              </div>
              <div style={{
                marginTop: "auto", fontSize: 10,
                fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.1em",
                color: PALETTE.textDim,
              }}>
                {count} TASK{count === 1 ? "" : "S"}
              </div>
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

// ---------------------------------------------------------------------------
// Task Flow
// ---------------------------------------------------------------------------

function TaskFlow({ tasks, allCount, phase, onClearPhase, selectedNodeId, onSelectNode }: {
  tasks: ProjectNode[];
  allCount: number;
  phase: Phase | null;
  onClearPhase: () => void;
  selectedNodeId: string | null;
  onSelectNode: (id: string) => void;
}) {
  return (
    <div>
      {phase && (
        <div style={{
          marginBottom: 16, padding: "8px 12px",
          background: "#ccfbf1", border: "1px solid #99f6e4",
          borderLeft: "3px solid #0f766e", borderRadius: 4,
          display: "flex", alignItems: "center", gap: 10,
          fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
        }}>
          <span style={{ color: "#0f766e", fontWeight: 700, letterSpacing: "0.14em" }}>
            FILTER · {phase.title.toUpperCase()}
          </span>
          <span style={{ color: PALETTE.textDim }}>
            {tasks.length}/{allCount} tasks
          </span>
          <button onClick={onClearPhase} style={{
            marginLeft: "auto", background: "transparent", border: "none",
            cursor: "pointer", color: "#0f766e", fontWeight: 700,
            fontSize: 10, letterSpacing: "0.14em",
          }}>CLEAR ×</button>
        </div>
      )}
      {tasks.length === 0 ? (
        <div style={{ color: PALETTE.textMute, fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>
          ∅ no tasks
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {tasks.map((t, i) => (
            <React.Fragment key={t.id}>
              <TaskFlowCard
                task={t}
                selected={t.id === selectedNodeId}
                onClick={() => onSelectNode(t.id)}
              />
              {i < tasks.length - 1 && (
                <div style={{
                  alignSelf: "center", color: PALETTE.textMute,
                  fontSize: 12, lineHeight: 1,
                }}>↓</div>
              )}
            </React.Fragment>
          ))}
        </div>
      )}
    </div>
  );
}

function TaskFlowCard({ task, selected, onClick }: {
  task: ProjectNode; selected: boolean; onClick: () => void;
}) {
  const status = taskStatus(task);
  const color = TASK_STATUS_COLOR[status] ?? PALETTE.textDim;
  const struck = status === "done" || status === "cancelled";
  const path = String(task.meta?.full_path ?? task.meta?.parent_bundle ?? "");
  const line = String(task.meta?.task_line ?? "");
  const truncated = task.label.length > 60 ? task.label.slice(0, 59) + "…" : task.label;
  return (
    <button
      onClick={onClick}
      title={`${path}${line ? ":" + line : ""}`}
      style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: "10px 14px", maxWidth: 720, width: "100%",
        background: selected ? "#ccfbf1" : PALETTE.panel,
        borderTop: `1px solid ${selected ? "#0f766e" : PALETTE.rule}`,
        borderRight: `1px solid ${selected ? "#0f766e" : PALETTE.rule}`,
        borderBottom: `1px solid ${selected ? "#0f766e" : PALETTE.rule}`,
        borderLeft: `4px solid ${color}`,
        borderRadius: 5, cursor: "pointer", textAlign: "left",
        fontFamily: "'Inter', sans-serif",
      }}
    >
      <StatusIcon status={status} />
      <span style={{
        fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
        letterSpacing: "0.14em", fontWeight: 700, color,
        padding: "2px 6px", border: `1px solid ${color}33`, borderRadius: 3,
        background: `${color}11`,
      }}>
        {status.replace("_", " ").toUpperCase()}
      </span>
      <span style={{
        flex: 1, fontSize: 13, color: PALETTE.text,
        textDecoration: struck ? "line-through" : "none",
        opacity: struck ? 0.65 : 1,
      }}>
        {truncated}
      </span>
      {line && (
        <span style={{
          fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
          color: PALETTE.textMute, letterSpacing: "0.08em",
        }}>
          L{line}
        </span>
      )}
    </button>
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

function Kanban({ tasks, selectedNodeId, onSelectNode }: {
  tasks: ProjectNode[]; selectedNodeId: string | null; onSelectNode: (id: string) => void;
}) {
  const sections = useMemo(() => bucketSectionsByStatus(tasks), [tasks]);
  const groups: Record<SectionBucket["bucket"], SectionBucket[]> = {
    pending: [], in_progress: [], done: [], cancelled: [],
  };
  for (const s of sections) groups[s.bucket].push(s);

  const [showCancelled, setShowCancelled] = useState(false);
  return (
    <div>
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(3, minmax(240px, 1fr))",
        gap: 16,
      }}>
        <SectionKanbanColumn title="PENDING" status="pending" sections={groups.pending}
          selectedNodeId={selectedNodeId} onSelectNode={onSelectNode} />
        <SectionKanbanColumn title="IN PROGRESS" status="in_progress" sections={groups.in_progress}
          selectedNodeId={selectedNodeId} onSelectNode={onSelectNode} />
        <SectionKanbanColumn title="DONE" status="done" sections={groups.done}
          selectedNodeId={selectedNodeId} onSelectNode={onSelectNode} />
      </div>
      {groups.cancelled.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <button
            onClick={() => setShowCancelled((v) => !v)}
            style={{
              background: PALETTE.panel, border: `1px solid ${PALETTE.rule}`,
              borderRadius: 4, padding: "6px 12px", cursor: "pointer",
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10, letterSpacing: "0.16em", fontWeight: 700,
              color: PALETTE.textDim,
            }}
          >
            {showCancelled ? "▾" : "▸"} CANCELLED ({groups.cancelled.length})
          </button>
          {showCancelled && (
            <div style={{ marginTop: 12, maxWidth: 360 }}>
              <SectionKanbanColumn title="CANCELLED" status="cancelled" sections={groups.cancelled}
                selectedNodeId={selectedNodeId} onSelectNode={onSelectNode} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SectionKanbanColumn({ title, status, sections, selectedNodeId, onSelectNode }: {
  title: string; status: string; sections: SectionBucket[];
  selectedNodeId: string | null; onSelectNode: (id: string) => void;
}) {
  const color = TASK_STATUS_COLOR[status] ?? PALETTE.textDim;
  const totalTasks = sections.reduce((acc, s) => acc + s.counts.total, 0);
  return (
    <div style={{
      background: PALETTE.panel,
      borderTop: `3px solid ${color}`,
      borderRight: `1px solid ${PALETTE.rule}`,
      borderBottom: `1px solid ${PALETTE.rule}`,
      borderLeft: `1px solid ${PALETTE.rule}`,
      borderRadius: 6, padding: 12,
      display: "flex", flexDirection: "column", gap: 10,
      minHeight: 120,
    }}>
      <div style={{
        display: "flex", alignItems: "center", gap: 8,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 10, letterSpacing: "0.18em", fontWeight: 700, color,
      }}>
        <span style={{ flex: 1 }}>{title}</span>
        <span style={{
          padding: "1px 7px", borderRadius: 10,
          background: `${color}22`, color, fontSize: 10,
        }}>
          {sections.length}{totalTasks > 0 ? `·${totalTasks}t` : ""}
        </span>
      </div>
      {sections.length === 0 ? (
        <div style={{ fontSize: 11, color: PALETTE.textMute, fontFamily: "'JetBrains Mono', monospace" }}>
          ∅ empty
        </div>
      ) : (
        sections.map((s) => (
          <SectionKanbanCard
            key={`${s.section || "unsectioned"}-${s.order}`}
            section={s}
            selectedNodeId={selectedNodeId}
            onSelectNode={onSelectNode}
          />
        ))
      )}
    </div>
  );
}

function SectionKanbanCard({ section, selectedNodeId, onSelectNode }: {
  section: SectionBucket; selectedNodeId: string | null; onSelectNode: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const c = section.counts;
  const color = TASK_STATUS_COLOR[section.bucket] ?? PALETTE.textDim;
  const donePct = c.total === 0 ? 0 : Math.round((c.done / c.total) * 100);
  const title = section.section || "(no section)";
  const hasSelection = section.tasks.some((t) => t.id === selectedNodeId);
  return (
    <div style={{
      background: hasSelection ? "#ccfbf1" : PALETTE.bg,
      borderTop: `1px solid ${hasSelection ? "#0f766e" : PALETTE.rule}`,
      borderRight: `1px solid ${hasSelection ? "#0f766e" : PALETTE.rule}`,
      borderBottom: `1px solid ${hasSelection ? "#0f766e" : PALETTE.rule}`,
      borderLeft: `3px solid ${color}`,
      borderRadius: 4,
      fontFamily: "'Inter', sans-serif",
      overflow: "hidden",
    }}>
      <button
        onClick={() => setExpanded((v) => !v)}
        style={{
          width: "100%", textAlign: "left",
          background: "transparent", border: "none",
          padding: "10px 12px", cursor: "pointer",
          display: "flex", flexDirection: "column", gap: 6,
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
          <span style={{
            fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
            color: PALETTE.textMute,
          }}>
            {expanded ? "▾" : "▸"}
          </span>
          <span style={{ flex: 1, fontSize: 12.5, fontWeight: 600, color: PALETTE.text, lineHeight: 1.3 }}>
            {title}
          </span>
        </div>
        <div style={{
          fontSize: 10, fontFamily: "'JetBrains Mono', monospace",
          color: PALETTE.textDim, letterSpacing: "0.06em",
          display: "flex", gap: 10, flexWrap: "wrap",
        }}>
          <span><span style={{ color: TASK_STATUS_COLOR.done, fontWeight: 700 }}>{c.done}</span>/{c.total} · {donePct}%</span>
          {c.in_progress > 0 && <span style={{ color: TASK_STATUS_COLOR.in_progress }}>{c.in_progress} wip</span>}
          {c.pending > 0 && <span>{c.pending} pending</span>}
          {c.cancelled > 0 && <span style={{ color: TASK_STATUS_COLOR.cancelled }}>{c.cancelled} cancelled</span>}
        </div>
      </button>
      {expanded && (
        <div style={{
          borderTop: `1px solid ${PALETTE.rule}`,
          padding: 8,
          display: "flex", flexDirection: "column", gap: 6,
          maxHeight: 240, overflowY: "auto",
          background: PALETTE.panel,
        }}>
          {section.tasks.map((t) => (
            <button
              key={t.id}
              onClick={(e) => { e.stopPropagation(); onSelectNode(t.id); }}
              title={t.label}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "5px 8px", textAlign: "left",
                background: t.id === selectedNodeId ? "#ccfbf1" : "transparent",
                border: "none", borderRadius: 3,
                cursor: "pointer",
                fontFamily: "'Inter', sans-serif",
              }}
            >
              <StatusIcon status={taskStatus(t)} />
              <span style={{
                fontSize: 11.5, color: PALETTE.text, lineHeight: 1.3,
                textDecoration: (taskStatus(t) === "done" || taskStatus(t) === "cancelled") ? "line-through" : "none",
                opacity: (taskStatus(t) === "done" || taskStatus(t) === "cancelled") ? 0.65 : 1,
                overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
              }}>
                {t.label}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

