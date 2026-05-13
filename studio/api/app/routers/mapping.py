"""Copilot-first project mapping endpoint.

POST /mapping/map-folder
    Submit a source folder path and receive a Copilot-inferred project graph.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.explorer import _allowed_worktree_roots, _is_within, _repo_root
from app.explorer_config import load_config
from app.explorer_indexer import index_project
from app.copilot_runtime import COPILOT_SDK


router = APIRouter(prefix="/mapping", tags=["mapping"])


class MapFolderRequest(BaseModel):
    path: str


class MapFolderResponse(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    meta: dict[str, Any]
    source: str  # "copilot" or "deterministic-fallback"


@router.post("/map-folder", response_model=MapFolderResponse)
async def map_folder(request: MapFolderRequest) -> MapFolderResponse:
    """Map a source folder to a project graph using Copilot inference.
    
    Validates the folder, builds a compact source manifest, and asks Copilot
    to infer the project flow. Falls back to deterministic indexing if Copilot
    is unavailable, but returns an explicit error in the response so the UI
    can surface unavailability to the user.
    """
    # Validate source folder
    candidate = Path(request.path)
    if not candidate.is_absolute():
        candidate = (_repo_root() / candidate).resolve()
    else:
        candidate = candidate.resolve()
    
    if not candidate.is_dir():
        raise HTTPException(status_code=404, detail=f"Folder not found: {request.path}")
    
    allowed = _allowed_worktree_roots()
    if not any(_is_within(candidate, root) for root in allowed):
        raise HTTPException(
            status_code=403,
            detail=(
                "Folder path is not in the allow-list. Set UIPATH_EXPLORER_ROOTS "
                "(os.pathsep-separated absolute paths) to opt in."
            ),
        )
    
    # Build manifest using existing indexer
    try:
        config = load_config(candidate)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"explorer.yaml invalid: {exc}") from exc
    
    index = index_project(candidate, config)
    
    # Attempt Copilot mapping
    if COPILOT_SDK is None:
        # Copilot unavailable - return deterministic fallback with explicit error
        return MapFolderResponse(
            nodes=index.nodes[:50],  # Limit to prevent overwhelming UI
            edges=index.edges[:100],
            errors=[
                {
                    "nodeId": "mapping",
                    "severity": "error",
                    "message": "Copilot SDK unavailable. Install copilotkit>=0.1.88 and configure credentials.",
                }
            ],
            meta={
                "project_type": config.project.type,
                "files_scanned": index.files_scanned,
                "copilot_available": False,
            },
            source="deterministic-fallback",
        )
    
    # Build compact manifest for Copilot
    manifest_lines = []
    manifest_lines.append(f"Project: {config.project.name}")
    manifest_lines.append(f"Type: {config.project.type}")
    manifest_lines.append(f"Files scanned: {index.files_scanned}")
    manifest_lines.append("")
    manifest_lines.append("File structure:")
    for node in index.nodes[:100]:
        kind = node.get("kind", "")
        label = node.get("label", "")
        layer = node.get("layer", "")
        path = node.get("code", {}).get("path", "") if isinstance(node.get("code"), dict) else ""
        if path:
            manifest_lines.append(f"  [{layer}] {kind}: {label} @ {path}")
        else:
            manifest_lines.append(f"  [{layer}] {kind}: {label}")
    
    manifest = "\n".join(manifest_lines)
    
    # TODO: Wire Copilot action for project-flow inference
    # For now, return deterministic result with Copilot marker
    # Once CopilotKit action is wired, replace this with actual LLM inference
    
    return MapFolderResponse(
        nodes=index.nodes[:50],
        edges=index.edges[:100],
        errors=[
            {
                "nodeId": "mapping",
                "severity": "warn",
                "message": "Copilot project mapping not yet implemented. Showing deterministic index.",
            }
        ],
        meta={
            "project_type": config.project.type,
            "files_scanned": index.files_scanned,
            "copilot_available": True,
            "manifest_length": len(manifest),
        },
        source="deterministic-fallback",
    )
