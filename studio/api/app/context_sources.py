from __future__ import annotations

import os
from pathlib import Path

from app.schemas import ContextSource, ContextSourceCategory, ContextSourcesResponse, DiagramNode


_REPO_ROOT_ENV = os.environ.get("UIPLAN_REPO_ROOT")
REPO_ROOT: Path = (
    Path(_REPO_ROOT_ENV).resolve() if _REPO_ROOT_ENV
    else Path(__file__).resolve().parents[3]
)


def _skill_source(
    skill_id: str,
    description: str,
) -> ContextSource:
    skill_path = REPO_ROOT / ".cursor" / "skills" / skill_id / "SKILL.md"
    return ContextSource(
        id=skill_id,
        title=skill_id,
        kind="skill",
        category="skills",
        description=description,
        source=f".cursor/skills/{skill_id}",
        available=skill_path.exists(),
    )


def get_context_sources() -> ContextSourcesResponse:
    return ContextSourcesResponse(
        categories=[
            ContextSourceCategory(
                id="skills",
                title="Skills",
                description="Curated UiPath builder skills available as diagram context.",
                sources=[
                    _skill_source("uipath-rpa", "Build C# coded workflows, XAML, and hybrid RPA projects."),
                    _skill_source("uipath-agents", "Design, run, evaluate, and deploy UiPath coded agents."),
                    _skill_source("uipath-platform", "Use Orchestrator, packages, assets, queues, and solutions."),
                    _skill_source(
                        "uipath-human-in-the-loop",
                        "Add Action Center approvals, escalations, and validation gates.",
                    ),
                    _skill_source(
                        "uipath-solution-design",
                        "Turn PDD inputs into implementation-ready UiPath solution designs.",
                    ),
                    _skill_source(
                        "uiplan-full",
                        "Use the UiPlan authoring workflow for spec, plan, tasks, and review loops.",
                    ),
                ],
            ),
            ContextSourceCategory(
                id="library",
                title="Library Books",
                description="Lightweight book identifiers; detailed retrieval stays in library search.",
                sources=[
                    ContextSource(
                        id="uipath-cli",
                        title="UiPath CLI docs",
                        kind="library",
                        category="library",
                        description="Command syntax and build-loop references for UiPath CLIs.",
                        source="uipath-cli",
                    ),
                    ContextSource(
                        id="uipath-workflows",
                        title="UiPath workflow docs",
                        kind="library",
                        category="library",
                        description="End-to-end workflow guidance for RPA, agents, apps, and solutions.",
                        source="uipath-workflows",
                    ),
                    ContextSource(
                        id="uipath-docs",
                        title="UiPath product docs",
                        kind="library",
                        category="library",
                        description="Product documentation indexed for targeted library-context search.",
                        source="uipath-docs",
                    ),
                ],
            ),
            ContextSourceCategory(
                id="documents",
                title="Documents",
                description="Local plan bundle documents used by the builder.",
                sources=[
                    ContextSource(
                        id="spec.md",
                        title="Spec",
                        kind="document",
                        category="documents",
                        description="User goals, acceptance criteria, and UiPath scope.",
                        source="spec.md",
                    ),
                    ContextSource(
                        id="plan.md",
                        title="Plan",
                        kind="workflow",
                        category="documents",
                        description="Implementation plan that drives the diagram and task breakdown.",
                        source="plan.md",
                    ),
                    ContextSource(
                        id="tasks.md",
                        title="Tasks",
                        kind="document",
                        category="documents",
                        description="Execution checklist and progress tracking for the rebuild.",
                        source="tasks.md",
                    ),
                ],
            ),
            ContextSourceCategory(
                id="review",
                title="Review Gates",
                description="Local gates that keep generated plan changes reviewable.",
                sources=[
                    ContextSource(
                        id="review-run",
                        title="Review findings",
                        kind="review",
                        category="review",
                        description="Run acceptance checks and group findings by document.",
                        source="/review/run",
                    ),
                    ContextSource(
                        id="lifecycle-readiness",
                        title="Lifecycle readiness",
                        kind="review",
                        category="review",
                        description="Summarize blocking errors before applying generated changes.",
                        source="/lifecycle/readiness",
                    ),
                    ContextSource(
                        id="preview-apply",
                        title="Preview and apply",
                        kind="review",
                        category="review",
                        description="Generate diffs, keep previews hash-guarded, then apply intentionally.",
                        source="/generate/section-preview",
                    ),
                ],
            ),
        ]
    )


def get_context_source_index() -> dict[str, ContextSource]:
    index: dict[str, ContextSource] = {}
    for category in get_context_sources().categories:
        for source in category.sources:
            index[source.id] = source
            index[source.source] = source
    return index


def is_unavailable_curated_source(identifier: str | None) -> bool:
    if not identifier:
        return False
    source = get_context_source_index().get(identifier)
    return source is not None and source.available is False


def sanitize_diagram_nodes(nodes: list[DiagramNode]) -> list[DiagramNode]:
    sanitized: list[DiagramNode] = []
    for node in nodes:
        if is_unavailable_curated_source(node.source) or is_unavailable_curated_source(node.id):
            if hasattr(node, "model_copy"):
                sanitized.append(node.model_copy(update={"source": None}))
            else:
                sanitized.append(node.copy(update={"source": None}))
            continue
        sanitized.append(node)
    return sanitized
