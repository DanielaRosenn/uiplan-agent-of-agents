from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.context_sources import sanitize_diagram_nodes
from app.generation_contracts.approval_state import apply_transition
from app.generation_contracts.command_registry import get_command_registry
from app.generation_contracts.models import (
    ApprovalPackageManifest,
    ApprovalStatus,
    CommandRegistry,
    GenerationGraph,
    StageId,
)
from app.generation_contracts.package_generation import generate_approval_package
from app.generation_contracts.storage import (
    list_packages,
    read_package_state,
    write_package_state,
)
from app.generation_service import (
    build_diagram_document_preview,
    build_preview_patch,
    enrich_generated_content,
)
from app.plan_writer import save_document
from app.schemas import (
    DiagramEdge,
    DiagramNode,
    PackageDetailResponse,
    PackageListResponse,
)
from app.state import (
    APPROVAL_PACKAGE_ONLY_POLICY,
    DOCUMENT_TARGETS,
    PENDING_GENERATION_PREVIEWS,
    content_hash,
    load_file_proposals,
    load_package_proposal,
    load_package_root,
    load_stage_manifests,
    proposal_state_or_404,
    read_target_for_proposal_preview,
    resolve_bundle_root,
)

router = APIRouter()


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


class GraphRefRequest(BaseModel):
    graph_id: str
    selected_node_id: str | None = None


class GenerateApprovalPackageApiRequest(BaseModel):
    bundle_root: str
    graph: GenerationGraph
    stages: list[StageId]
    reviewer: str | None = None
    graph_ref: GraphRefRequest | None = None
    write_policy: str


@router.post("/generate/section-preview")
def generate_section_preview(payload: GenerateSectionPreviewRequest) -> dict:
    if payload.document_name not in DOCUMENT_TARGETS:
        raise HTTPException(status_code=400, detail="Unsupported document name.")
    root = resolve_bundle_root(payload.bundle_root)
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
    PENDING_GENERATION_PREVIEWS.set(preview_id, {
        "path": str(target),
        "content": proposed_content,
        "base_hash": content_hash(before),
    })
    return {
        "preview_id": preview_id,
        "proposed_content": proposed_content,
        "diff": build_preview_patch(before, proposed_content, payload.document_name),
    }


@router.post("/generate/diagram-preview")
def generate_diagram_preview(payload: GenerateDiagramPreviewRequest) -> dict:
    if payload.document_name not in DOCUMENT_TARGETS:
        raise HTTPException(status_code=400, detail="Unsupported document name.")
    root = resolve_bundle_root(payload.bundle_root)
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
    PENDING_GENERATION_PREVIEWS.set(preview_id, {
        "path": str(target),
        "content": proposed_content,
        "base_hash": content_hash(before),
    })
    return {
        "preview_id": preview_id,
        "proposed_content": proposed_content,
        "diff": build_preview_patch(before, proposed_content, payload.document_name),
    }


@router.post("/generate/apply")
def generate_apply(payload: GenerateApplyRequest) -> dict:
    pending = PENDING_GENERATION_PREVIEWS.get(payload.preview_id)
    if pending is None:
        raise HTTPException(status_code=404, detail="Preview not found.")
    target = Path(pending["path"])
    try:
        current = target.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (IsADirectoryError, PermissionError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if content_hash(current) != pending["base_hash"]:
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
    PENDING_GENERATION_PREVIEWS.pop(payload.preview_id, None)
    return {
        "path": str(result.path),
        "backup_path": str(result.backup_path),
        "bytes_written": result.bytes_written,
    }


@router.get("/generation/command-registry", response_model=CommandRegistry)
def generation_command_registry() -> CommandRegistry:
    return get_command_registry()


@router.post("/generation/packages", response_model=ApprovalPackageManifest)
def generation_packages_create(
    payload: GenerateApprovalPackageApiRequest,
) -> ApprovalPackageManifest:
    if payload.write_policy != APPROVAL_PACKAGE_ONLY_POLICY:
        raise HTTPException(
            status_code=400,
            detail="Only approval_package_only write_policy is supported.",
        )
    root = resolve_bundle_root(payload.bundle_root)
    if not root.exists() or not root.is_dir():
        raise HTTPException(status_code=404, detail=f"Bundle root not found: {root}")
    effective_graph = payload.graph
    if payload.graph_ref is not None:
        created_from = payload.graph.created_from
        if payload.graph_ref.selected_node_id:
            created_from = f"{created_from}:selected_node:{payload.graph_ref.selected_node_id}"
        effective_graph = payload.graph.model_copy(
            update={
                "graph_id": payload.graph_ref.graph_id,
                "created_from": created_from,
            }
        )
    try:
        return generate_approval_package(
            bundle_root=root,
            graph=effective_graph,
            requested_stages=payload.stages,
            reviewer=payload.reviewer,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/generation/packages", response_model=PackageListResponse)
def generation_packages_list(bundle_root: str) -> PackageListResponse:
    root = resolve_bundle_root(bundle_root)
    return PackageListResponse(packages=list_packages(root))


@router.get("/generation/packages/{package_id}", response_model=PackageDetailResponse)
def generation_packages_detail(package_id: str, bundle_root: str) -> PackageDetailResponse:
    root = resolve_bundle_root(bundle_root)
    package_root = load_package_root(root, package_id)
    manifest_path = package_root / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail=f"Manifest not found for package: {package_id}")
    manifest = ApprovalPackageManifest.model_validate(
        json.loads(manifest_path.read_text(encoding="utf-8"))
    )
    approval_state = read_package_state(package_root)
    stages = load_stage_manifests(package_root)
    proposals = load_file_proposals(package_root)
    return PackageDetailResponse(
        manifest=manifest,
        approval_state=approval_state,
        stages=stages,
        proposals=proposals,
    )


@router.post("/generation/packages/{package_id}/approval")
def generation_packages_update_approval(
    package_id: str, payload: UpdateApprovalStateRequest
) -> dict:
    root = resolve_bundle_root(payload.bundle_root)
    package_root = load_package_root(root, package_id)
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


@router.post("/generation/packages/{package_id}/proposals/{proposal_id}/preview")
def generation_packages_preview_proposal(
    package_id: str, proposal_id: str, payload: ProposalPreviewRequest
) -> dict:
    root = resolve_bundle_root(payload.bundle_root)
    package_root = load_package_root(root, package_id)
    proposal = load_package_proposal(package_root, proposal_id)
    proposal_path = package_root / proposal.proposal_path
    if not proposal_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Proposal file not found: {proposal.proposal_path}"
        )
    proposed_content = proposal_path.read_text(encoding="utf-8")
    before, base_hash = read_target_for_proposal_preview(root, proposal.target_path)
    preview_id = uuid4().hex
    PENDING_GENERATION_PREVIEWS.set(preview_id, {
        "path": str((root / proposal.target_path).resolve()),
        "content": proposed_content,
        "base_hash": base_hash,
    })
    return {
        "preview_id": preview_id,
        "proposal_id": proposal.proposal_id,
        "target_path": proposal.target_path,
        "diff": build_preview_patch(before, proposed_content, proposal.target_path),
    }


@router.post("/generation/packages/{package_id}/proposals/{proposal_id}/apply")
def generation_packages_apply_proposal_preview(
    package_id: str, proposal_id: str, payload: ProposalApplyRequest
) -> dict:
    root = resolve_bundle_root(payload.bundle_root)
    package_root = load_package_root(root, package_id)
    proposal = load_package_proposal(package_root, proposal_id)
    current_state = read_package_state(package_root)
    proposal_state = proposal_state_or_404(current_state.proposals, proposal_id)
    if proposal_state.review_status != "approved":
        raise HTTPException(status_code=409, detail="Proposal must be approved before apply.")
    pending = PENDING_GENERATION_PREVIEWS.get(payload.preview_id)
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
        if content_hash(current_content) != pending["base_hash"]:
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
    PENDING_GENERATION_PREVIEWS.pop(payload.preview_id, None)
    return {
        "approval_state": next_state.model_dump(mode="json"),
        "applied": {
            "path": str(result.path),
            "backup_path": str(result.backup_path),
            "bytes_written": result.bytes_written,
        },
    }
