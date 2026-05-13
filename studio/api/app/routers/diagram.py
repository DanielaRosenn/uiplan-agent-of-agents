from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.context_sources import sanitize_diagram_nodes
from app.diagram_service import load_diagram, save_diagram
from app.schemas import (
    DiagramData,
    LoadDiagramResponse,
    SaveDiagramRequest,
    SaveDiagramResponse,
)
from app.state import resolve_bundle_root

router = APIRouter()


@router.get("/diagram/load", response_model=LoadDiagramResponse)
def diagram_load(bundle_root: str) -> LoadDiagramResponse:
    root = resolve_bundle_root(bundle_root)
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


@router.post("/diagram/save", response_model=SaveDiagramResponse)
def diagram_save(payload: SaveDiagramRequest) -> SaveDiagramResponse:
    root = resolve_bundle_root(payload.bundle_root)
    try:
        return save_diagram(
            root,
            DiagramData(nodes=sanitize_diagram_nodes(payload.nodes), edges=payload.edges),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (IsADirectoryError, PermissionError, UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
