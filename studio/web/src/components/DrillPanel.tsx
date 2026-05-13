import React from "react";
import { X, ExternalLink } from "lucide-react";
import { PALETTE } from "../theme";

interface DrillPanelProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  content?: string;
  fallback?: string;
  docsPath?: string;
}

export default function DrillPanel({ isOpen, onClose, title, content, fallback, docsPath }: DrillPanelProps) {
  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: "fixed", inset: 0,
          background: "rgba(0, 0, 0, 0.3)",
          zIndex: 40,
        }}
      />

      {/* Slide-over panel */}
      <div style={{
        position: "fixed",
        top: 0, right: 0, bottom: 0,
        width: 480,
        background: PALETTE.bg,
        border: `1px solid ${PALETTE.rule}`,
        borderRight: "none",
        boxShadow: "-4px 0 24px rgba(0, 0, 0, 0.12)",
        zIndex: 50,
        display: "flex", flexDirection: "column",
      }}>
        {/* Header */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "16px 20px",
          borderBottom: `1px solid ${PALETTE.rule}`,
        }}>
          <div>
            <div style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 9, letterSpacing: "0.12em",
              color: PALETTE.textMute, textTransform: "uppercase",
              marginBottom: 4,
            }}>
              DOCUMENTATION
            </div>
            <div style={{
              fontSize: 14, fontWeight: 600,
              color: PALETTE.text,
            }}>
              {title}
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              width: 32, height: 32,
              borderRadius: 6,
              border: `1px solid ${PALETTE.rule}`,
              background: PALETTE.panel,
              cursor: "pointer",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}
          >
            <X size={16} color={PALETTE.textDim} />
          </button>
        </div>

        {/* Content */}
        <div style={{
          flex: 1, overflowY: "auto",
          padding: 20,
        }}>
          {content ? (
            <MarkdownRenderer content={content} />
          ) : (
            <Fallback message={fallback} docsPath={docsPath} />
          )}
        </div>
      </div>
    </>
  );
}

function MarkdownRenderer({ content }: { content: string }) {
  // Simple markdown rendering (in production, use a real markdown library)
  const lines = content.split("\n");
  const rendered: JSX.Element[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Headings
    if (line.startsWith("### ")) {
      rendered.push(
        <h3 key={i} style={{
          fontSize: 15, fontWeight: 700,
          color: PALETTE.text,
          marginTop: 20, marginBottom: 10,
        }}>
          {line.slice(4)}
        </h3>
      );
      continue;
    }
    if (line.startsWith("## ")) {
      rendered.push(
        <h2 key={i} style={{
          fontSize: 17, fontWeight: 700,
          color: PALETTE.text,
          marginTop: 24, marginBottom: 12,
        }}>
          {line.slice(3)}
        </h2>
      );
      continue;
    }
    if (line.startsWith("# ")) {
      rendered.push(
        <h1 key={i} style={{
          fontSize: 20, fontWeight: 700,
          color: PALETTE.text,
          marginTop: 28, marginBottom: 14,
        }}>
          {line.slice(2)}
        </h1>
      );
      continue;
    }

    // Code blocks
    if (line.startsWith("```")) {
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      rendered.push(
        <pre key={i} style={{
          background: PALETTE.panel,
          border: `1px solid ${PALETTE.rule}`,
          borderRadius: 6,
          padding: 12,
          marginTop: 12, marginBottom: 12,
          overflowX: "auto",
        }}>
          <code style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            color: PALETTE.text,
          }}>
            {codeLines.join("\n")}
          </code>
        </pre>
      );
      continue;
    }

    // Lists
    if (line.startsWith("- ") || line.startsWith("* ")) {
      rendered.push(
        <li key={i} style={{
          fontSize: 13,
          color: PALETTE.text,
          lineHeight: 1.6,
          marginTop: 4,
        }}>
          {line.slice(2)}
        </li>
      );
      continue;
    }

    // Paragraphs
    if (line.trim()) {
      rendered.push(
        <p key={i} style={{
          fontSize: 13,
          color: PALETTE.text,
          lineHeight: 1.6,
          marginTop: 12, marginBottom: 12,
        }}>
          {line}
        </p>
      );
    }
  }

  return <div>{rendered}</div>;
}

function Fallback({ message, docsPath }: { message?: string; docsPath?: string }) {
  return (
    <div style={{
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      height: "100%", gap: 16,
    }}>
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 10, letterSpacing: "0.18em",
        color: PALETTE.textMute, textTransform: "uppercase",
      }}>
        NO DOCUMENTATION
      </div>

      <div style={{
        fontFamily: "'Newsreader', Georgia, serif",
        fontSize: 13, fontStyle: "italic",
        textAlign: "center", maxWidth: 320,
        color: PALETTE.textDim, lineHeight: 1.5,
      }}>
        {message || "No drill-down documentation is available for this node."}
      </div>

      {docsPath && (
        <div style={{
          marginTop: 12,
          padding: "8px 12px",
          background: PALETTE.panel,
          border: `1px solid ${PALETTE.rule}`,
          borderRadius: 6,
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 10,
          color: PALETTE.textDim,
        }}>
          Expected at: <span style={{ color: PALETTE.text }}>{docsPath}</span>
        </div>
      )}

      <a
        href="#"
        onClick={(e) => {
          e.preventDefault();
          // In production, this would open the docs file in an editor
          alert("Would open docs file in editor");
        }}
        style={{
          marginTop: 16,
          display: "flex", alignItems: "center", gap: 8,
          padding: "8px 12px",
          background: "#3b82f6",
          color: "#fff",
          borderRadius: 6,
          textDecoration: "none",
          fontSize: 12,
          fontWeight: 600,
        }}
      >
        <ExternalLink size={14} />
        Create Documentation
      </a>
    </div>
  );
}
