import React from "react";
import { CheckSquare, Circle, FileCode, MinusSquare, Square } from "lucide-react";

import { PALETTE } from "../theme";
import type { ProjectGraph, ProjectNode, TaskSummary } from "../projectGraph/types";
import { Section } from "./primitives";

const TASK_STATUS_COLOR: Record<string, string> = {
  done: "#059669",
  in_progress: "#d97706",
  pending: "#6b7280",
  cancelled: "#9ca3af",
};

function ProgressBar({ summary }: { summary: TaskSummary }) {
  if (summary.total === 0) {
    return (
      <div style={{ fontSize: 12, color: PALETTE.textMute, fontFamily: "'JetBrains Mono', monospace" }}>
        no tasks parsed
      </div>
    );
  }
  const donePct = (summary.done / summary.total) * 100;
  const progPct = (summary.in_progress / summary.total) * 100;
  const cancelPct = (summary.cancelled / summary.total) * 100;
  return (
    <div>
      <div style={{
        display: "flex", alignItems: "baseline", gap: 8,
        fontFamily: "'JetBrains Mono', monospace",
      }}>
        <span style={{ fontSize: 18, fontWeight: 700, color: PALETTE.text }}>
          {summary.done}
        </span>
        <span style={{ fontSize: 12, color: PALETTE.textDim }}>
          of {summary.total} complete
        </span>
        <span style={{
          marginLeft: "auto", fontSize: 12, fontWeight: 700,
          color: summary.done === summary.total ? "#059669" : "#d97706",
        }}>
          {Math.round(donePct)}%
        </span>
      </div>
      <div style={{
        marginTop: 8, height: 6, borderRadius: 3,
        background: PALETTE.bg, border: `1px solid ${PALETTE.rule}`,
        display: "flex", overflow: "hidden",
      }}>
        <div style={{ width: `${donePct}%`, background: "#059669" }} />
        <div style={{ width: `${progPct}%`, background: "#d97706" }} />
        <div style={{ width: `${cancelPct}%`, background: "#9ca3af" }} />
      </div>
      <div style={{
        marginTop: 8, display: "flex", gap: 12, flexWrap: "wrap",
        fontSize: 12, fontFamily: "'JetBrains Mono', monospace",
        color: PALETTE.textDim, letterSpacing: "0.08em",
      }}>
        <Stat label="DONE" value={summary.done} color="#059669" />
        {summary.in_progress > 0 && <Stat label="WIP" value={summary.in_progress} color="#d97706" />}
        <Stat label="PENDING" value={summary.pending} color="#6b7280" />
        {summary.cancelled > 0 && <Stat label="CANCELLED" value={summary.cancelled} color="#9ca3af" />}
      </div>
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <span>
      <span style={{ color, fontWeight: 700 }}>{value}</span>
      <span style={{ marginLeft: 4 }}>{label}</span>
    </span>
  );
}

function TaskRow({ node }: { node: ProjectNode }) {
  const status = String(node.meta?.task_status ?? "pending");
  const color = TASK_STATUS_COLOR[status] ?? PALETTE.textDim;
  const Icon = status === "done" ? CheckSquare
    : status === "cancelled" ? MinusSquare
    : status === "in_progress" ? Circle
    : Square;
  const struck = status === "done" || status === "cancelled";
  return (
    <div style={{
      display: "flex", alignItems: "flex-start", gap: 10,
      padding: "8px 10px",
      background: PALETTE.bg, border: `1px solid ${PALETTE.rule}`,
      borderLeft: `3px solid ${color}`, borderRadius: 4,
    }}>
      <Icon size={14} color={color} strokeWidth={2} style={{ flexShrink: 0, marginTop: 1 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: 12.5, lineHeight: 1.45, color: PALETTE.text,
          textDecoration: struck ? "line-through" : "none",
          opacity: struck ? 0.65 : 1,
        }}>
          {node.label}
        </div>
        {node.desc && node.desc !== "task" && (
          <div style={{
            marginTop: 2, fontSize: 12, color: PALETTE.textMute,
            fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.08em",
          }}>
            {node.desc.toUpperCase()}
          </div>
        )}
      </div>
      <span style={{
        fontSize: 12, fontFamily: "'JetBrains Mono', monospace",
        letterSpacing: "0.12em", fontWeight: 700, color,
      }}>
        {status.toUpperCase().replace("_", " ")}
      </span>
    </div>
  );
}

export function UiplanProgressPanel({
  node, rootGraph, onJumpToFile,
}: {
  node: ProjectNode;
  rootGraph?: ProjectGraph;
  onJumpToFile?: (path: string) => void;
}) {
  const summary = node.task_summary;
  const children = node.children?.nodes ?? [];
  // Bundle nodes have file children; tasks-file nodes have task children.
  const taskNodes = children.filter((c) => c.kind === "uiplan_task");
  const isBundle = node.kind === "uiplan_bundle";

  // Bundle aggregate: phase count + files-touched count.
  const allTasks = isBundle ? collectBundleTasks(node) : [];
  const phaseCount = isBundle ? countPhases(node) : 0;
  const filesTouched = isBundle ? collectFilesTouched(node, allTasks) : [];

  return (
    <div style={{ padding: 18, fontFamily: "'Inter', sans-serif" }}>
      {summary && (
        <>
          <Section label="PROGRESS" />
          <div style={{ marginTop: 10 }}>
            <ProgressBar summary={summary} />
          </div>
        </>
      )}
      {isBundle && (
        <div style={{ marginTop: 18 }}>
          <Section label="BUNDLE" />
          <div style={{
            marginTop: 10, fontSize: 12, lineHeight: 1.85,
            fontFamily: "'JetBrains Mono', monospace",
          }}>
            <KvRow k="phases" v={String(phaseCount).padStart(2, "0")} />
            <KvRow k="files touched" v={String(filesTouched.length).padStart(2, "0")} />
            <KvRow k="tasks" v={String(allTasks.length).padStart(2, "0")} />
          </div>
        </div>
      )}
      {node.desc && (
        <div style={{ marginTop: 22 }}>
          <Section label="ABOUT" />
          <div style={{ marginTop: 10, fontSize: 13, lineHeight: 1.55, color: PALETTE.text }}>
            {node.desc}
          </div>
        </div>
      )}
      {taskNodes.length > 0 && (
        <div style={{ marginTop: 22 }}>
          <Section label="TASKS" count={taskNodes.length} />
          <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 4 }}>
            {taskNodes.map((t) => <TaskRow key={t.id} node={t} />)}
          </div>
        </div>
      )}
      {isBundle && filesTouched.length > 0 && (
        <div style={{ marginTop: 22 }}>
          <Section label="FILES TOUCHED" count={filesTouched.length} />
          <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 4 }}>
            {filesTouched.map((p) => (
              <FileJumpRow key={p} path={p} rootGraph={rootGraph} onJumpToFile={onJumpToFile} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function KvRow({ k, v }: { k: string; v: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between" }}>
      <span style={{ color: PALETTE.textDim }}>{k}</span>
      <span style={{ color: PALETTE.text, fontWeight: 600 }}>{v}</span>
    </div>
  );
}

/** Per-task drill-down panel: status + body + Implements (file jumps). */
export function UiplanTaskPanel({
  node, rootGraph, onJumpToFile,
}: {
  node: ProjectNode;
  rootGraph?: ProjectGraph;
  onJumpToFile?: (path: string) => void;
}) {
  const status = String(node.meta?.task_status ?? "pending");
  const color = TASK_STATUS_COLOR[status] ?? PALETTE.textDim;
  const path = String(node.meta?.full_path ?? node.meta?.parent_bundle ?? "");
  const line = String(node.meta?.task_line ?? "");
  const section = String(node.meta?.task_section ?? "");
  const body = String(node.meta?.body ?? "");
  const refs = extractImplements(node, body);

  return (
    <div style={{ padding: 18, fontFamily: "'Inter', sans-serif" }}>
      <Section label="TASK" />
      <div style={{
        marginTop: 10, padding: "10px 12px",
        background: PALETTE.bg, border: `1px solid ${PALETTE.rule}`,
        borderLeft: `3px solid ${color}`, borderRadius: 4,
      }}>
        <div style={{
          display: "flex", alignItems: "center", gap: 8,
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 12, letterSpacing: "0.14em", fontWeight: 700, color,
        }}>
          {status.replace("_", " ").toUpperCase()}
          {section && (
            <span style={{ color: PALETTE.textDim, fontWeight: 500 }}>
              · {section.toUpperCase()}
            </span>
          )}
        </div>
        <div style={{
          marginTop: 8, fontSize: 13.5, lineHeight: 1.45,
          color: PALETTE.text,
          textDecoration: status === "done" || status === "cancelled" ? "line-through" : "none",
          opacity: status === "done" || status === "cancelled" ? 0.7 : 1,
        }}>
          {node.label}
        </div>
        {(path || line) && (
          <div style={{
            marginTop: 6, fontSize: 12,
            fontFamily: "'JetBrains Mono', monospace",
            color: PALETTE.textMute, letterSpacing: "0.08em",
          }}>
            {path}{line ? `:${line}` : ""}
          </div>
        )}
      </div>

      {body && (
        <div style={{ marginTop: 22 }}>
          <Section label="DETAILS" />
          <div style={{ marginTop: 10 }}>
            <MarkdownView source={body} />
          </div>
        </div>
      )}

      {refs.files.length > 0 && (
        <div style={{ marginTop: 22 }}>
          <Section label="IMPLEMENTS" count={refs.files.length} />
          <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 4 }}>
            {refs.files.map((p) => (
              <FileJumpRow key={p} path={p} rootGraph={rootGraph} onJumpToFile={onJumpToFile} />
            ))}
          </div>
        </div>
      )}

      {refs.symbols.length > 0 && (
        <div style={{ marginTop: 22 }}>
          <Section label="SYMBOLS" count={refs.symbols.length} />
          <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 6 }}>
            {refs.symbols.map((s) => (
              <span key={s} style={{
                fontSize: 12, fontFamily: "'JetBrains Mono', monospace",
                color: PALETTE.text, background: PALETTE.bg,
                border: `1px solid ${PALETTE.rule}`,
                padding: "3px 8px", borderRadius: 3,
              }}>
                {s}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function FileJumpRow({ path, rootGraph, onJumpToFile }: {
  path: string;
  rootGraph?: ProjectGraph;
  onJumpToFile?: (path: string) => void;
}) {
  const exists = !!findFileNodeId(rootGraph, path);
  return (
    <button
      onClick={() => onJumpToFile?.(path)}
      disabled={!onJumpToFile}
      title={exists ? "Jump to file node" : "No matching node in graph"}
      style={{
        display: "flex", alignItems: "center", gap: 8,
        padding: "8px 10px", textAlign: "left",
        background: PALETTE.bg, border: `1px solid ${PALETTE.rule}`,
        borderLeft: `3px solid ${exists ? "#2563eb" : PALETTE.rule}`,
        borderRadius: 4,
        cursor: onJumpToFile ? "pointer" : "default",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 12, color: exists ? PALETTE.text : PALETTE.textDim,
        opacity: exists ? 1 : 0.7,
      }}
    >
      <FileCode size={12} color={exists ? "#2563eb" : PALETTE.textMute} strokeWidth={2} />
      <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {path}
      </span>
      {exists && (
        <span style={{
          fontSize: 12, color: "#2563eb", fontWeight: 700, letterSpacing: "0.14em",
        }}>JUMP →</span>
      )}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const FILE_REF_RE = /`([^`\n]+?\.(?:tsx?|jsx?|py|cs|xaml|md|yaml|yml|json|css|html|svg|sh|ps1|go|rs|java|rb))(?::\d+(?:-\d+)?)?`/g;
const SYMBOL_RE = /`([A-Za-z_][\w$]*(?:\.[A-Za-z_][\w$]*)*\(\)|[A-Z][\w$]+|[a-z_][\w$]+_[\w$]+)`/g;

interface Refs {
  files: string[];
  symbols: string[];
}

function extractImplements(_node: ProjectNode, body: string): Refs {
  const files = new Set<string>();
  const symbols = new Set<string>();
  if (!body) return { files: [], symbols: [] };

  let m: RegExpExecArray | null;
  FILE_REF_RE.lastIndex = 0;
  while ((m = FILE_REF_RE.exec(body)) !== null) {
    files.add(m[1]);
  }

  // Strip file refs from the body so we don't double-count them as symbols.
  const withoutFiles = body.replace(FILE_REF_RE, "");
  SYMBOL_RE.lastIndex = 0;
  while ((m = SYMBOL_RE.exec(withoutFiles)) !== null) {
    const sym = m[1];
    // Skip very short tokens or pure markdown noise.
    if (sym.length < 3) continue;
    symbols.add(sym);
  }

  return {
    files: Array.from(files),
    symbols: Array.from(symbols).slice(0, 20),
  };
}

function collectBundleTasks(bundle: ProjectNode): ProjectNode[] {
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

function countPhases(bundle: ProjectNode): number {
  for (const child of bundle.children?.nodes ?? []) {
    if (child.kind === "uiplan_doc" && /plan\.md$/i.test(child.label)) {
      const body = String(child.meta?.body ?? "");
      const lines = body.split(/\r?\n/);
      let phaseHeads = 0;
      let h2Heads = 0;
      for (const raw of lines) {
        const m = /^##\s+(.+?)\s*$/.exec(raw);
        if (!m) continue;
        h2Heads++;
        if (/^(?:phase|step|stage)\s+(\d+|[A-Z])\b/i.test(m[1].trim())) phaseHeads++;
      }
      return phaseHeads > 0 ? phaseHeads : h2Heads;
    }
  }
  return 0;
}

const BUNDLE_DOC_NAMES = new Set(["spec.md", "plan.md", "tasks.md"]);

function isImplementationFile(path: string): boolean {
  const norm = path.replace(/\\/g, "/");
  if (/\/skills\//i.test(norm)) return false;
  if (/SKILL\.md$/i.test(norm)) return false;
  if (/\.meta\.ya?ml$/i.test(norm)) return false;
  if (/\.md$/i.test(norm)) {
    const base = norm.split("/").pop()?.toLowerCase() ?? "";
    if (!BUNDLE_DOC_NAMES.has(base)) return false;
  }
  return true;
}

function collectFilesTouched(bundle: ProjectNode, tasks: ProjectNode[]): string[] {
  const set = new Set<string>();
  for (const t of tasks) {
    const body = String(t.meta?.body ?? "");
    const refs = extractImplements(t, body);
    refs.files.forEach((f) => set.add(f));
  }
  // Also scan task labels (some checklists embed paths inline).
  for (const t of tasks) {
    FILE_REF_RE.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = FILE_REF_RE.exec(t.label)) !== null) set.add(m[1]);
  }
  // Scan plan.md / spec.md doc bodies as a fallback.
  for (const child of bundle.children?.nodes ?? []) {
    if (child.kind !== "uiplan_doc") continue;
    const body = String(child.meta?.body ?? "");
    FILE_REF_RE.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = FILE_REF_RE.exec(body)) !== null) set.add(m[1]);
  }
  return Array.from(set).filter(isImplementationFile).sort();
}

/** Return the id of a graph node whose code.path or id ends with `path`. */
export function findFileNodeId(graph: ProjectGraph | undefined, path: string): string | null {
  if (!graph) return null;
  const norm = path.replace(/^\.?\/+/, "");
  // Walk top-level + recurse children.
  const stack: ProjectNode[] = [...graph.nodes];
  while (stack.length) {
    const n = stack.shift()!;
    if (n.kind && n.kind.startsWith("uiplan_")) {
      // skip — we don't want to land on uiplan synthetic nodes.
    } else {
      const codePath = n.code?.path;
      if (codePath && (codePath === norm || codePath.endsWith("/" + norm) || norm.endsWith("/" + codePath))) {
        return n.id;
      }
      if (n.id === `file:${norm}` || n.id.endsWith(`:${norm}`)) {
        return n.id;
      }
    }
    if (n.children?.nodes) stack.push(...n.children.nodes);
  }
  return null;
}

/** Lightweight, safe markdown renderer for UiPlan docs.
 *
 * No new dependency. Handles: headings, bold/italic/code spans, fenced code
 * blocks, links, bullet/numbered lists, blockquotes, hr, paragraphs.
 */
export function MarkdownView({ source }: { source: string }) {
  const blocks = parseBlocks(source);
  return (
    <div style={{
      fontFamily: "'Newsreader', Georgia, serif",
      fontSize: 13.5, lineHeight: 1.65, color: PALETTE.text,
    }}>
      {blocks.map((b, i) => renderBlock(b, i))}
    </div>
  );
}

type Block =
  | { kind: "heading"; level: number; text: string }
  | { kind: "code"; lang: string; body: string }
  | { kind: "list"; ordered: boolean; items: string[] }
  | { kind: "quote"; text: string }
  | { kind: "hr" }
  | { kind: "para"; text: string };

function parseBlocks(src: string): Block[] {
  const lines = src.split(/\r?\n/);
  const out: Block[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }

    // fenced code
    const fence = /^```(.*)$/.exec(line);
    if (fence) {
      const lang = fence[1].trim();
      const body: string[] = [];
      i++;
      while (i < lines.length && !/^```/.test(lines[i])) {
        body.push(lines[i]); i++;
      }
      i++; // skip closing fence
      out.push({ kind: "code", lang, body: body.join("\n") });
      continue;
    }

    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    if (heading) {
      out.push({ kind: "heading", level: heading[1].length, text: heading[2].trim() });
      i++; continue;
    }

    if (/^\s*-{3,}\s*$/.test(line) || /^\s*\*{3,}\s*$/.test(line)) {
      out.push({ kind: "hr" });
      i++; continue;
    }

    if (/^\s*>\s?/.test(line)) {
      const quote: string[] = [];
      while (i < lines.length && /^\s*>\s?/.test(lines[i])) {
        quote.push(lines[i].replace(/^\s*>\s?/, ""));
        i++;
      }
      out.push({ kind: "quote", text: quote.join(" ") });
      continue;
    }

    if (/^\s*([-*+]|\d+\.)\s+/.test(line)) {
      const ordered = /^\s*\d+\.\s+/.test(line);
      const items: string[] = [];
      while (i < lines.length && /^\s*([-*+]|\d+\.)\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*([-*+]|\d+\.)\s+/, ""));
        i++;
      }
      out.push({ kind: "list", ordered, items });
      continue;
    }

    // paragraph: gather until blank line
    const para: string[] = [];
    while (i < lines.length && lines[i].trim() && !/^(#{1,6}\s|```|\s*>|\s*([-*+]|\d+\.)\s)/.test(lines[i])) {
      para.push(lines[i]);
      i++;
    }
    out.push({ kind: "para", text: para.join(" ") });
  }
  return out;
}

function renderBlock(b: Block, key: number): React.ReactNode {
  switch (b.kind) {
    case "heading": {
      const sizes = [22, 18, 15.5, 14, 13, 12];
      const size = sizes[Math.min(b.level - 1, sizes.length - 1)];
      return (
        <div key={key} style={{
          margin: "18px 0 6px",
          fontFamily: "'Inter', system-ui, sans-serif",
          fontSize: size, fontWeight: 700, color: PALETTE.text,
          letterSpacing: b.level <= 2 ? "-0.01em" : "0",
        }}>
          {renderInline(b.text)}
        </div>
      );
    }
    case "code":
      return (
        <pre key={key} style={{
          margin: "10px 0", padding: "10px 12px",
          background: "#1e1e1e", color: "#d4d4d4",
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 12, lineHeight: 1.55,
          borderRadius: 6, overflowX: "auto",
        }}>{b.body}</pre>
      );
    case "list":
      return (
        <ul key={key} style={{
          margin: "8px 0", paddingLeft: 22,
          listStyleType: b.ordered ? "decimal" : "disc",
        }}>
          {b.items.map((it, j) => (
            <li key={j} style={{ marginBottom: 4 }}>{renderInline(it)}</li>
          ))}
        </ul>
      );
    case "quote":
      return (
        <blockquote key={key} style={{
          margin: "10px 0", padding: "6px 12px",
          borderLeft: `3px solid ${PALETTE.rule}`,
          color: PALETTE.textDim, fontStyle: "italic",
        }}>
          {renderInline(b.text)}
        </blockquote>
      );
    case "hr":
      return <hr key={key} style={{ margin: "18px 0", border: "none", borderTop: `1px solid ${PALETTE.rule}` }} />;
    case "para":
      return (
        <p key={key} style={{ margin: "8px 0" }}>
          {renderInline(b.text)}
        </p>
      );
  }
}

function renderInline(text: string): React.ReactNode[] {
  // Tokenize on code spans first (to avoid markdown parsing inside them).
  const out: React.ReactNode[] = [];
  let rest = text;
  let key = 0;
  while (rest.length > 0) {
    const codeMatch = /`([^`]+)`/.exec(rest);
    const linkMatch = /\[([^\]]+)\]\(([^)]+)\)/.exec(rest);
    const boldMatch = /\*\*([^*]+)\*\*/.exec(rest);
    const italicMatch = /(?:^|[^*])\*([^*]+)\*/.exec(rest);
    const candidates = [
      codeMatch && { type: "code" as const, m: codeMatch },
      linkMatch && { type: "link" as const, m: linkMatch },
      boldMatch && { type: "bold" as const, m: boldMatch },
      italicMatch && { type: "italic" as const, m: italicMatch },
    ].filter(Boolean) as Array<{ type: "code" | "link" | "bold" | "italic"; m: RegExpExecArray }>;
    if (candidates.length === 0) { out.push(rest); break; }
    candidates.sort((a, b) => a.m.index - b.m.index);
    const first = candidates[0];
    if (first.m.index > 0) out.push(rest.slice(0, first.m.index));
    const k = key++;
    if (first.type === "code") {
      out.push(<code key={k} style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: "0.9em",
        background: PALETTE.bg, border: `1px solid ${PALETTE.rule}`,
        padding: "1px 5px", borderRadius: 3,
      }}>{first.m[1]}</code>);
    } else if (first.type === "link") {
      out.push(<a key={k} href={first.m[2]} target="_blank" rel="noreferrer" style={{ color: "#2563eb" }}>{first.m[1]}</a>);
    } else if (first.type === "bold") {
      out.push(<strong key={k}>{first.m[1]}</strong>);
    } else {
      // italic match may have captured a leading non-* char
      const lead = first.m[0].startsWith("*") ? "" : first.m[0][0];
      if (lead) out.push(lead);
      out.push(<em key={k}>{first.m[1]}</em>);
    }
    rest = rest.slice(first.m.index + first.m[0].length);
  }
  return out;
}
