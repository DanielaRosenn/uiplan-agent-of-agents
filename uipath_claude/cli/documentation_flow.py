"""CLI helper to run the documentation generation sub-flow until completion."""

from __future__ import annotations

from typing import Any

from uipath_claude.graph.nodes.documentation import handle_documentation_request
from uipath_claude.rendering.progress import ProgressReporter
from uipath_claude.tools.doc_tools import list_docs

# At most one pass per doc type in _DOC_PRIORITY (pdd, sdd, add, tdd) plus buffer.
_MAX_DOC_ITERATIONS = 8


async def run_documentation_flow(
    *,
    user_input: str,
    history: list[dict[str, str]],
    project_path: str,
    session_id: str,
    model_name: str,
    region: str,
    progress: ProgressReporter,
) -> tuple[list[str], str]:
    """Run ``handle_documentation_request`` until ``doc_phase`` is ``complete``.

    Returns ``(created_docs, assistant_response)``.
    """
    state: dict[str, Any] = {
        "messages": history + [{"role": "user", "content": user_input}],
        "project_path": project_path,
        "session_id": session_id,
        "created_docs": [],
    }
    announced: set[str] = set()
    iterations = 0
    with progress.status("Documentation: generating"):
        while state.get("doc_phase") != "complete":
            iterations += 1
            if iterations > _MAX_DOC_ITERATIONS:
                assistant_text = str(state.get("assistant_response", ""))
                if assistant_text.strip():
                    assistant_text += "\n\n"
                assistant_text += (
                    f"[Documentation stopped after {_MAX_DOC_ITERATIONS} steps "
                    "(incomplete). Check doc_phase in logs.]"
                )
                state = {**state, "assistant_response": assistant_text}
                break
            state = await handle_documentation_request(
                user_input,
                state,
                model_name=model_name,
                region=region,
            )
            for doc in state.get("created_docs") or []:
                if doc in announced:
                    continue
                meta = list_docs(project_path).get(doc) or {}
                if meta.get("exists"):
                    path = meta.get("path")
                    if path:
                        progress.file_written(str(path))
                    announced.add(doc)
    assistant_text = str(state.get("assistant_response", ""))
    return list(state.get("created_docs") or []), assistant_text
