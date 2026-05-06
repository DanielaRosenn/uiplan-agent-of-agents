import React, { ReactNode } from "react";

interface CleanLayoutProps {
  children: {
    explorer: ReactNode;
    canvas: ReactNode;
    inspector: ReactNode;
  };
}

export function CleanLayout({ children }: CleanLayoutProps) {
  return (
    <div className="clean-layout">
      <aside className="explorer-panel">{children.explorer}</aside>
      <main className="canvas-panel">{children.canvas}</main>
      <aside className="inspector-panel">{children.inspector}</aside>
    </div>
  );
}
