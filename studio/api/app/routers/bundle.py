from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.plan_loader import load_bundle
from app.plan_writer import save_document
from app.state import (
    DOCUMENT_TARGETS,
    LEGACY_DIRECT_SAVE_POLICY,
    resolve_bundle_root,
)

router = APIRouter()


class SaveDocumentRequest(BaseModel):
    bundle_root: str
    document_name: str
    content: str
    legacy_internal: bool = False
    write_policy: str | None = None


@router.get("/bundle/load")
def bundle_load(bundle_root: str) -> dict:
    root = resolve_bundle_root(bundle_root)
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


@router.post("/bundle/save")
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
    root = resolve_bundle_root(payload.bundle_root)
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
