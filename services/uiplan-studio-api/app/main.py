import hashlib
import json
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.context_sources import get_context_sources, sanitize_diagram_nodes
from app.copilot_runtime import (
    copilot_generate_response_payload,
    copilot_info_payload,
    register_copilot_runtime,
)
from app.diagram_service import load_diagram, save_diagram
from app.generation_contracts.models import (
    ApprovalPackageManifest,
    ApprovalStatus,
    CommandRegistry,
    FileProposal,
    ProposalState,
    StageManifest,
)
from app.generation_contracts.approval_state import apply_transition
from app.generation_contracts.command_registry import get_command_registry
from app.generation_contracts.package_generation import generate_approval_package
from app.generation_contracts.storage import list_packages, read_package_state, write_package_state
from app.generation_service import (
    build_diagram_document_preview,
    build_preview_patch,
    enrich_generated_content,
)
from app.graph_indexer import index_workspace_sources
from app.library_service import search_library_context
from app.project_graph.templates import (
    ProjectGraphTemplateResponse,
    create_starter_project_graph_template_response,
)
from app.schemas import (
    AssistantChatRequest,
    AssistantChatResponse,
    DiagramEdge,
    DiagramNode,
    DiagramData,
    GraphIndexEdge,
    GraphIndexNode,
    GraphIndexResponse,
    GenerateApprovalPackageRequest,
    LoadDiagramResponse,
    ContextSourcesResponse,
    HealthResponse,
    PackageDetailResponse,
    PackageListResponse,
    LibraryContextRequest,
    LibraryContextResponse,
    SaveDiagramRequest,
    SaveDiagramResponse,
)
from app.plan_loader import load_bundle
from app.plan_writer import save_document
from app.review_service import run_review

app = FastAPI(title="UiPlan Studio API")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_copilot_runtime(app)

PLANS_ROOT = (Path(__file__).resolve().parents[3] / ".cursor" / "plans").resolve()
# Preview payloads are intentionally process-local for Task 2; they are not shared across
# workers or persisted across restarts.
_PENDING_GENERATION_PREVIEWS: dict[str, dict[str, str]] = {}
DOCUMENT_TARGETS = {"spec.md", "plan.md", "tasks.md"}
LEGACY_DIRECT_SAVE_POLICY = "legacy_internal_direct_write"


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _resolve_bundle_root(bundle_root: str) -> Path:
    requested = Path(bundle_root)
    if requested.is_absolute():
        root = requested.resolve()
    else:
        parts = requested.parts
        if len(parts) >= 2 and parts[0] == ".cursor" and parts[1] == "plans":
            root = (PLANS_ROOT.parent.parent / requested).resolve()
        elif parts and parts[0] == "plans":
            root = (PLANS_ROOT.parent / requested).resolve()
        else:
            root = (PLANS_ROOT / requested).resolve()
    try:
        root.relative_to(PLANS_ROOT)
    except ValueError as exc:
        raise HTTPException(
            status_code=403,
            detail=f"bundle_root must be under {PLANS_ROOT}",
        ) from exc
    return root


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        routes=[
            "/bundle/load",
            "/diagram/load",
            "/diagram/save",
            "/graph/index",
            "/review/run",
            "/lifecycle/readiness",
            "/generate/section-preview",
            "/generate/diagram-preview",
            "/generate/apply",
            "/generation/packages",
            "/generation/packages/{package_id}",
            "/generation/packages/{package_id}/approval",
            "/generation/packages/{package_id}/proposals/{proposal_id}/preview",
            "/generation/packages/{package_id}/proposals/{proposal_id}/apply",
            "/generation/command-registry",
            "/context/sources",
            "/agent/context-sources",
            "/agent/library-context",
            "/agent/chat",
            "/project-graph/templates/starter",
            "/copilotkit",
            "/copilotkit/info",
            "/copilotkit/runtime",
        ],
        metadata={
            "preview_store": (
                "single-process in-memory store; preview ids are not durable across restarts "
                "or multi-worker deployments"
            )
        },
    )


@app.get(
    "/project-graph/templates/starter",
    response_model=ProjectGraphTemplateResponse,
    response_model_exclude_none=True,
)
def project_graph_starter_template() -> ProjectGraphTemplateResponse:
    return create_starter_project_graph_template_response()


class SaveDocumentRequest(BaseModel):
    bundle_root: str
    document_name: str
    content: str
    legacy_internal: bool = False
    write_policy: str | None = None


class ReviewRunRequest(BaseModel):
    spec: str
    plan: str
    tasks: str
    stage: str = "all"
    gate_ids: list[str] = Field(default_factory=list)
    slug: str | None = None


class GenerateSectionPreviewRequest(BaseModel):
    bundle_root: str
    document_name: str
    proposed_content: str
    library_context: list[dict[str, str | int | None]] = Field(default_factory=list)


class GenerateDiagramPreviewRequest(BaseModel):
    bundle_root: str
    document_name: str
    nodes: list[DiagramNode] = Field(default_factory=list)
    edges: list[DiagramEdge] = Field(default_factory=list)
    focus: str | None = None
    context: list[dict[str, str | int | None]] = Field(default_factory=list)


class GenerateApplyRequest(BaseModel):
    preview_id: str


class UpdateApprovalStateRequest(BaseModel):
    bundle_root: str
    target: str
    target_id: str
    next_status: ApprovalStatus
    reviewer: str | None = None
    note: str | None = None


class ProposalPreviewRequest(BaseModel):
    bundle_root: str


class ProposalApplyRequest(BaseModel):
    bundle_root: str
    preview_id: str


@app.get("/bundle/load")
def bundle_load(bundle_root: str) -> dict:
    root = _resolve_bundle_root(bundle_root)
    try:
        bundle = load_bundle(root)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (IsADirectoryError, PermissionError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "slug": bundle.slug,
        "status": bundle.status,
        "root": str(bundle.root),
        "documents": bundle.documents,
    }


@app.post("/bundle/save")
def bundle_save(payload: SaveDocumentRequest) -> dict:
    if (
        payload.legacy_internal is not True
        or payload.write_policy != LEGACY_DIRECT_SAVE_POLICY
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "/bundle/save is a legacy internal endpoint. "
                "Use /generate/section-preview followed by /generate/apply for document edits."
            ),
        )
    if payload.document_name not in DOCUMENT_TARGETS:
        raise HTTPException(status_code=400, detail="Unsupported document name.")
    root = _resolve_bundle_root(payload.bundle_root)
    if not root.exists() or not root.is_dir():
        raise HTTPException(status_code=404, detail=f"Bundle root not found: {root}")
    target = root / payload.document_name
    try:
        result = save_document(target, payload.content)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (IsADirectoryError, PermissionError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "path": str(result.path),
        "backup_path": str(result.backup_path),
        "bytes_written": result.bytes_written,
    }


@app.get("/diagram/load", response_model=LoadDiagramResponse)
def diagram_load(bundle_root: str) -> LoadDiagramResponse:
    root = _resolve_bundle_root(bundle_root)
    try:
        diagram, path, defaulted = load_diagram(root)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (IsADirectoryError, PermissionError, UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return LoadDiagramResponse(
        nodes=diagram.nodes,
        edges=diagram.edges,
        path=str(path) if path is not None else None,
        defaulted=defaulted,
    )


@app.post("/diagram/save", response_model=SaveDiagramResponse)
def diagram_save(payload: SaveDiagramRequest) -> SaveDiagramResponse:
    root = _resolve_bundle_root(payload.bundle_root)
    try:
        return save_diagram(
            root,
            DiagramData(nodes=sanitize_diagram_nodes(payload.nodes), edges=payload.edges),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (IsADirectoryError, PermissionError, UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/graph/index", response_model=GraphIndexResponse)
def graph_index(bundle_root: str) -> GraphIndexResponse:
    root = _resolve_bundle_root(bundle_root)
    if not root.exists() or not root.is_dir():
        raise HTTPException(status_code=404, detail=f"Bundle root not found: {root}")
    workspace = index_workspace_sources(root)
    return GraphIndexResponse(
        version=workspace.version,
        nodes=[
            GraphIndexNode(id=node.id, type=node.type, title=node.title, summary=node.summary)
            for node in workspace.nodes
        ],
        edges=[
            GraphIndexEdge(
                id=edge.id,
                type=edge.type,
                source=edge.source,
                target=edge.target,
                label=edge.label,
            )
            for edge in workspace.edges
        ],
    )


@app.post("/review/run")
def review_run(payload: ReviewRunRequest) -> dict:
    return run_review(
        spec=payload.spec,
        plan=payload.plan,
        tasks=payload.tasks,
        stage=payload.stage,
        gate_ids=payload.gate_ids,
        slug=payload.slug,
    )


@app.post("/lifecycle/readiness")
def lifecycle_readiness(payload: ReviewRunRequest) -> dict:
    review = run_review(
        spec=payload.spec,
        plan=payload.plan,
        tasks=payload.tasks,
        stage=payload.stage,
        gate_ids=payload.gate_ids,
        slug=payload.slug,
    )
    findings = review.get("findings", [])
    error_count = sum(
        1 for finding in findings if str(finding.get("severity", "")).lower() == "error"
    )
    return {
        "status": "ready" if error_count == 0 else "blocked",
        "acceptance_ready": review.get("acceptance_ready", False),
        "error_count": error_count,
        "findings_by_document": review.get("findings_by_document", {}),
    }


@app.post("/generate/section-preview")
def generate_section_preview(payload: GenerateSectionPreviewRequest) -> dict:
    if payload.document_name not in DOCUMENT_TARGETS:
        raise HTTPException(status_code=400, detail="Unsupported document name.")
    root = _resolve_bundle_root(payload.bundle_root)
    if not root.exists() or not root.is_dir():
        raise HTTPException(status_code=404, detail=f"Bundle root not found: {root}")
    target = root / payload.document_name
    try:
        before = target.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (IsADirectoryError, PermissionError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    proposed_content = enrich_generated_content(
        payload.proposed_content,
        payload.library_context,
    )
    preview_id = uuid4().hex
    _PENDING_GENERATION_PREVIEWS[preview_id] = {
        "path": str(target),
        "content": proposed_content,
        "base_hash": _content_hash(before),
    }
    return {
        "preview_id": preview_id,
        "proposed_content": proposed_content,
        "diff": build_preview_patch(before, proposed_content, payload.document_name),
    }


@app.post("/generate/diagram-preview")
def generate_diagram_preview(payload: GenerateDiagramPreviewRequest) -> dict:
    if payload.document_name not in DOCUMENT_TARGETS:
        raise HTTPException(status_code=400, detail="Unsupported document name.")
    root = _resolve_bundle_root(payload.bundle_root)
    if not root.exists() or not root.is_dir():
        raise HTTPException(status_code=404, detail=f"Bundle root not found: {root}")
    target = root / payload.document_name
    try:
        before = target.read_text(encoding="utf-8")
        proposed_content = build_diagram_document_preview(
            existing_content=before,
            document_name=payload.document_name,
            nodes=sanitize_diagram_nodes(payload.nodes),
            edges=payload.edges,
            focus=payload.focus,
            context=payload.context,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (IsADirectoryError, PermissionError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    preview_id = uuid4().hex
    _PENDING_GENERATION_PREVIEWS[preview_id] = {
        "path": str(target),
        "content": proposed_content,
        "base_hash": _content_hash(before),
    }
    return {
        "preview_id": preview_id,
        "proposed_content": proposed_content,
        "diff": build_preview_patch(before, proposed_content, payload.document_name),
    }


@app.post("/generate/apply")
def generate_apply(payload: GenerateApplyRequest) -> dict:
    pending = _PENDING_GENERATION_PREVIEWS.get(payload.preview_id)
    if pending is None:
        raise HTTPException(status_code=404, detail="Preview not found.")
    target = Path(pending["path"])
    try:
        current = target.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (IsADirectoryError, PermissionError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if _content_hash(current) != pending["base_hash"]:
        raise HTTPException(
            status_code=409,
            detail="Document changed since preview was created.",
        )
    try:
        result = save_document(target, pending["content"])
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (IsADirectoryError, PermissionError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _PENDING_GENERATION_PREVIEWS.pop(payload.preview_id, None)
    return {
        "path": str(result.path),
        "backup_path": str(result.backup_path),
        "bytes_written": result.bytes_written,
    }


@app.get("/generation/command-registry", response_model=CommandRegistry)
def generation_command_registry() -> CommandRegistry:
    return get_command_registry()


@app.post("/generation/packages", response_model=ApprovalPackageManifest)
def generation_packages_create(payload: GenerateApprovalPackageRequest) -> ApprovalPackageManifest:
    root = _resolve_bundle_root(payload.bundle_root)
    if not root.exists() or not root.is_dir():
        raise HTTPException(status_code=404, detail=f"Bundle root not found: {root}")
    try:
        return generate_approval_package(
            bundle_root=root,
            graph=payload.graph,
            requested_stages=payload.stages,
            reviewer=payload.reviewer,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/generation/packages", response_model=PackageListResponse)
def generation_packages_list(bundle_root: str) -> PackageListResponse:
    root = _resolve_bundle_root(bundle_root)
    return PackageListResponse(packages=list_packages(root))


def _load_stage_manifests(package_root: Path) -> list[StageManifest]:
    stages: list[StageManifest] = []
    for stage_manifest_path in sorted(package_root.glob("stages/*/stage.manifest.json")):
        payload = json.loads(stage_manifest_path.read_text(encoding="utf-8"))
        stages.append(StageManifest.model_validate(payload))
    return stages


def _load_file_proposals(package_root: Path) -> list[FileProposal]:
    proposals: list[FileProposal] = []
    for proposal_manifest_path in sorted(package_root.glob("stages/*/proposals/*.proposal.json")):
        payload = json.loads(proposal_manifest_path.read_text(encoding="utf-8"))
        proposals.append(FileProposal.model_validate(payload))
    return proposals


def _load_package_root(bundle_root: Path, package_id: str) -> Path:
    package_root = bundle_root / ".uiplan" / "generation" / "packages" / package_id
    if not package_root.exists():
        raise HTTPException(status_code=404, detail=f"Package not found: {package_id}")
    return package_root


def _load_package_proposal(package_root: Path, proposal_id: str) -> FileProposal:
    proposals = _load_file_proposals(package_root)
    proposal = next((candidate for candidate in proposals if candidate.proposal_id == proposal_id), None)
    if proposal is None:
        raise HTTPException(status_code=404, detail=f"Proposal not found: {proposal_id}")
    return proposal


def _read_target_for_proposal_preview(bundle_root: Path, target_path: str) -> tuple[str, str]:
    target = (bundle_root / target_path).resolve()
    try:
        target.relative_to(bundle_root.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="proposal target path escapes bundle root") from exc
    if target.exists():
        try:
            before = target.read_text(encoding="utf-8")
        except (IsADirectoryError, PermissionError, UnicodeDecodeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return before, _content_hash(before)
    return "", "__missing__"


def _proposal_state_or_404(approval_state: dict[str, ProposalState], proposal_id: str) -> ProposalState:
    proposal_state = approval_state.get(proposal_id)
    if proposal_state is None:
        raise HTTPException(status_code=404, detail=f"Proposal state not found: {proposal_id}")
    return proposal_state


@app.get("/generation/packages/{package_id}", response_model=PackageDetailResponse)
def generation_packages_detail(package_id: str, bundle_root: str) -> PackageDetailResponse:
    root = _resolve_bundle_root(bundle_root)
    package_root = _load_package_root(root, package_id)
    manifest_path = package_root / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail=f"Manifest not found for package: {package_id}")
    manifest = ApprovalPackageManifest.model_validate(
        json.loads(manifest_path.read_text(encoding="utf-8"))
    )
    approval_state = read_package_state(package_root)
    stages = _load_stage_manifests(package_root)
    proposals = _load_file_proposals(package_root)
    return PackageDetailResponse(
        manifest=manifest,
        approval_state=approval_state,
        stages=stages,
        proposals=proposals,
    )


@app.post("/generation/packages/{package_id}/approval")
def generation_packages_update_approval(
    package_id: str, payload: UpdateApprovalStateRequest
) -> dict:
    root = _resolve_bundle_root(payload.bundle_root)
    package_root = _load_package_root(root, package_id)
    current_state = read_package_state(package_root)
    try:
        next_state = apply_transition(
            current_state,
            target=payload.target,
            target_id=payload.target_id,
            next_status=payload.next_status,
            reviewer=payload.reviewer,
            note=payload.note,
        )
        write_package_state(
            package_root,
            next_state,
            expected_updated_at=current_state.updated_at,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 409 if "stale approval state write" in detail else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return {"approval_state": next_state.model_dump(mode="json")}


@app.post("/generation/packages/{package_id}/proposals/{proposal_id}/preview")
def generation_packages_preview_proposal(
    package_id: str, proposal_id: str, payload: ProposalPreviewRequest
) -> dict:
    root = _resolve_bundle_root(payload.bundle_root)
    package_root = _load_package_root(root, package_id)
    proposal = _load_package_proposal(package_root, proposal_id)
    proposal_path = package_root / proposal.proposal_path
    if not proposal_path.exists():
        raise HTTPException(status_code=404, detail=f"Proposal file not found: {proposal.proposal_path}")
    proposed_content = proposal_path.read_text(encoding="utf-8")
    before, base_hash = _read_target_for_proposal_preview(root, proposal.target_path)
    preview_id = uuid4().hex
    _PENDING_GENERATION_PREVIEWS[preview_id] = {
        "path": str((root / proposal.target_path).resolve()),
        "content": proposed_content,
        "base_hash": base_hash,
    }
    return {
        "preview_id": preview_id,
        "proposal_id": proposal.proposal_id,
        "target_path": proposal.target_path,
        "diff": build_preview_patch(before, proposed_content, proposal.target_path),
    }


@app.post("/generation/packages/{package_id}/proposals/{proposal_id}/apply")
def generation_packages_apply_proposal_preview(
    package_id: str, proposal_id: str, payload: ProposalApplyRequest
) -> dict:
    root = _resolve_bundle_root(payload.bundle_root)
    package_root = _load_package_root(root, package_id)
    proposal = _load_package_proposal(package_root, proposal_id)
    current_state = read_package_state(package_root)
    proposal_state = _proposal_state_or_404(current_state.proposals, proposal_id)
    if proposal_state.review_status != "approved":
        raise HTTPException(status_code=409, detail="Proposal must be approved before apply.")
    pending = _PENDING_GENERATION_PREVIEWS.get(payload.preview_id)
    if pending is None:
        raise HTTPException(status_code=404, detail="Preview not found.")
    target_path = (root / proposal.target_path).resolve()
    if Path(pending["path"]) != target_path:
        raise HTTPException(status_code=409, detail="Preview does not match proposal target path.")

    if pending["base_hash"] == "__missing__":
        if target_path.exists():
            raise HTTPException(status_code=409, detail="Target changed since preview was created.")
    else:
        try:
            current_content = target_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise HTTPException(status_code=409, detail="Target deleted since preview was created.") from exc
        except (IsADirectoryError, PermissionError, UnicodeDecodeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if _content_hash(current_content) != pending["base_hash"]:
            raise HTTPException(status_code=409, detail="Target changed since preview was created.")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    result = save_document(target_path, pending["content"])
    try:
        next_state = apply_transition(
            current_state,
            target="proposal",
            target_id=proposal_id,
            next_status="applied",
            reviewer=proposal_state.reviewer,
            note=proposal_state.reviewer_notes,
            preview_id=payload.preview_id,
        )
        write_package_state(
            package_root,
            next_state,
            expected_updated_at=current_state.updated_at,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 409 if "stale approval state write" in detail else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    _PENDING_GENERATION_PREVIEWS.pop(payload.preview_id, None)
    return {
        "approval_state": next_state.model_dump(mode="json"),
        "applied": {
            "path": str(result.path),
            "backup_path": str(result.backup_path),
            "bytes_written": result.bytes_written,
        },
    }


@app.post("/agent/library-context", response_model=LibraryContextResponse)
def agent_library_context(payload: LibraryContextRequest) -> LibraryContextResponse:
    items = search_library_context(payload.query, payload.top_n)
    return LibraryContextResponse(query=payload.query, items=items)


@app.get("/agent/context-sources", response_model=ContextSourcesResponse)
def agent_context_sources() -> ContextSourcesResponse:
    return get_context_sources()


@app.get("/context/sources", response_model=ContextSourcesResponse)
def context_sources() -> ContextSourcesResponse:
    return get_context_sources()


@app.post("/agent/chat", response_model=AssistantChatResponse)
def agent_chat(payload: AssistantChatRequest) -> AssistantChatResponse:
    normalized = payload.message.lower()
    selected = next(
        (node for node in payload.nodes if node.id == payload.selected_node_id),
        None,
    )
    focus = f" focused on {selected.title}" if selected else ""
    suggested_nodes: list[DiagramNode] = []

    if "skill" in normalized:
        suggested_nodes.append(
            DiagramNode(
                id="skill-uipath-platform",
                title="uipath-platform",
                kind="skill",
                description="Use for Orchestrator, packages, assets, queues, and solution lifecycle.",
                x=760,
                y=92,
                source=".cursor/skills/uipath-platform",
            )
        )

    if "library" in normalized or "book" in normalized:
        suggested_nodes.append(
            DiagramNode(
                id="library-uipath-cli-agent-deploy",
                title="Agent deploy docs",
                kind="library",
                description="Book context for packaging, publishing, and deploying coded agents.",
                x=760,
                y=308,
                source="uipath-cli/03-agent/deploy",
            )
        )

    if "hitl" in normalized or "human" in normalized or "approval" in normalized:
        suggested_nodes.append(
            DiagramNode(
                id="workflow-hitl-approval",
                title="HITL approval",
                kind="workflow",
                description="Human review gate before writes, publish, deploy, or escalation.",
                x=76,
                y=396,
                source="uipath-human-in-the-loop",
            )
        )

    if suggested_nodes:
        message = (
            f"I added suggested diagram context{focus}. Review the new nodes, then generate "
            "a preview when you want those ideas reflected in the plan documents."
        )
    else:
        message = (
            f"I can help shape the UiPath diagram{focus}. Ask for skills, library books, "
            "HITL gates, deployment flow, review gates, or plan updates."
        )

    return AssistantChatResponse(message=message, suggested_nodes=suggested_nodes)


@app.get("/copilotkit/info")
def copilotkit_info() -> dict:
    return copilot_info_payload()


@app.get("/copilotkit")
def copilotkit_runtime_info() -> dict:
    return copilotkit_info()


@app.post("/copilotkit")
async def copilotkit_runtime(request: Request) -> dict:
    body = await request.json()
    method = str(body.get("method", ""))
    operation = str(body.get("operationName", ""))

    if method == "info":
        return copilotkit_info()

    if operation in {"AvailableAgents", "availableAgents"}:
        agents = copilotkit_info().get("agents", {})
        available_agents = (
            [
                {"id": agent_id, "name": agent_id, **metadata}
                for agent_id, metadata in agents.items()
            ]
            if isinstance(agents, dict)
            else agents
        )
        return {"data": {"availableAgents": {"agents": available_agents}}}

    if operation in {"LoadAgentState", "loadAgentState"}:
        variables = body.get("variables", {})
        data = variables.get("data", {}) if isinstance(variables, dict) else {}
        thread_id = body.get("threadId") or data.get("threadId") or "local"
        return {
            "data": {
                "loadAgentState": {
                    "threadId": thread_id,
                    "threadExists": False,
                    "state": {},
                    "messages": [],
                }
            }
        }

    if operation in {"GenerateCopilotResponse", "generateCopilotResponse"}:
        return {
            "data": {
                "generateCopilotResponse": copilot_generate_response_payload()
            }
        }

    return {"data": {}}
