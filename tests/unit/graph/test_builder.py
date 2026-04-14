"""LangGraph builder smoke tests."""

import asyncio

from uipath_claude.graph.builder import compile_chat_graph


def test_compile_chat_graph_runs_route_execute() -> None:
    skills: list[dict] = []

    def select_skills(_user: str) -> list[dict]:
        return []

    def build_runtime(_user: str, selected: list[dict]) -> str:
        return "ctx" if selected else ""

    async def run_model(_messages, runtime: str, stream: bool) -> str:
        assert isinstance(stream, bool)
        return "model-out"

    graph = compile_chat_graph(
        skills,
        select_skills_fn=select_skills,
        build_runtime_for_selected=build_runtime,
        run_model=run_model,
    )
    result = asyncio.run(
        graph.ainvoke(
            {
                "messages": [{"role": "user", "content": "hello"}],
                "stream": False,
                "runtime_extra": "",
            }
        )
    )
    assert result["assistant_response"] == "model-out"
    assert result["messages"][-1]["role"] == "assistant"


def test_graph_has_route_and_execute_nodes() -> None:
    async def run_model(_m, _r, _s):
        return "x"

    g = compile_chat_graph(
        [],
        select_skills_fn=lambda u: [],
        build_runtime_for_selected=lambda u, s: "",
        run_model=run_model,
    )
    assert "route" in g.nodes
    assert "execute" in g.nodes
