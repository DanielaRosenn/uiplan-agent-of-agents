import React, { useState } from "react";

import type { AssistantMessage, DiagramNode, Finding } from "../types";

interface AgentPanelProps {
  selectedFinding: Finding | null;
  selectedNode: DiagramNode | null;
  messages: AssistantMessage[];
  onGenerateSection: () => void;
  onApplyCopilotSuggestion: () => Promise<void>;
  onDraftPlanPackageRequest: () => void;
  onDraftScaffoldPackageRequest: () => void;
  onFixSelectedFinding: (finding: Finding) => void;
  onSendMessage: (message: string) => Promise<void>;
}

export default function AgentPanel({
  selectedFinding,
  selectedNode,
  messages,
  onGenerateSection,
  onApplyCopilotSuggestion,
  onDraftPlanPackageRequest,
  onDraftScaffoldPackageRequest,
  onFixSelectedFinding,
  onSendMessage,
}: AgentPanelProps) {
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isApplyingSuggestion, setIsApplyingSuggestion] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const message = draft.trim();
    if (!message) {
      return;
    }
    setDraft("");
    setIsSending(true);
    try {
      await onSendMessage(message);
    } finally {
      setIsSending(false);
    }
  };

  const handleApplyCopilotSuggestion = async () => {
    setIsApplyingSuggestion(true);
    try {
      await onApplyCopilotSuggestion();
    } finally {
      setIsApplyingSuggestion(false);
    }
  };

  return (
    <section aria-label="UiPlan Copilot" className="agent-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Copilot</p>
          <h2>Build with UiPath context</h2>
        </div>
        <span className="copilot-badge">CopilotKit-ready</span>
      </div>
      <p className="muted">
        Copilot can list context sources, search library context, suggest diagram nodes,
        summarize the canvas, and draft preview/package requests. It does not apply document
        changes.
      </p>
      {selectedNode ? (
        <p className="selected-context">Focused on: {selectedNode.title}</p>
      ) : (
        <p className="selected-context">Select a diagram node to focus the assistant.</p>
      )}
      <div className="chat-log" aria-live="polite">
        {messages.map((message, index) => (
          <div key={`${message.role}-${index}`} className={`chat-message ${message.role}`}>
            <strong>{message.role === "assistant" ? "Copilot" : "You"}</strong>
            <p>{message.content}</p>
          </div>
        ))}
      </div>
      <form className="chat-form" onSubmit={handleSubmit}>
        <textarea
          aria-label="Copilot message"
          value={draft}
          rows={3}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Example: show the skills and library context for this workflow"
        />
        <button type="submit" disabled={isSending || !draft.trim()}>
          {isSending ? "Sending..." : "Send"}
        </button>
      </form>
      <div className="studio-actions">
        <button type="button" onClick={onDraftPlanPackageRequest}>
          Draft Plan package request
        </button>
        <button type="button" onClick={onDraftScaffoldPackageRequest}>
          Draft Scaffold package request
        </button>
        <button type="button" onClick={onGenerateSection}>
          Preview diagram from focus
        </button>
        <button
          type="button"
          onClick={handleApplyCopilotSuggestion}
          disabled={isApplyingSuggestion}
        >
          {isApplyingSuggestion ? "Applying suggestion..." : "Apply Copilot add node"}
        </button>
        <button
          type="button"
          onClick={() => selectedFinding && onFixSelectedFinding(selectedFinding)}
          disabled={selectedFinding == null}
        >
          Fix selected finding
        </button>
      </div>
    </section>
  );
}
