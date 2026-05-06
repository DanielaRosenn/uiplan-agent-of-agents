import type {
  AssistantChatResponse,
  BundleData,
  ContextSourcesResponse,
  DiagramData,
  DiagramEdge,
  DiagramNode,
  DocumentName,
  LibraryContextResponse,
  LifecycleReadinessResponse,
  ReviewResponse,
  SectionPreviewResponse,
} from "../types";
import { resolveApiBaseUrl } from "../config";
import { toGenerationGraphPayload } from "../generationGraphAdapter";
import type { ProjectGraph } from "../projectGraph/types";
import type { ProjectGraphTemplateMetadata } from "../projectGraph/templates";
import type {
  ApprovalPackageDetail as PackageDetail,
  ApprovalPackageManifest,
  ApprovalStatus,
  CommandRegistry,
  StageId,
} from "../generationTypes";

interface ApiOptions {
  baseUrl?: string;
}

export interface ProposalPreviewResponse {
  preview_id: string;
  proposal_id?: string;
  target_path?: string;
  diff?: string;
  diff_body?: string;
  diff_content?: string;
}

export interface GraphNodeContextResponse {
  node_id: string;
  query: string;
  citations: Array<{
    source_type: string;
    source_id: string;
    snippet: string;
    strict: boolean;
  }>;
}

export interface GraphActionExecuteResponse {
  message: string;
  workspace: {
    nodes: DiagramNode[];
    edges: DiagramEdge[];
    [key: string]: unknown;
  };
}

export function createApiClient(options: ApiOptions = {}) {
  const baseUrl = resolveApiBaseUrl(options.baseUrl ?? import.meta.env.VITE_UIPLAN_API_URL);

  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${baseUrl}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
    return (await response.json()) as T;
  }

  return {
    loadBundle(bundleRoot: string) {
      const encodedRoot = encodeURIComponent(bundleRoot);
      return request<BundleData>(`/bundle/load?bundle_root=${encodedRoot}`);
    },
    loadDiagram(bundleRoot: string) {
      const encodedRoot = encodeURIComponent(bundleRoot);
      return request<DiagramData & { path?: string | null; defaulted?: boolean }>(
        `/diagram/load?bundle_root=${encodedRoot}`,
      );
    },
    saveDiagram(bundleRoot: string, nodes: DiagramNode[], edges: DiagramEdge[]) {
      return request<DiagramData & { path: string; bytes_written: number }>("/diagram/save", {
        method: "POST",
        body: JSON.stringify({
          bundle_root: bundleRoot,
          nodes,
          edges,
        }),
      });
    },
    runReview(spec: string, plan: string, tasks: string) {
      return request<ReviewResponse>("/review/run", {
        method: "POST",
        body: JSON.stringify({ spec, plan, tasks }),
      });
    },
    runLifecycleReadiness(spec: string, plan: string, tasks: string) {
      return request<LifecycleReadinessResponse>("/lifecycle/readiness", {
        method: "POST",
        body: JSON.stringify({ spec, plan, tasks }),
      });
    },
    previewSection(
      bundleRoot: string,
      documentName: DocumentName,
      proposedContent: string,
      libraryContext: Array<Record<string, string | number | null>> = [],
    ) {
      return request<SectionPreviewResponse>("/generate/section-preview", {
        method: "POST",
        body: JSON.stringify({
          bundle_root: bundleRoot,
          document_name: documentName,
          proposed_content: proposedContent,
          library_context: libraryContext,
        }),
      });
    },
    previewDiagramDocument(
      bundleRoot: string,
      documentName: DocumentName,
      nodes: DiagramNode[],
      edges: DiagramEdge[],
      focus: string | null,
      context: Array<Record<string, string | number | null>> = [],
    ) {
      return request<SectionPreviewResponse>("/generate/diagram-preview", {
        method: "POST",
        body: JSON.stringify({
          bundle_root: bundleRoot,
          document_name: documentName,
          nodes,
          edges,
          focus,
          context,
        }),
      });
    },
    searchLibraryContext(query: string, topN = 5) {
      return request<LibraryContextResponse>("/agent/library-context", {
        method: "POST",
        body: JSON.stringify({ query, top_n: topN }),
      });
    },
    resolveGraphNodeContext(nodeId: string, query: string, sources: string[]) {
      return request<GraphNodeContextResponse>("/graph/context/resolve", {
        method: "POST",
        body: JSON.stringify({
          node_id: nodeId,
          query,
          sources,
        }),
      });
    },
    executeGraphAction(
      action: string,
      payload: Record<string, unknown>,
      workspace: { nodes: DiagramNode[]; edges: DiagramEdge[]; [key: string]: unknown },
    ) {
      return request<GraphActionExecuteResponse>("/graph/actions/execute", {
        method: "POST",
        body: JSON.stringify({
          action,
          payload,
          workspace,
        }),
      });
    },
    loadContextSources() {
      return request<ContextSourcesResponse>("/agent/context-sources");
    },
    loadStarterProjectGraphTemplate() {
      return request<{ metadata: ProjectGraphTemplateMetadata; graph: ProjectGraph }>(
        "/project-graph/templates/starter",
      );
    },
    loadCommandRegistry() {
      return request<CommandRegistry>("/generation/command-registry");
    },
    chatWithAssistant(message: string, nodes: DiagramNode[], selectedNodeId: string | null) {
      return request<AssistantChatResponse>("/agent/chat", {
        method: "POST",
        body: JSON.stringify({
          message,
          nodes,
          selected_node_id: selectedNodeId,
        }),
      });
    },
    applyPreview(previewId: string) {
      return request<{ path: string; backup_path: string; bytes_written: number }>(
        "/generate/apply",
        {
          method: "POST",
          body: JSON.stringify({ preview_id: previewId }),
        },
      );
    },
    generateApprovalPackage(
      bundleRoot: string,
      graph: DiagramData,
      stages: StageId[],
      reviewer: string | null = null,
    ) {
      return request<ApprovalPackageManifest>("/generation/packages", {
        method: "POST",
        body: JSON.stringify({
          bundle_root: bundleRoot,
          graph: toGenerationGraphPayload(bundleRoot, graph),
          stages,
          reviewer,
        }),
      });
    },
    listApprovalPackages(bundleRoot: string) {
      const encodedRoot = encodeURIComponent(bundleRoot);
      return request<{ packages: ApprovalPackageManifest[] }>(
        `/generation/packages?bundle_root=${encodedRoot}`,
      );
    },
    loadApprovalPackage(bundleRoot: string, packageId: string) {
      const encodedRoot = encodeURIComponent(bundleRoot);
      return request<PackageDetail>(
        `/generation/packages/${encodeURIComponent(packageId)}?bundle_root=${encodedRoot}`,
      );
    },
    updateApprovalState(
      bundleRoot: string,
      packageId: string,
      target: "proposal" | "stage",
      targetId: string,
      nextStatus: ApprovalStatus,
      reviewer: string | null = null,
      note: string | null = null,
    ) {
      return request<{ approval_state: PackageDetail["approval_state"] }>(
        `/generation/packages/${encodeURIComponent(packageId)}/approval`,
        {
          method: "POST",
          body: JSON.stringify({
            bundle_root: bundleRoot,
            target,
            target_id: targetId,
            next_status: nextStatus,
            reviewer,
            note,
          }),
        },
      );
    },
    previewProposal(bundleRoot: string, packageId: string, proposalId: string) {
      return request<ProposalPreviewResponse>(
        `/generation/packages/${encodeURIComponent(packageId)}/proposals/${encodeURIComponent(proposalId)}/preview`,
        {
          method: "POST",
          body: JSON.stringify({
            bundle_root: bundleRoot,
          }),
        },
      );
    },
    applyProposalPreview(bundleRoot: string, packageId: string, proposalId: string, previewId: string) {
      return request<{ approval_state: PackageDetail["approval_state"] }>(
        `/generation/packages/${encodeURIComponent(packageId)}/proposals/${encodeURIComponent(proposalId)}/apply`,
        {
          method: "POST",
          body: JSON.stringify({
            bundle_root: bundleRoot,
            preview_id: previewId,
          }),
        },
      );
    },
  };
}
