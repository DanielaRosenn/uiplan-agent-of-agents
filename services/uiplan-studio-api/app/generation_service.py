import difflib

from app.schemas import DiagramEdge, DiagramNode


GENERATED_SECTION_START = "<!-- uiplan-diagram-generated:start -->"
GENERATED_SECTION_END = "<!-- uiplan-diagram-generated:end -->"
ESCAPED_GENERATED_SECTION_START = "<!-- uiplan-diagram-generated&#58;start -->"
ESCAPED_GENERATED_SECTION_END = "<!-- uiplan-diagram-generated&#58;end -->"
CONTEXT_KINDS = {"skill", "library", "review"}
SEQUENCE_KINDS = {"workflow", "review", "skill", "library"}
KIND_LABELS = {
    "document": "Documents",
    "workflow": "Workflow",
    "skill": "Skills",
    "library": "Library Context",
    "review": "Review Gates",
}


def build_preview_patch(before: str, after: str, filename: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile=filename,
            tofile=filename,
            lineterm="",
        )
    )


def build_diagram_document_preview(
    existing_content: str,
    document_name: str,
    nodes: list[DiagramNode],
    edges: list[DiagramEdge],
    focus: str | None = None,
    context: list[dict[str, str | int | None]] | None = None,
) -> str:
    section = _build_generated_section(document_name, nodes, edges, focus, context or [])
    return _upsert_generated_section(existing_content, section)


def enrich_generated_content(
    proposed_content: str,
    library_context: list[dict[str, str | int | None]] | None = None,
) -> str:
    if not library_context:
        return proposed_content

    citations: list[str] = []
    for item in library_context[:3]:
        book_id = str(item.get("book_id", "")).strip()
        chapter_id = str(item.get("chapter_id", "")).strip()
        section_id = str(item.get("section_id", "")).strip()
        if book_id and chapter_id and section_id:
            citations.append(f"- {book_id}/{chapter_id}/{section_id}")

    if not citations:
        return proposed_content

    context_block = "\n".join(
        [
            "",
            "<!-- generated_with_library_context",
            *citations,
            "-->",
            "",
        ]
    )
    if proposed_content.endswith("\n"):
        return f"{proposed_content.rstrip()}{context_block}\n"
    return f"{proposed_content}{context_block}"


def _build_generated_section(
    document_name: str,
    nodes: list[DiagramNode],
    edges: list[DiagramEdge],
    focus: str | None,
    context: list[dict[str, str | int | None]],
) -> str:
    ordered_nodes = _flow_order(nodes, edges)
    if document_name == "spec.md":
        body = _build_spec_section(ordered_nodes, edges, focus, context)
    elif document_name == "plan.md":
        body = _build_plan_section(ordered_nodes, edges)
    elif document_name == "tasks.md":
        body = _build_tasks_section(ordered_nodes, edges)
    else:
        raise ValueError(f"Unsupported document name: {document_name}")

    return "\n".join([GENERATED_SECTION_START, body.rstrip(), GENERATED_SECTION_END, ""])


def _build_spec_section(
    nodes: list[DiagramNode],
    edges: list[DiagramEdge],
    focus: str | None,
    context: list[dict[str, str | int | None]],
) -> str:
    focused_nodes = _focused_nodes(nodes, focus)
    context_nodes = [node for node in nodes if node.kind in CONTEXT_KINDS or node.source]
    lines = [
        "## Generated From Visual Builder",
        "",
        "### Visual Builder Scope",
        f"- Diagram contains {len(nodes)} node(s) and {len(edges)} edge(s).",
        "- Scope is derived from the current visual builder canvas and remains preview-only.",
        "",
        "### Selected Nodes",
        *_node_lines(focused_nodes or nodes),
        "",
        "### Context Sources",
        *_context_lines(context_nodes, context),
        "",
        "### Assumptions",
        "- Generated content should be reviewed before applying the preview.",
        "- Existing document sections remain authoritative unless explicitly updated.",
        "- Diagram edges indicate intended implementation relationships, not completed work.",
    ]
    return "\n".join(lines)


def _build_plan_section(nodes: list[DiagramNode], edges: list[DiagramEdge]) -> str:
    sequence_nodes = [node for node in nodes if node.kind in SEQUENCE_KINDS]
    if not sequence_nodes:
        sequence_nodes = nodes

    lines = [
        "## Generated From Visual Builder",
        "",
        "### Implementation Sequence",
    ]
    for index, node in enumerate(sequence_nodes, start=1):
        edge_summary = _outgoing_summary(node, edges)
        source = f" Source: {_safe_text(node.source)}." if node.source else ""
        lines.append(
            f"{index}. {_safe_text(node.title)} ({_safe_text(node.kind)}): "
            f"{_safe_text(node.description)}{source}{edge_summary}"
        )

    lines.extend(
        [
            "",
            "### Review Flow",
            *_edge_lines(edges),
            "",
            "### Notes",
            "- Sequence is deterministic from diagram flow order and node kind priority.",
            "- Apply this preview only after reviewing the generated diff.",
        ]
    )
    return "\n".join(lines)


def _build_tasks_section(nodes: list[DiagramNode], edges: list[DiagramEdge]) -> str:
    lines = [
        "## Generated From Visual Builder",
        "",
        "### Flow-Ordered Checklist",
    ]
    for node in nodes:
        lines.append(f"- [ ] Review {_safe_text(node.kind)} node: {_safe_text(node.title)}")
        lines.append(f"  - {_safe_text(node.description)}")
        if node.source:
            lines.append(f"  - Source: {_safe_text(node.source)}")
        outgoing = [edge for edge in edges if edge.from_ == node.id]
        for edge in sorted(outgoing, key=lambda item: (item.to, item.label, item.id)):
            lines.append(
                f"  - Confirm edge `{_safe_text(edge.label)}` to `{_safe_text(edge.to)}`."
            )

    lines.extend(["", "### Checklist By Node Kind"])
    for kind in sorted({node.kind for node in nodes}, key=_kind_sort_key):
        lines.append(f"- {_safe_text(KIND_LABELS.get(kind, kind.title()))}")
        for node in [item for item in nodes if item.kind == kind]:
            lines.append(f"  - [ ] Capture output for {_safe_text(node.title)}.")

    return "\n".join(lines)


def _upsert_generated_section(existing_content: str, section: str) -> str:
    start_index = existing_content.find(GENERATED_SECTION_START)
    end_index = existing_content.find(GENERATED_SECTION_END)
    if start_index != -1 and end_index != -1 and end_index > start_index:
        section_end = end_index + len(GENERATED_SECTION_END)
        has_newline = existing_content[section_end:section_end + 1] == "\n"
        trailing_newline = "\n" if has_newline else ""
        suffix = existing_content[section_end + len(trailing_newline):]
        return f"{existing_content[:start_index]}{section.rstrip()}{trailing_newline}{suffix}"

    if not existing_content:
        return section
    separator = "\n\n" if not existing_content.endswith("\n") else "\n"
    return f"{existing_content}{separator}{section}"


def _flow_order(nodes: list[DiagramNode], edges: list[DiagramEdge]) -> list[DiagramNode]:
    nodes_by_id = {node.id: node for node in nodes}
    incoming = {node.id: 0 for node in nodes}
    outgoing: dict[str, list[str]] = {node.id: [] for node in nodes}
    for edge in edges:
        if edge.from_ in nodes_by_id and edge.to in nodes_by_id:
            outgoing[edge.from_].append(edge.to)
            incoming[edge.to] += 1

    ready = sorted(
        [node_id for node_id, count in incoming.items() if count == 0],
        key=lambda node_id: _node_sort_key(nodes_by_id[node_id]),
    )
    ordered_ids: list[str] = []

    while ready:
        node_id = ready.pop(0)
        ordered_ids.append(node_id)
        children = sorted(
            outgoing[node_id],
            key=lambda item: _node_sort_key(nodes_by_id[item]),
        )
        for child_id in children:
            incoming[child_id] -= 1
            if incoming[child_id] == 0:
                ready.append(child_id)
                ready.sort(key=lambda item: _node_sort_key(nodes_by_id[item]))

    ordered_id_set = set(ordered_ids)
    remaining = [
        node.id
        for node in sorted(nodes, key=_node_sort_key)
        if node.id not in ordered_id_set
    ]
    return [nodes_by_id[node_id] for node_id in [*ordered_ids, *remaining]]


def _focused_nodes(nodes: list[DiagramNode], focus: str | None) -> list[DiagramNode]:
    if not focus:
        return []
    normalized = focus.casefold()
    return [
        node
        for node in nodes
        if normalized
        in {node.id.casefold(), node.title.casefold(), (node.source or "").casefold()}
    ]


def _node_lines(nodes: list[DiagramNode]) -> list[str]:
    if not nodes:
        return ["- No nodes selected."]
    return [
        f"- {_safe_text(node.title)} ({_safe_text(node.kind)}): "
        f"{_safe_text(node.description)}"
        + (f" Source: {_safe_text(node.source)}." if node.source else "")
        for node in nodes
    ]


def _context_lines(
    nodes: list[DiagramNode],
    context: list[dict[str, str | int | None]],
) -> list[str]:
    lines: list[str] = []
    for node in nodes:
        source = node.source or "diagram"
        lines.append(
            f"- {_safe_text(node.title)} ({_safe_text(node.kind)}): {_safe_text(source)}"
        )
    for item in context:
        citation = "/".join(
            _safe_text(str(item.get(key, "")).strip())
            for key in ("book_id", "chapter_id", "section_id")
            if str(item.get(key, "")).strip()
        )
        if citation:
            lines.append(f"- Library context: {citation}")
    return lines or ["- No explicit context sources selected."]


def _edge_lines(edges: list[DiagramEdge]) -> list[str]:
    if not edges:
        return ["- No diagram edges defined."]
    return [
        f"- `{_safe_text(edge.from_)}` --{_safe_text(edge.label)}--> `{_safe_text(edge.to)}`"
        for edge in sorted(edges, key=lambda item: (item.from_, item.to, item.label, item.id))
    ]


def _outgoing_summary(node: DiagramNode, edges: list[DiagramEdge]) -> str:
    outgoing = [edge for edge in edges if edge.from_ == node.id]
    if not outgoing:
        return ""
    links = ", ".join(
        f"{_safe_text(edge.label)} -> {_safe_text(edge.to)}"
        for edge in sorted(outgoing, key=lambda item: (item.to, item.label, item.id))
    )
    return f" Next: {links}."


def _safe_text(value: str | None) -> str:
    if value is None:
        return ""
    return (
        str(value)
        .replace(GENERATED_SECTION_START, ESCAPED_GENERATED_SECTION_START)
        .replace(GENERATED_SECTION_END, ESCAPED_GENERATED_SECTION_END)
    )


def _node_sort_key(node: DiagramNode) -> tuple[int, int, str]:
    return (_kind_sort_key(node.kind), node.y, node.title.casefold())


def _kind_sort_key(kind: str) -> int:
    priority = {
        "document": 0,
        "workflow": 1,
        "skill": 2,
        "library": 3,
        "review": 4,
    }
    return priority.get(kind, 99)
