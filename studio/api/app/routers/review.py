from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.review_service import run_review

router = APIRouter()


class ReviewRunRequest(BaseModel):
    spec: str
    plan: str
    tasks: str
    stage: str = "all"
    gate_ids: list[str] = Field(default_factory=list)
    slug: str | None = None


@router.post("/review/run")
def review_run(payload: ReviewRunRequest) -> dict:
    return run_review(
        spec=payload.spec,
        plan=payload.plan,
        tasks=payload.tasks,
        stage=payload.stage,
        gate_ids=payload.gate_ids,
        slug=payload.slug,
    )


@router.post("/lifecycle/readiness")
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
