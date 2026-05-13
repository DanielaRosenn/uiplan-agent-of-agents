from __future__ import annotations

from fastapi import APIRouter

from app import library_service
from app.context_sources import get_context_sources
from app.project_graph.templates import (
    ProjectGraphTemplateResponse,
    create_starter_project_graph_template_response,
)
from app.schemas import (
    ContextSourcesResponse,
    LibraryContextRequest,
    LibraryContextResponse,
)

router = APIRouter()


@router.get(
    "/project-graph/templates/starter",
    response_model=ProjectGraphTemplateResponse,
    response_model_exclude_none=True,
)
def project_graph_starter_template() -> ProjectGraphTemplateResponse:
    return create_starter_project_graph_template_response()


@router.post("/agent/library-context", response_model=LibraryContextResponse)
def agent_library_context(payload: LibraryContextRequest) -> LibraryContextResponse:
    items = library_service.search_library_context(payload.query, payload.top_n)
    return LibraryContextResponse(query=payload.query, items=items)


@router.get("/agent/context-sources", response_model=ContextSourcesResponse)
def agent_context_sources() -> ContextSourcesResponse:
    return get_context_sources()


@router.get("/context/sources", response_model=ContextSourcesResponse)
def context_sources() -> ContextSourcesResponse:
    return get_context_sources()
