export type PhaseEvent = {
  phase: string;
  status: string;
  time: string;
  details?: string;
};

export type HitlDecision = {
  phase: string;
  approved: boolean;
  note?: string;
  time: string;
};

export type UiPlanRunEvents = {
  runId: string;
  phaseHistory: PhaseEvent[];
  hitlDecisions: HitlDecision[];
  loopBudgets: {
    maxBuildIterations: number;
    maxDeployIterations: number;
  };
  buildIterations: Array<Record<string, unknown>>;
  deployIterations: Array<Record<string, unknown>>;
  escalation?: Record<string, unknown>;
  generatedDocuments?: Array<Record<string, unknown>>;
  buildArtifacts?: Array<Record<string, unknown>>;
  provisionedResources?: Array<Record<string, unknown>>;
};

export type CopilotViewModel = {
  runId: string;
  timeline: string[];
  hitlSummary: string[];
  loopSummary: string[];
  dependencySummary: string[];
  escalationSummary: string;
};

const asLabel = (value: unknown): string => String(value ?? "");

export function toCopilotViewModel(input: UiPlanRunEvents): CopilotViewModel {
  const timeline = input.phaseHistory.map(
    (event) => `${event.time} :: ${event.phase} :: ${event.status}${event.details ? ` :: ${event.details}` : ""}`,
  );

  const hitlSummary = input.hitlDecisions.map(
    (decision) =>
      `${decision.phase} => ${decision.approved ? "approved" : "rejected"}${decision.note ? ` (${decision.note})` : ""}`,
  );

  const loopSummary = [
    `build budget: ${input.loopBudgets.maxBuildIterations}, attempts: ${input.buildIterations.length}`,
    `deploy budget: ${input.loopBudgets.maxDeployIterations}, attempts: ${input.deployIterations.length}`,
  ];

  const dependencySummary = [
    `documents: ${(input.generatedDocuments ?? []).length}`,
    `artifacts: ${(input.buildArtifacts ?? []).length}`,
    `resources: ${(input.provisionedResources ?? []).length}`,
  ];

  const escalationSummary = input.escalation && Object.keys(input.escalation).length > 0
    ? `escalation: ${asLabel(input.escalation.reason)}`
    : "escalation: none";

  return {
    runId: input.runId,
    timeline,
    hitlSummary,
    loopSummary,
    dependencySummary,
    escalationSummary,
  };
}
