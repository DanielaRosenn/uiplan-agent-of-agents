import React from "react";
import { CheckSquare, Circle, MinusSquare, Square } from "lucide-react";

import { PALETTE } from "../theme";
import type { ProjectNode, TaskSummary } from "../projectGraph/types";
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
      <div style={{ fontSize: 11, color: PALETTE.textMute, fontFamily: "'JetBrains Mono', monospace" }}>
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
          marginLeft: "auto", fontSize: 11, fontWeight: 700,
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
        fontSize: 10, fontFamily: "'JetBrains Mono', monospace",
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
            marginTop: 2, fontSize: 9.5, color: PALETTE.textMute,
            fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.08em",
          }}>
            {node.desc.toUpperCase()}
          </div>
        )}
      </div>
      <span style={{
        fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
        letterSpacing: "0.12em", fontWeight: 700, color,
      }}>
        {status.toUpperCase().replace("_", " ")}
      </span>
    </div>
  );
}

export function UiplanProgressPanel({ node }: { node: ProjectNode }) {
  const summary = node.task_summary;
  const tasks = node.children?.nodes ?? [];
  const taskNodes = tasks.filter((c) => c.kind === "uiplan_task");
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
    </div>
  );
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
          fontSize: 11.5, lineHeight: 1.55,
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
