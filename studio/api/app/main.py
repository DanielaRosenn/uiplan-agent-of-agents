"""UiPlan Studio API composition root.

Route handlers live in ``app/routers/``. This module wires the FastAPI app,
CORS, the CopilotKit submodule, and the explorer router, and owns the
``/health`` endpoint.

Backwards-compatibility: some tests import ``app.main._PENDING_GENERATION_PREVIEWS``,
``app.main.LEGACY_DIRECT_SAVE_POLICY``, ``app.main.PLANS_ROOT``, etc. directly.
We re-export those names from :mod:`app.state` here so existing tests keep
working without modification.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.copilot_runtime import register_copilot_runtime
from app.explorer import router as explorer_router
from app.routers.bundle import router as bundle_router
from app.routers.context import router as context_router
from app.routers.copilotkit import router as copilotkit_router
from app.routers.diagram import router as diagram_router
from app.routers.generation import router as generation_router
from app.routers.mapping import router as mapping_router
from app.routers.review import router as review_router
from app.routers.fixtures import router as fixtures_router
from app.schemas import HealthResponse
from app.security import LocalOnlyMiddleware
from app.state import (
    APPROVAL_PACKAGE_ONLY_POLICY,
    DOCUMENT_TARGETS,
    LEGACY_DIRECT_SAVE_POLICY,
    PENDING_GENERATION_PREVIEWS,
    PLANS_ROOT,
    content_hash as _content_hash,
    resolve_bundle_root as _resolve_bundle_root,
)

# Backwards-compat aliases for tests that reference these names through ``app.main``.
_PENDING_GENERATION_PREVIEWS = PENDING_GENERATION_PREVIEWS

__all__ = [
    "app",
    "APPROVAL_PACKAGE_ONLY_POLICY",
    "DOCUMENT_TARGETS",
    "LEGACY_DIRECT_SAVE_POLICY",
    "PLANS_ROOT",
    "_PENDING_GENERATION_PREVIEWS",
    "_content_hash",
    "_resolve_bundle_root",
]


app = FastAPI(title="UiPlan Studio API")
app.add_middleware(LocalOnlyMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_copilot_runtime(app)
app.include_router(explorer_router)
app.include_router(bundle_router)
app.include_router(diagram_router)
app.include_router(review_router)
app.include_router(context_router)
app.include_router(generation_router)
app.include_router(mapping_router)
app.include_router(fixtures_router)
app.include_router(copilotkit_router)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        routes=[
            "/bundle/load",
            "/diagram/load",
            "/diagram/save",
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
            "/project-graph/templates/starter",
            "/copilotkit",
            "/copilotkit/info",
            "/copilotkit/runtime",
        ],
        metadata={
            "network_policy": "local-only",
            "preview_store": (
                "single-process bounded in-memory store; preview ids are not durable across "
                "restarts or multi-worker deployments"
            ),
        },
    )
