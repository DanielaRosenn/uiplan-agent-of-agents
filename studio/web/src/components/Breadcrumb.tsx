import React from "react";
import { ArrowLeft, ChevronRight, Home } from "lucide-react";

import { PALETTE, getLayer } from "../theme";
import type { ProjectNode } from "../projectGraph/types";

interface BreadcrumbProps {
  trail: ProjectNode[];
  onNavigate: (depth: number) => void;
  onBack: () => void;
}

export default function Breadcrumb({ trail, onNavigate, onBack }: BreadcrumbProps) {
  if (trail.length === 0) return null;
  return (
    <div style={{ position: "absolute", top: 12, left: 12, right: 12, zIndex: 10, display: "flex", alignItems: "center", gap: 8, pointerEvents: "none" }}>
      <button onClick={onBack} style={{
        pointerEvents: "auto",
        display: "flex", alignItems: "center", gap: 5,
        padding: "6px 10px", background: PALETTE.panel,
        border: `1px solid ${PALETTE.rule}`,
        borderRadius: 4, cursor: "pointer",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 10.5, fontWeight: 600, color: PALETTE.text, letterSpacing: "0.08em",
      }} title="Back (Esc)">
        <ArrowLeft size={12} strokeWidth={2.2} />
        BACK
      </button>

      <div style={{
        pointerEvents: "auto",
        display: "flex", alignItems: "center", gap: 4,
        padding: "6px 12px", background: PALETTE.panel,
        border: `1px solid ${PALETTE.rule}`, borderRadius: 4,
        fontFamily: "'JetBrains Mono', monospace", fontSize: 10.5,
        flex: "0 1 auto", minWidth: 0, overflow: "hidden",
      }}>
        <button onClick={() => onNavigate(0)} style={{
          background: "transparent", border: "none", cursor: "pointer", padding: "2px 4px",
          display: "flex", alignItems: "center", gap: 5, color: PALETTE.textDim,
          fontFamily: "inherit", fontSize: "inherit", letterSpacing: "0.18em", fontWeight: 700,
        }}>
          <Home size={11} />
          ROOT
        </button>
        {trail.map((crumb, i) => {
          const layer = getLayer(crumb.layer);
          const isLast = i === trail.length - 1;
          return (
            <React.Fragment key={i}>
              <ChevronRight size={10} style={{ color: PALETTE.textMute, flexShrink: 0 }} />
              <button onClick={() => onNavigate(i + 1)} style={{
                background: isLast ? layer.soft : "transparent",
                border: isLast ? `1px solid ${layer.color}33` : "1px solid transparent",
                borderRadius: 3, padding: "2px 7px",
                cursor: isLast ? "default" : "pointer",
                display: "flex", alignItems: "center", gap: 5,
                color: isLast ? layer.color : PALETTE.text,
                fontFamily: "inherit", fontSize: "inherit",
                fontWeight: isLast ? 700 : 500,
                whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: 200,
              }}>
                <div style={{ width: 5, height: 5, background: layer.color, borderRadius: 1, flexShrink: 0 }} />
                {crumb.label}
              </button>
            </React.Fragment>
          );
        })}
      </div>

      <div style={{ flex: 1 }} />

      <div style={{
        pointerEvents: "auto",
        padding: "6px 10px", background: PALETTE.panel,
        border: `1px solid ${PALETTE.rule}`, borderRadius: 4,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 9.5, color: PALETTE.textDim, letterSpacing: "0.15em",
      }}>
        DEPTH&nbsp;·&nbsp;{String(trail.length).padStart(2, "0")}
      </div>
    </div>
  );
}
