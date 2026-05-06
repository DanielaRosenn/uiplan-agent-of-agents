import type { ApprovalPackageDetail, FileProposal, StageId, StageManifest } from "../generationTypes";
import type { ContextSource, ContextSourceCategory, DocumentName } from "../types";
import {
  normalizeProjectGraph,
  type ProjectGraphAdapterInput,
  type ProjectGraphAdapterResult,
  type ProjectGraphClusterInput,
  type ProjectGraphEdgeInput,
  type ProjectGraphInput,
  type ProjectGraphIssue,
  type ProjectGraphIssueInput,
  type ProjectGraphNodeInput,
  type ProjectGraphProjectType,
} from "./types";

type AdapterParts = Omit<ProjectGraphInput, "projectType">;

const DOCUMENT_NAMES: DocumentName[] = ["spec.md", "plan.md", "tasks.md"];
const MERMAID_HEADER_PATTERN = /^(flowchart|graph)\s+(?:TB|TD|BT|RL|LR)?\b/i;
const MERMAID_BLOCK_PATTERN = /```mermaid\s*([\s\S]*?)```/gi;

interface UiPlanDocumentsSource {
  documents?: Partial<Record<DocumentName | string, string>>;
  bundleRoot?: string;
}

interface MermaidParseState {
  nodes: ProjectGraphNodeInput[];
  edges: ProjectGraphEdgeInput[];
  issues: ProjectGraphIssueInput[];
  nodeIds: Set<string>;
}

export function adaptUiPlanDocuments(input: ProjectGraphAdapterInput): ProjectGraphAdapterResult {
  const source = readDocumentsSource(input.source);
  const nodes: ProjectGraphNodeInput[] = [];
  const edges: ProjectGraphEdgeInput[] = [];
  const clusters: ProjectGraphClusterInput[] = [];
  const issues: ProjectGraphIssueInput[] = [];

  DOCUMENT_NAMES.forEach((documentName) => {
    const text = source.documents[documentName];
    if (text == null) {
      return;
    }

    const documentId = `doc:${slugify(documentName)}`;
    const sectionIds: string[] = [];
    const taskIds: string[] = [];
    nodes.push({
      id: documentId,
      label: documentName,
      kind: "generated_artifact",
      layer: "document",
      metadata: {
        nodeType: "document",
        documentName,
        bundleRoot: source.bundleRoot,
        characterCount: text.length,
      },
    });

    const sections = extractMarkdownSections(documentName, text);
    sections.forEach((section, index) => {
      const sectionId = `${documentId}:section:${index + 1}`;
      sectionIds.push(sectionId);
      nodes.push({
        id: sectionId,
        label: section.title,
        kind: "generated_artifact",
        layer: "section",
        metadata: {
          nodeType: "section",
          documentName,
          level: section.level,
          line: section.line,
        },
      });
      edges.push({
        id: `${documentId}:documents:${sectionId}`,
        source: documentId,
        target: sectionId,
        kind: "documents",
        metadata: { source: "projectGraph.documents" },
      });
    });

    const tasks = extractMarkdownTasks(documentName, text, sections);
    tasks.forEach((task, index) => {
      const taskId = `${documentId}:task:${index + 1}`;
      taskIds.push(taskId);
      nodes.push({
        id: taskId,
        label: task.label,
        kind: "process_step",
        layer: "task",
        metadata: {
          nodeType: "task",
          documentName,
          line: task.line,
          done: task.done,
          status: task.done ? "done" : "pending",
          sectionId: task.sectionId,
        },
      });
      edges.push({
        id: `${documentId}:documents:${taskId}`,
        source: documentId,
        target: taskId,
        kind: "documents",
        metadata: { source: "projectGraph.documents" },
      });
      if (task.sectionId) {
        edges.push({
          id: `${task.sectionId}:drives:${taskId}`,
          source: task.sectionId,
          target: taskId,
          kind: "drives",
          metadata: { source: "projectGraph.documents" },
        });
      }
    });

    clusters.push({
      id: `cluster:${documentId}`,
      label: documentName,
      nodeIds: [documentId, ...sectionIds, ...taskIds],
      kind: "document",
      metadata: { source: "projectGraph.documents", documentName },
    });
  });

  if (nodes.length === 0) {
    issues.push({
      id: "documents:none",
      message: "No UiPlan document content was provided.",
      severity: "note",
      metadata: { source: "projectGraph.documents" },
    });
  }

  return createAdapterResult(input.projectType, { nodes, edges, clusters, errors: issues });
}

export function extractMarkdownTodos(
  markdown: string,
): Array<{ label: string; done: boolean; line: number }> {
  return markdown
    .split(/\r?\n/)
    .map((line, index) => {
      const match = line.match(/^\s*[-*+]\s+\[([ xX])\]\s+(.+?)\s*$/);
      if (!match) {
        return null;
      }
      return {
        label: match[2].trim(),
        done: match[1].toLowerCase() === "x",
        line: index + 1,
      };
    })
    .filter((task): task is { label: string; done: boolean; line: number } => task != null);
}

export function adaptMermaidFlowcharts(input: ProjectGraphAdapterInput): ProjectGraphAdapterResult {
  const mermaidBlocks = readMermaidSources(input.source);
  const state: MermaidParseState = {
    nodes: [],
    edges: [],
    issues: [],
    nodeIds: new Set(),
  };

  mermaidBlocks.forEach((block, index) => parseMermaidBlock(block, index + 1, state));

  if (mermaidBlocks.length === 0) {
    state.issues.push({
      id: "mermaid:none",
      message: "No supported Mermaid flowchart or graph block was provided.",
      severity: "note",
      metadata: { source: "projectGraph.mermaid" },
    });
  }

  return createAdapterResult(input.projectType, {
    nodes: state.nodes,
    edges: state.edges,
    errors: state.issues,
  });
}

export function adaptContextSources(input: ProjectGraphAdapterInput): ProjectGraphAdapterResult {
  const sources = readContextSources(input.source);
  const nodes: ProjectGraphNodeInput[] = [];
  const issues: ProjectGraphIssueInput[] = [];

  sources.forEach((source) => {
    const classification = classifyContextSource(source);
    const nodeId = `context:${slugify(source.id)}`;
    nodes.push({
      id: nodeId,
      label: source.title,
      kind: classification.kind,
      layer: classification.layer,
      metadata: {
        nodeType: classification.layer,
        contextSourceId: source.id,
        category: source.category,
        description: source.description,
        source: source.source,
        available: source.available,
      },
    });

    if (!source.available) {
      issues.push({
        id: `${nodeId}:unavailable`,
        message: `Context source '${source.title}' is not currently available.`,
        severity: "warning",
        targetId: nodeId,
        metadata: { source: "projectGraph.contextSources" },
      });
    }
  });

  return createAdapterResult(input.projectType, { nodes, errors: issues });
}

export function adaptApprovalPackage(input: ProjectGraphAdapterInput): ProjectGraphAdapterResult {
  const detail = input.source as Partial<ApprovalPackageDetail>;
  const nodes: ProjectGraphNodeInput[] = [];
  const edges: ProjectGraphEdgeInput[] = [];
  const issues: ProjectGraphIssueInput[] = [];

  const packageId = detail.manifest?.package_id ?? "approval-package";
  const stages = Array.isArray(detail.stages) ? detail.stages : [];
  const proposals = Array.isArray(detail.proposals) ? detail.proposals : [];
  const stageIds = new Set<StageId>();

  stages.forEach((stage, index) => {
    if (!isStageManifest(stage)) {
      issues.push(createMalformedApprovalItemIssue("stage", index));
      return;
    }
    const stageNodeId = stageNodeIdFor(stage.stage_id);
    stageIds.add(stage.stage_id);
    nodes.push({
      id: stageNodeId,
      label: stage.stage_id,
      kind: "review_gate",
      layer: "approval_stage",
      metadata: {
        nodeType: "approval_stage",
        packageId,
        stageId: stage.stage_id,
        status: stage.status,
        applyEligible: stage.apply_eligible,
        blockingFindings: stage.blocking_findings,
      },
    });

    const nextStage = stages[index + 1];
    if (isStageManifest(nextStage)) {
      edges.push({
        id: `${stageNodeId}:blocks:${stageNodeIdFor(nextStage.stage_id)}`,
        source: stageNodeId,
        target: stageNodeIdFor(nextStage.stage_id),
        kind: "blocks",
        label: "blocks",
        metadata: { source: "projectGraph.approvalPackage" },
      });
    }
  });

  proposals.forEach((proposal, index) => {
    if (!isFileProposal(proposal)) {
      issues.push(createMalformedApprovalItemIssue("proposal", index));
      return;
    }
    if (!stageIds.has(proposal.stage_id)) {
      stageIds.add(proposal.stage_id);
      nodes.push({
        id: stageNodeIdFor(proposal.stage_id),
        label: proposal.stage_id,
        kind: "review_gate",
        layer: "approval_stage",
        metadata: {
          nodeType: "approval_stage",
          packageId,
          stageId: proposal.stage_id,
          synthesized: true,
        },
      });
      issues.push({
        id: `approval-package:synthetic-stage:${proposal.stage_id}`,
        message: `Synthesized missing approval stage '${proposal.stage_id}' from proposal metadata.`,
        severity: "note",
        targetId: stageNodeIdFor(proposal.stage_id),
        metadata: { source: "projectGraph.approvalPackage" },
      });
    }

    const proposalNodeId = `proposal:${slugify(proposal.proposal_id)}`;
    nodes.push({
      id: proposalNodeId,
      label: proposal.target_path,
      kind: "generated_artifact",
      layer: "proposal",
      metadata: {
        nodeType: "proposal",
        packageId,
        proposalId: proposal.proposal_id,
        stageId: proposal.stage_id,
        targetPath: proposal.target_path,
        fileKind: proposal.file_kind,
        owningNodeIds: proposal.owning_node_ids,
        projectTypeIds: proposal.project_type_ids,
        applyEligible: proposal.apply_eligible,
        citations: proposal.citations,
        findings: proposal.findings,
      },
    });

    edges.push({
      id: `${stageNodeIdFor(proposal.stage_id)}:generates:${proposalNodeId}`,
      source: stageNodeIdFor(proposal.stage_id),
      target: proposalNodeId,
      kind: "generates",
      label: "generates",
      metadata: { source: "projectGraph.approvalPackage" },
    });

    proposal.owning_node_ids.forEach((owningNodeId) => {
      edges.push({
        id: `${owningNodeId}:generates:${proposalNodeId}`,
        source: owningNodeId,
        target: proposalNodeId,
        kind: "generates",
        metadata: { source: "projectGraph.approvalPackage", optionalOwnerReference: true },
      });
    });
  });

  if (stages.length === 0 && proposals.length === 0) {
    issues.push({
      id: "approval-package:empty",
      message: "Approval package has no stages or proposals to adapt.",
      severity: "note",
      metadata: { source: "projectGraph.approvalPackage" },
    });
  }

  return createAdapterResult(input.projectType, { nodes, edges, errors: issues });
}

export function composeProjectGraphResults(
  projectType: ProjectGraphProjectType,
  results: ProjectGraphAdapterResult[],
): ProjectGraphAdapterResult {
  const nodes = new Map<string, ProjectGraphNodeInput>();
  const edges = new Map<string, ProjectGraphEdgeInput>();
  const clusters = new Map<string, ProjectGraphClusterInput>();
  const issues: ProjectGraphIssueInput[] = [];

  results.forEach((result) => {
    result.graph.nodes.forEach((node) => addUnique(nodes, node, "node", issues));
    result.graph.edges.forEach((edge) => addUnique(edges, edge, "edge", issues));
    result.graph.clusters.forEach((cluster) => addUnique(clusters, cluster, "cluster", issues));
    issues.push(...result.issues, ...result.graph.errors);
  });

  return createAdapterResult(projectType, {
    nodes: [...nodes.values()],
    edges: [...edges.values()],
    clusters: [...clusters.values()],
    errors: dedupeIssues(issues),
  });
}

export const uiPlanDocumentsAdapter = adaptUiPlanDocuments;
export const mermaidFlowchartAdapter = adaptMermaidFlowcharts;
export const contextSourcesAdapter = adaptContextSources;
export const approvalPackageAdapter = adaptApprovalPackage;

function createAdapterResult(
  projectType: ProjectGraphProjectType,
  parts: AdapterParts,
): ProjectGraphAdapterResult {
  const graph = normalizeProjectGraph({ projectType, ...parts });
  return { graph, issues: graph.errors };
}

function readDocumentsSource(source: unknown): { documents: Record<string, string>; bundleRoot?: string } {
  const candidate = source as UiPlanDocumentsSource;
  if (candidate?.documents && typeof candidate.documents === "object") {
    return {
      documents: Object.fromEntries(
        Object.entries(candidate.documents).filter((entry): entry is [string, string] => {
          return typeof entry[1] === "string";
        }),
      ),
      bundleRoot: candidate.bundleRoot,
    };
  }

  return { documents: {} };
}

function extractMarkdownSections(documentName: DocumentName, markdown: string) {
  return markdown
    .split(/\r?\n/)
    .map((line, index) => {
      const match = line.match(/^(#{1,6})\s+(.+?)\s*#*\s*$/);
      if (!match) {
        return null;
      }
      return {
        title: match[2].trim(),
        level: match[1].length,
        line: index + 1,
        documentName,
      };
    })
    .filter(
      (section): section is { title: string; level: number; line: number; documentName: DocumentName } =>
        section != null,
    );
}

function extractMarkdownTasks(
  documentName: DocumentName,
  markdown: string,
  sections: Array<{ line: number }>,
) {
  return extractMarkdownTodos(markdown).map((task) => {
    const sectionIndex = sections.findLastIndex((section) => section.line < task.line);
    const documentId = `doc:${slugify(documentName)}`;
    return {
      ...task,
      sectionId: sectionIndex < 0 ? undefined : `${documentId}:section:${sectionIndex + 1}`,
    };
  });
}

function readMermaidSources(source: unknown): string[] {
  if (typeof source === "string") {
    const blocks = [...source.matchAll(MERMAID_BLOCK_PATTERN)].map((match) => match[1]);
    if (blocks.length > 0) {
      return blocks.filter((block) => MERMAID_HEADER_PATTERN.test(firstContentLine(block)));
    }
    return MERMAID_HEADER_PATTERN.test(firstContentLine(source)) ? [source] : [];
  }

  const candidate = source as { text?: unknown; mermaid?: unknown; blocks?: unknown };
  if (typeof candidate?.mermaid === "string") {
    return readMermaidSources(candidate.mermaid);
  }
  if (typeof candidate?.text === "string") {
    return readMermaidSources(candidate.text);
  }
  if (Array.isArray(candidate?.blocks)) {
    return candidate.blocks.filter((block): block is string => typeof block === "string");
  }
  return [];
}

function parseMermaidBlock(block: string, blockIndex: number, state: MermaidParseState): void {
  const lines = block.split(/\r?\n/);
  lines.forEach((rawLine, index) => {
    const line = rawLine.trim().replace(/;$/, "");
    if (!line || line.startsWith("%%") || MERMAID_HEADER_PATTERN.test(line)) {
      return;
    }
    if (/^(subgraph|end|classDef|class|style|linkStyle|click)\b/i.test(line)) {
      state.issues.push(createUnsupportedMermaidIssue(blockIndex, index + 1, line));
      return;
    }

    const edge = parseMermaidEdge(line);
    if (edge) {
      const source = addMermaidNode(edge.source, blockIndex, state);
      const target = addMermaidNode(edge.target, blockIndex, state);
      state.edges.push({
        id: `mermaid:${blockIndex}:edge:${state.edges.length + 1}`,
        source: source.id,
        target: target.id,
        kind: "drives",
        label: edge.label,
        metadata: {
          source: "projectGraph.mermaid",
          nodeType: "transition",
          mermaidOperator: edge.operator,
          line: index + 1,
        },
      });
      return;
    }

    const node = parseMermaidNodeRef(line);
    if (node) {
      addMermaidNode(node, blockIndex, state);
      return;
    }

    state.issues.push(createUnsupportedMermaidIssue(blockIndex, index + 1, line));
  });
}

function parseMermaidEdge(line: string) {
  const pipeLabeled = line.match(/^(.+?)\s*(-->|==>|-\.->|->)\s*\|\s*(.+?)\s*\|\s*(.+)$/);
  if (pipeLabeled) {
    const source = parseMermaidNodeRef(pipeLabeled[1]);
    const target = parseMermaidNodeRef(pipeLabeled[4]);
    if (!source || !target) {
      return null;
    }
    return {
      source,
      target,
      label: pipeLabeled[3].trim(),
      operator: pipeLabeled[2],
    };
  }

  const labeled = line.match(/^(.+?)\s+--\s*(.+?)\s*-->\s+(.+)$/);
  if (labeled) {
    const source = parseMermaidNodeRef(labeled[1]);
    const target = parseMermaidNodeRef(labeled[3]);
    if (!source || !target) {
      return null;
    }
    return {
      source,
      target,
      label: labeled[2].trim(),
      operator: "-->",
    };
  }

  const plain = line.match(/^(.+?)\s*(-->|==>|-\.->|->)\s*(.+)$/);
  if (plain) {
    const source = parseMermaidNodeRef(plain[1]);
    const target = parseMermaidNodeRef(plain[3]);
    if (!source || !target) {
      return null;
    }
    return {
      source,
      target,
      label: undefined,
      operator: plain[2],
    };
  }

  return null;
}

function parseMermaidNodeRef(token: string | null) {
  if (!token) {
    return null;
  }

  const normalized = token.trim().replace(/;$/, "");
  const match = normalized.match(/^([A-Za-z0-9_:-]+)(?:\s*(\[\[|\[|\{\{|\{|\(\(|\(|>)(.*?)(\]\]|\]|\}\}|\}|\)\)|\)|\]))?$/);
  if (!match) {
    return null;
  }

  return {
    rawId: match[1],
    localId: match[1],
    label: (match[3] ?? match[1]).trim(),
    shape: match[2] ?? "implicit",
  };
}

function addMermaidNode(
  parsed: NonNullable<ReturnType<typeof parseMermaidNodeRef>>,
  blockIndex: number,
  state: MermaidParseState,
) {
  const nodeId = mermaidNodeId(blockIndex, parsed.localId);
  if (!state.nodeIds.has(nodeId)) {
    state.nodeIds.add(nodeId);
    state.nodes.push({
      id: nodeId,
      label: parsed.label,
      kind: "process_step",
      layer: "workflow",
      metadata: {
        source: "projectGraph.mermaid",
        nodeType: "workflow",
        mermaidId: parsed.rawId,
        mermaidLocalId: parsed.localId,
        mermaidShape: parsed.shape,
        blockIndex,
      },
    });
  }
  return { id: nodeId };
}

function readContextSources(source: unknown): ContextSource[] {
  if (Array.isArray(source)) {
    return source.filter(isContextSource);
  }

  const candidate = source as { sources?: unknown; categories?: unknown };
  if (Array.isArray(candidate?.sources)) {
    return candidate.sources.filter(isContextSource);
  }
  if (Array.isArray(candidate?.categories)) {
    return candidate.categories.flatMap((category) => {
      const typedCategory = category as ContextSourceCategory;
      return Array.isArray(typedCategory.sources) ? typedCategory.sources.filter(isContextSource) : [];
    });
  }
  return [];
}

function isContextSource(value: unknown): value is ContextSource {
  const candidate = value as ContextSource;
  return (
    typeof candidate?.id === "string" &&
    typeof candidate.title === "string" &&
    typeof candidate.category === "string" &&
    typeof candidate.source === "string" &&
    typeof candidate.available === "boolean"
  );
}

function classifyContextSource(source: ContextSource) {
  const searchable = `${source.kind} ${source.category} ${source.id} ${source.source} ${source.title}`.toLowerCase();
  if (searchable.includes("tool") || searchable.includes("mcp")) {
    return { kind: "tool" as const, layer: "tool" };
  }
  if (searchable.includes("skill")) {
    return { kind: "skill" as const, layer: "skill" };
  }
  if (searchable.includes("library") || searchable.includes("book")) {
    return { kind: "docs_context" as const, layer: "library" };
  }
  return { kind: "docs_context" as const, layer: "context" };
}

function addUnique<T extends { id: string }>(
  target: Map<string, T>,
  item: T,
  itemType: string,
  issues: ProjectGraphIssueInput[],
): void {
  if (target.has(item.id)) {
    issues.push({
      id: `compose:duplicate-${itemType}:${item.id}`,
      message: `Duplicate ${itemType} '${item.id}' was ignored while composing ProjectGraph results.`,
      severity: "warning",
      targetId: item.id,
      metadata: { source: "projectGraph.compose" },
    });
    return;
  }
  target.set(item.id, item);
}

function dedupeIssues(issues: ProjectGraphIssueInput[]): ProjectGraphIssueInput[] {
  const seen = new Set<string>();
  return issues.filter((issue) => {
    if (seen.has(issue.id)) {
      return false;
    }
    seen.add(issue.id);
    return true;
  });
}

function stageNodeIdFor(stageId: StageId): string {
  return `approval-stage:${stageId}`;
}

function mermaidNodeId(blockIndex: number, localId: string): string {
  return `mermaid:${blockIndex}:${slugify(localId)}`;
}

function isStageManifest(value: unknown): value is StageManifest {
  const candidate = value as StageManifest;
  return (
    candidate != null &&
    typeof candidate.stage_id === "string" &&
    typeof candidate.status === "string" &&
    Array.isArray(candidate.blocking_findings) &&
    typeof candidate.apply_eligible === "boolean"
  );
}

function isFileProposal(value: unknown): value is FileProposal {
  const candidate = value as FileProposal;
  return (
    candidate != null &&
    typeof candidate.proposal_id === "string" &&
    typeof candidate.stage_id === "string" &&
    typeof candidate.target_path === "string" &&
    typeof candidate.file_kind === "string" &&
    Array.isArray(candidate.owning_node_ids) &&
    Array.isArray(candidate.project_type_ids) &&
    Array.isArray(candidate.citations) &&
    Array.isArray(candidate.findings) &&
    typeof candidate.apply_eligible === "boolean"
  );
}

function createMalformedApprovalItemIssue(
  itemType: "stage" | "proposal",
  index: number,
): ProjectGraphIssue {
  return {
    id: `approval-package:malformed-${itemType}:${index}`,
    message: `Malformed approval package ${itemType} at index ${index} was ignored.`,
    severity: "warning",
    metadata: { source: "projectGraph.approvalPackage" },
  };
}

function createUnsupportedMermaidIssue(
  blockIndex: number,
  line: number,
  syntax: string,
): ProjectGraphIssue {
  return {
    id: `mermaid:${blockIndex}:unsupported:${line}`,
    message: `Unsupported Mermaid syntax ignored on line ${line}.`,
    severity: "warning",
    metadata: { source: "projectGraph.mermaid", syntax },
  };
}

function firstContentLine(value: string): string {
  return value.split(/\r?\n/).find((line) => line.trim().length > 0)?.trim() ?? "";
}

function slugify(value: string): string {
  const slug = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "item";
}
