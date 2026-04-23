"""LangGraph-based chat orchestration."""

from uipath_claude.graph.builder import compile_chat_graph


async def _langgraph_studio_run_model(
    _messages: list[dict[str, str]], _runtime: str, _stream: bool
) -> str:
    """Minimal stub for LangGraph Studio; full chat uses ``compile_chat_graph`` from the CLI."""
    return (
        "[stub] LangGraph Studio graph loaded. Run `uipath-claude chat` for the full agent."
    )


# Exposed for ``langgraph.json`` (``uipath_claude.graph:graph``).
graph = compile_chat_graph(
    [],
    select_skills_fn=lambda _u: [],
    build_runtime_for_selected=lambda _u, _s: "",
    run_model=_langgraph_studio_run_model,
)

__all__ = ["compile_chat_graph", "graph"]
