import React from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

interface CodeSnippetViewerProps {
  code: string;
  language: string;
  lines?: string;
}

export default function CodeSnippetViewer({ code, language, lines }: CodeSnippetViewerProps) {
  return (
    <div className="code-snippet">
      <div className="code-header">
        <span>{lines}</span>
      </div>
      <SyntaxHighlighter language={language} style={vscDarkPlus}>
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
