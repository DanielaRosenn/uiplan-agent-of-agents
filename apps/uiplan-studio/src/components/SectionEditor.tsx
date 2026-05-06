import React from "react";

interface SectionEditorProps {
  documentName: string;
  content: string;
  onChangeContent: (nextContent: string) => void;
}

export default function SectionEditor({
  documentName,
  content,
  onChangeContent,
}: SectionEditorProps) {
  return (
    <section>
      <h2>Editor</h2>
      <p>{documentName}</p>
      <textarea
        aria-label="Document content"
        value={content}
        rows={16}
        onChange={(event) => onChangeContent(event.target.value)}
      />
    </section>
  );
}
