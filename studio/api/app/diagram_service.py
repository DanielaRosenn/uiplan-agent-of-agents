import json
from pathlib import Path

from pydantic import ValidationError

from app.schemas import DiagramData, DiagramEdge, DiagramNode, SaveDiagramResponse


DIAGRAM_FILENAME = "diagram.json"


DEFAULT_DIAGRAM = DiagramData(
    nodes=[
        DiagramNode(
            id="spec",
            title="Spec",
            kind="document",
            description="User goals, acceptance criteria, and UiPath scope.",
            x=48,
            y=64,
            source="spec.md",
        ),
        DiagramNode(
            id="tasks",
            title="Tasks",
            kind="document",
            description="Execution checklist generated from the plan.",
            x=48,
            y=300,
            source="tasks.md",
        ),
        DiagramNode(
            id="plan",
            title="Workflow Plan",
            kind="workflow",
            description="Build steps that Copilot can convert into implementation tasks.",
            x=292,
            y=180,
            source="plan.md",
        ),
        DiagramNode(
            id="skills",
            title="UiPath Skills",
            kind="skill",
            description="Relevant skill guidance for RPA, agents, platform, and HITL.",
            x=530,
            y=64,
            source=".cursor/skills",
        ),
        DiagramNode(
            id="library",
            title="Library Books",
            kind="library",
            description="Book sections used as grounded implementation context.",
            x=530,
            y=300,
            source="UiPath library",
        ),
        DiagramNode(
            id="review",
            title="Review Gates",
            kind="review",
            description="Findings, readiness, and preview-then-apply safeguards.",
            x=292,
            y=420,
            source="review service",
        ),
    ],
    edges=[
        DiagramEdge(id="spec-plan", from_="spec", to="plan", label="drives"),
        DiagramEdge(id="tasks-plan", from_="tasks", to="plan", label="tracks"),
        DiagramEdge(id="skills-plan", from_="skills", to="plan", label="guides"),
        DiagramEdge(id="library-plan", from_="library", to="plan", label="grounds"),
        DiagramEdge(id="plan-review", from_="plan", to="review", label="validated by"),
    ],
)


def _diagram_path(bundle_root: Path) -> Path:
    root = bundle_root.resolve()
    target = (root / DIAGRAM_FILENAME).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise PermissionError(f"Diagram path must stay within bundle root: {root}") from exc
    return target


def _diagram_payload(data: DiagramData) -> dict:
    if hasattr(data, "model_dump"):
        return data.model_dump(by_alias=True)
    return data.dict(by_alias=True)


def load_diagram(bundle_root: Path) -> tuple[DiagramData, Path | None, bool]:
    root = bundle_root.resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Bundle root not found: {root}")

    target = _diagram_path(root)
    if not target.exists():
        return DEFAULT_DIAGRAM, None, True

    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        return DiagramData(**payload), target, False
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(f"Invalid diagram file: {target}") from exc


def save_diagram(bundle_root: Path, data: DiagramData) -> SaveDiagramResponse:
    root = bundle_root.resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Bundle root not found: {root}")

    target = _diagram_path(root)
    content = json.dumps(_diagram_payload(data), indent=2) + "\n"
    target.write_text(content, encoding="utf-8")
    return SaveDiagramResponse(
        path=str(target),
        bytes_written=len(content.encode("utf-8")),
        nodes=data.nodes,
        edges=data.edges,
    )
