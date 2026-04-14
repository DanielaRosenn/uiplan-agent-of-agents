"""Unit tests for graph node factories."""

import pytest

from uipath_claude.graph.nodes.execute import make_execute_node
from uipath_claude.graph.nodes.route import make_route_node


@pytest.mark.asyncio
async def test_route_node_sets_selected_names() -> None:
    skills = [{"name": "uipath-rpa", "path": ""}]

    def select(u: str) -> list:
        return skills if "xaml" in u.lower() else []

    route = make_route_node(select)
    out = await route({"messages": [{"role": "user", "content": "make xaml"}]})
    assert "uipath-rpa" in (out.get("selected_skill_names") or [])


@pytest.mark.asyncio
async def test_execute_node_merges_runtime_extra() -> None:
    skills_by_name = {"a": {"name": "a", "path": ""}}

    def build(_u, sel):
        return "BASE"

    async def run_model(msgs, runtime, stream):
        assert "EXTRA" in runtime
        return "done"

    route = make_route_node(lambda u: [{"name": "a", "path": ""}])
    _ = await route({"messages": [{"role": "user", "content": "hi"}]})
    execute = make_execute_node(skills_by_name, build, run_model, default_stream=False)
    state = {
        "messages": [{"role": "user", "content": "hi"}],
        "selected_skill_names": ["a"],
        "runtime_extra": "EXTRA",
        "stream": False,
    }
    out = await execute(state)
    assert out["assistant_response"] == "done"
