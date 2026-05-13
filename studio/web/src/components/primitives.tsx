import React from "react";
import { PALETTE } from "../theme";

export function Section({ label, count }: { label: string; count?: number }) {
  // Convert ALL CAPS labels to Title Case or Sentence case
  const formattedLabel = label.length > 0 
    ? label.charAt(0).toUpperCase() + label.slice(1).toLowerCase() 
    : label;

  return (
    <div style={{
      fontSize: 13, fontWeight: 600,
      color: PALETTE.text,
      display: "flex", alignItems: "center", gap: 8,
      fontFamily: "'Inter', sans-serif",
    }}>
      <span>{formattedLabel}</span>
      {count !== undefined && (
        <span style={{ color: PALETTE.textMute, fontSize: 12 }}>· {String(count).padStart(2, "0")}</span>
      )}
      <div style={{ flex: 1, height: 1, background: PALETTE.rule }} />
    </div>
  );
}

export function SyntaxHighlight({ code }: { code: string }) {
  const TOKENS: Array<{ re: RegExp; color: string }> = [
    { re: /(\/\/[^\n]*|#[^\n]*)/g, color: "#6a9955" },
    { re: /("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)/g, color: "#ce9178" },
    { re: /\b(import|from|export|const|let|var|function|return|async|await|class|def|if|else|for|while|new|public|true|false|None|null)\b/g, color: "#569cd6" },
    { re: /\b([A-Z][a-zA-Z0-9_]*)\b/g, color: "#4ec9b0" },
    { re: /\b(\d+)\b/g, color: "#b5cea8" },
  ];

  const segments: Array<{ start: number; end: number; color: string; text: string }> = [];
  const claimed = new Array(code.length).fill(false);
  TOKENS.forEach(({ re, color }) => {
    let m: RegExpExecArray | null;
    re.lastIndex = 0;
    while ((m = re.exec(code)) !== null) {
      const start = m.index;
      const end = start + m[0].length;
      let any = false;
      for (let i = start; i < end; i++) if (claimed[i]) { any = true; break; }
      if (!any) {
        segments.push({ start, end, color, text: m[0] });
        for (let i = start; i < end; i++) claimed[i] = true;
      }
    }
  });
  segments.sort((a, b) => a.start - b.start);

  const out: React.ReactNode[] = [];
  let cursor = 0;
  segments.forEach((seg, i) => {
    if (seg.start > cursor) out.push(<span key={`p${i}`}>{code.slice(cursor, seg.start)}</span>);
    out.push(<span key={`t${i}`} style={{ color: seg.color }}>{seg.text}</span>);
    cursor = seg.end;
  });
  if (cursor < code.length) out.push(<span key="end">{code.slice(cursor)}</span>);
  return <>{out}</>;
}

export function StatusPip({ color, title }: { color: string; title?: string }) {
  return (
    <span title={title} style={{
      display: "inline-block",
      width: 8, height: 8, borderRadius: "50%",
      background: color,
      boxShadow: `0 0 0 2px ${PALETTE.panel}, 0 0 0 3px ${color}33`,
    }} />
  );
}
