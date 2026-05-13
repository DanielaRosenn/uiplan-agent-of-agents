from app.generation_service import (
    ESCAPED_GENERATED_SECTION_END,
    ESCAPED_GENERATED_SECTION_START,
    GENERATED_SECTION_END,
    GENERATED_SECTION_START,
    build_diagram_document_preview,
    build_preview_patch,
    enrich_generated_content,
)
from app.schemas import DiagramEdge, DiagramNode


def test_build_preview_patch_returns_unified_diff() -> None:
    before = "# Spec\nOld\n"
    after = "# Spec\nNew\n"

    patch = build_preview_patch(before, after, "spec.md")

    assert "--- spec.md" in patch
    assert "+++ spec.md" in patch
    assert "-Old" in patch
    assert "+New" in patch


def test_enrich_generated_content_appends_citation_block() -> None:
    content = "# Spec\nBody\n"
    enriched = enrich_generated_content(
        content,
        [
            {
                "book_id": "uipath-cli",
                "chapter_id": "03-agent",
                "section_id": "deploy",
                "score": 9,
            }
        ],
    )
    assert "generated_with_library_context" in enriched
    assert "- uipath-cli/03-agent/deploy" in enriched


def test_enrich_generated_content_returns_original_without_context() -> None:
    content = "# Plan\nBody\n"
    assert enrich_generated_content(content, []) == content


def test_build_diagram_document_preview_generates_spec_section() -> None:
    content = build_diagram_document_preview(
        existing_content="# Spec\nExisting goals.\n",
        document_name="spec.md",
        nodes=[
            DiagramNode(
                id="plan",
                title="Workflow Plan",
                kind="workflow",
                description="Build sequence",
                x=10,
                y=20,
                source="plan.md",
            ),
            DiagramNode(
                id="skill-platform",
                title="uipath-platform",
                kind="skill",
                description="Use Orchestrator guidance",
                x=20,
                y=30,
                source=".cursor/skills/uipath-platform",
            ),
        ],
        edges=[
            DiagramEdge(
                id="plan-skill",
                from_="plan",
                to="skill-platform",
                label="uses",
            )
        ],
        focus="skill-platform",
        context=[{"book_id": "uipath-cli", "chapter_id": "01", "section_id": "pack"}],
    )

    assert content.startswith("# Spec\nExisting goals.")
    assert GENERATED_SECTION_START in content
    assert "### Visual Builder Scope" in content
    assert "- uipath-platform (skill): Use Orchestrator guidance" in content
    assert "- Library context: uipath-cli/01/pack" in content
    assert GENERATED_SECTION_END in content


def test_build_diagram_document_preview_replaces_existing_generated_section() -> None:
    existing = "\n".join(
        [
            "# Plan",
            "",
            GENERATED_SECTION_START,
            "old generated content",
            GENERATED_SECTION_END,
            "",
            "Manual notes.",
            "",
        ]
    )

    content = build_diagram_document_preview(
        existing_content=existing,
        document_name="plan.md",
        nodes=[
            DiagramNode(
                id="workflow",
                title="Workflow",
                kind="workflow",
                description="Implement flow",
                x=10,
                y=20,
            ),
            DiagramNode(
                id="review",
                title="Review",
                kind="review",
                description="Validate diff",
                x=20,
                y=40,
            ),
        ],
        edges=[
            DiagramEdge(
                id="workflow-review",
                from_="workflow",
                to="review",
                label="validates",
            )
        ],
    )

    assert "old generated content" not in content
    assert "1. Workflow (workflow): Implement flow" in content
    assert "Manual notes." in content
    assert content.count(GENERATED_SECTION_START) == 1


def test_build_diagram_document_preview_generates_tasks_checklist() -> None:
    content = build_diagram_document_preview(
        existing_content="# Tasks\n",
        document_name="tasks.md",
        nodes=[
            DiagramNode(
                id="spec",
                title="Spec",
                kind="document",
                description="Define scope",
                x=0,
                y=0,
                source="spec.md",
            ),
            DiagramNode(
                id="workflow",
                title="Workflow",
                kind="workflow",
                description="Build flow",
                x=0,
                y=10,
            ),
        ],
        edges=[DiagramEdge(id="spec-workflow", from_="spec", to="workflow", label="drives")],
    )

    assert "### Flow-Ordered Checklist" in content
    assert "- [ ] Review document node: Spec" in content
    assert "- [ ] Review workflow node: Workflow" in content
    assert "Confirm edge `drives` to `workflow`." in content


def test_diagram_generated_section_escapes_marker_like_diagram_text() -> None:
    existing = "# Plan\n"
    content = build_diagram_document_preview(
        existing_content=existing,
        document_name="plan.md",
        nodes=[
            DiagramNode(
                id="workflow",
                title=f"Title {GENERATED_SECTION_START}",
                kind="workflow",
                description=f"Description {GENERATED_SECTION_END}",
                x=10,
                y=20,
                source=f"source {GENERATED_SECTION_START}",
            ),
            DiagramNode(
                id="review",
                title="Review",
                kind="review",
                description="Validate",
                x=20,
                y=40,
            ),
        ],
        edges=[
            DiagramEdge(
                id="workflow-review",
                from_="workflow",
                to="review",
                label=f"label {GENERATED_SECTION_END}",
            )
        ],
        context=[
            {
                "book_id": f"book {GENERATED_SECTION_START}",
                "chapter_id": "chapter",
                "section_id": f"section {GENERATED_SECTION_END}",
            }
        ],
    )

    generated_block = content[
        content.index(GENERATED_SECTION_START) + len(GENERATED_SECTION_START):
        content.index(GENERATED_SECTION_END)
    ]
    assert GENERATED_SECTION_START not in generated_block
    assert GENERATED_SECTION_END not in generated_block
    assert ESCAPED_GENERATED_SECTION_START in generated_block
    assert ESCAPED_GENERATED_SECTION_END in generated_block

    updated = build_diagram_document_preview(
        existing_content=content,
        document_name="plan.md",
        nodes=[
            DiagramNode(
                id="workflow",
                title="Updated Workflow",
                kind="workflow",
                description="Updated flow",
                x=10,
                y=20,
            )
        ],
        edges=[],
    )

    assert updated.count(GENERATED_SECTION_START) == 1
    assert updated.count(GENERATED_SECTION_END) == 1
    assert "Updated Workflow" in updated
    assert "Title" not in updated


def test_diagram_generated_section_preserves_trailing_existing_content() -> None:
    existing = "# Spec\nPreserve me.   \n\n  \n"

    content = build_diagram_document_preview(
        existing_content=existing,
        document_name="spec.md",
        nodes=[
            DiagramNode(
                id="workflow",
                title="Workflow",
                kind="workflow",
                description="Build flow",
                x=0,
                y=0,
            )
        ],
        edges=[],
    )

    assert content.startswith(f"{existing}\n{GENERATED_SECTION_START}")
