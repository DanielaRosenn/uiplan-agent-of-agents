import React from "react";

interface DiffPanelProps {
  diff: string;
}

export default function DiffPanel({ diff }: DiffPanelProps) {
  return (
    <section aria-label="Diff Preview">
      <h2>Diff Preview</h2>
      <pre>{diff}</pre>
    </section>
  );
}
