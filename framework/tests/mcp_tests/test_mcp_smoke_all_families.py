"""End-to-end smoke test covering every MCP tool family.

Goal: a teammate using Cursor or Claude Code natively (not via the bespoke
`uipath-claude` CLI) can trust that "all tools work" by running one pytest
command. This test exercises both:

1. ``list_tools()`` - the registered ``@server.list_tools()`` handler in
   ``framework/mcp_server/server.py`` - so a regression that drops a
   family's ``get_*_tools()`` extend call is caught.
2. ``call_tool(name, args)`` - the registered ``@server.call_tool()``
   prefix dispatcher - so a regression in the dispatch table is also caught
   (rather than silently falling through to ``Unknown tool``).

For each family we pick one deterministic, no-side-effect, no-LLM,
fixture-free read-only entry point. The singleton ``uipath_answer`` tool
is LLM-backed (Bedrock) so we only verify it is listed, not call it.
"""
from __future__ import annotations

import json

import pytest

from mcp_server.server import call_tool as _call_tool
from mcp_server.server import list_tools as _list_tools


# Each row: (family_prefix, tool_name_to_call, args).
# This list MUST mirror the dispatch chain in framework/mcp_server/server.py:call_tool.
# When a new tool family is added there, add one row here so this smoke covers it.
#
# Notes on specific choices:
#   - uipath_doc_list_packages may legitimately return ``[]`` depending on
#     local activity-doc fixtures; an empty list still proves dispatch + the
#     family's read path are intact, which is what the smoke is scoped to.
#   - uipath_plan_list now properly serializes datetime.date objects from YAML
#     frontmatter to ISO strings before JSON encoding (fixed BUG_PLAN_LIST_DATETIME_SERIALISE).
FAMILIES = [
    ("uipath_workflow_", "uipath_workflow_environment_probe", {}),
    ("uipath_skill_",    "uipath_skill_list",                {}),
    ("uipath_agent_",    "uipath_agent_classify_intent",     {"user_input": "hello"}),
    ("uipath_doc_",      "uipath_doc_list_packages",         {}),
    ("uipath_memory_",   "uipath_memory_load",               {}),
    ("uipath_library_",  "uipath_library_list",              {}),
    ("uipath_design_",   "uipath_design_list",               {}),
    ("uipath_intent_",   "uipath_intent_classify",
        {"user_input": "how does GetQueueItem work"}),
    ("uipath_plan_",     "uipath_plan_list",                 {}),
    ("uipath_assistant_", "uipath_assistant_context",
        {"request": "list available skills"}),
]

# uipath_answer is a singleton tool name (not a prefix family) and is
# LLM-backed (Bedrock). Verify it's listed, but never call it from the
# smoke - that would make the test depend on cloud credentials.
LISTED_ONLY = ["uipath_answer"]

# Legacy alias for uipath_doc_ family (dispatches to call_doc_tool).
# Tested separately to ensure the alias path doesn't regress.
ALIAS_TOOLS = [
    ("query_uipath_docs", {"question": "What is GetQueueItem?"}),
]


async def _catalog_names() -> list[str]:
    """Return tool names from the registered list_tools handler."""
    tools = await _list_tools()
    return [t.name for t in tools]


def _decode_text_result(result) -> str:
    """Extract the first TextContent.text from a call_tool response."""
    assert isinstance(result, list) and result, (
        f"expected non-empty list[TextContent], got {result!r}"
    )
    item = result[0]
    text = getattr(item, "text", None)
    assert isinstance(text, str), f"expected TextContent.text str, got {item!r}"
    return text


# Empty-state contract notes for the smoke test:
# - uipath_library_list returns the prose string "No books found." when the
#   library is empty.
# - uipath_design_list returns "No design proposals match the filter." when
#   no proposals exist.
# Both prose strings are non-empty, so they pass the "text != ''" / non-empty
# checks below. uipath_doc_list_packages explicitly handles an empty list.
# If a family is later rewritten to return an empty JSON [] / {} on the
# empty path, add it to the explicit-empty branch instead of relying on
# this prose escape hatch.
def _looks_non_empty(payload) -> bool:
    """True if the parsed payload is a non-empty dict/list/string, or an
    object that's not obviously empty. Used as a generous shape check."""
    if payload is None:
        return False
    if isinstance(payload, (dict, list, str)):
        return len(payload) > 0
    return True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "prefix,tool_name,args",
    FAMILIES,
    ids=[f[0] for f in FAMILIES],
)
async def test_family_smoke(prefix: str, tool_name: str, args: dict):
    names = await _catalog_names()

    family_hits = [n for n in names if n.startswith(prefix)]
    assert family_hits, (
        f"No tool with prefix {prefix!r} in catalog of {len(names)} tools "
        f"-- the family's get_*_tools() extend call may have been dropped "
        f"from list_tools() in framework/mcp_server/server.py"
    )

    assert tool_name in names, (
        f"Tool {tool_name!r} not in catalog. Family {prefix!r} has: "
        f"{sorted(family_hits)[:10]}"
    )

    result = await _call_tool(tool_name, args)
    text = _decode_text_result(result)

    if text.startswith("Error: "):
        pytest.fail(
            f"{tool_name} returned error from call_tool dispatcher: {text}"
        )
    if text.startswith("Unknown tool:"):
        pytest.fail(
            f"call_tool dispatcher has no branch for prefix {prefix!r} "
            f"(got: {text}). Check the if/elif chain in "
            f"framework/mcp_server/server.py:call_tool."
        )

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        # uipath_memory_load / uipath_library_list return prose strings,
        # not JSON. uipath_memory_load may legitimately return an empty
        # string if no persistent memory has been written yet - that is
        # still a valid "dispatcher reached the family without raising"
        # signal, which is what the smoke is scoped to.
        if tool_name == "uipath_memory_load":
            assert isinstance(text, str)
            return
        assert text != "", (
            f"{tool_name} returned an empty string with no error prefix"
        )
        return

    if tool_name == "uipath_doc_list_packages":
        # Empty package list is acceptable - no activity docs are
        # required to be present for the smoke; we only assert the
        # dispatcher reached the family and returned a parseable list.
        assert isinstance(payload, list), (
            f"{tool_name} expected list, got {type(payload).__name__}"
        )
        return

    assert _looks_non_empty(payload), (
        f"{tool_name} returned empty/None payload: {payload!r}"
    )

    if tool_name == "uipath_agent_classify_intent":
        assert isinstance(payload, dict) and "intent" in payload, (
            f"{tool_name} payload missing 'intent' key: {payload!r}"
        )
    elif tool_name == "uipath_intent_classify":
        assert isinstance(payload, dict), (
            f"{tool_name} expected dict payload, got "
            f"{type(payload).__name__}: {payload!r}"
        )
        assert any(k in payload for k in ("intent", "category")), (
            f"{tool_name} payload missing both 'intent' and 'category' "
            f"keys: {payload!r}"
        )
    elif tool_name == "uipath_assistant_context":
        assert isinstance(payload, dict), (
            f"{tool_name} expected dict payload, got "
            f"{type(payload).__name__}: {payload!r}"
        )
        assert payload.get("status") == "ok" or "context" in payload, (
            f"{tool_name} payload missing 'context' key and status != 'ok': "
            f"{payload!r}"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("name", LISTED_ONLY)
async def test_listed_only_tools(name: str):
    names = await _catalog_names()
    assert name in names, (
        f"Singleton tool {name!r} not in catalog; check that "
        f"get_answer_tools() is still extended into list_tools()"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_name,args",
    ALIAS_TOOLS,
    ids=[t[0] for t in ALIAS_TOOLS],
)
async def test_alias_tools(tool_name: str, args: dict):
    """Test legacy alias tools (e.g. query_uipath_docs) that dispatch to families."""
    names = await _catalog_names()
    assert tool_name in names, (
        f"Alias {tool_name} not in catalog -- may have been removed from "
        f"the aggregator's list_tools() in framework/mcp_server/server.py"
    )
    
    result = await _call_tool(tool_name, args)
    text = _decode_text_result(result)
    
    if text.startswith("Error: "):
        pytest.fail(
            f"{tool_name} alias returned error from call_tool dispatcher: {text}"
        )
    if text.startswith("Unknown tool: "):
        pytest.fail(
            f"{tool_name} alias not dispatched correctly (got {text!r})"
        )
    
    assert _looks_non_empty(text), (
        f"{tool_name} alias returned empty/error-like result: {text[:300]}"
    )
