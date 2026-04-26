"""Pin MCP ToolAnnotations on every exposed tool.

These annotations let MCP clients (Cursor in particular) show their native
Allow/Deny approval card before invoking destructive tools, without us having
to roll a custom in-chat approval prompt.
"""
from __future__ import annotations

import pytest

from mcp_server.tools.agent_tools import get_agent_tools
from mcp_server.tools.answer_tools import get_answer_tools
from mcp_server.tools.design_tools import get_design_tools
from mcp_server.tools.doc_tools import get_doc_tools
from mcp_server.tools.intent_tools import get_intent_tools
from mcp_server.tools.library_tools import get_library_tools
from mcp_server.tools.memory_tools import get_memory_tools
from mcp_server.tools.assistant_tools import get_assistant_tools
from mcp_server.tools.plan_tools import get_plan_tools
from mcp_server.tools.skill_tools import get_skill_tools
from mcp_server.tools.workflow_tools import get_workflow_tools

ALL_GETTERS = [
    get_library_tools,
    get_doc_tools,
    get_skill_tools,
    get_agent_tools,
    get_memory_tools,
    get_workflow_tools,
    get_design_tools,
    get_intent_tools,
    get_plan_tools,
    get_answer_tools,
    get_assistant_tools,
]

READ_ONLY = {
    # library
    "uipath_library_list",
    "uipath_library_toc",
    "uipath_library_read_section",
    "uipath_library_search",
    "uipath_library_lookup",
    "uipath_library_list_proposals",
    # doc
    "uipath_doc_list_packages",
    "uipath_doc_list_activities",
    "uipath_doc_get_activity",
    "uipath_doc_get_package_overview",
    "uipath_doc_search",
    "uipath_doc_find_activity",
    "query_uipath_docs",
    "uipath_doc_query",
    "uipath_doc_read_template",
    "uipath_doc_list_docs",
    "uipath_doc_read_doc",
    # skill
    "uipath_skill_list",
    "uipath_skill_get",
    "uipath_skill_match",
    "uipath_skill_insights_query",
    "uipath_skill_manifest",
    "uipath_skill_check_updates",
    "uipath_skill_lessons_list",
    # agent
    "uipath_agent_classify_intent",
    # memory
    "uipath_memory_load",
    # workflow
    "uipath_workflow_read_file",
    "uipath_workflow_list_directory",
    "uipath_workflow_read_project",
    "uipath_workflow_validate",
    "uipath_workflow_environment_probe",
    # design
    "uipath_design_list",
    "uipath_design_status",
    # intent / plan / answer
    "uipath_intent_classify",
    "uipath_plan_build",
    "uipath_plan_list",
    "uipath_plan_read",
    "uipath_plan_render_mermaid",
    "uipath_plan_brainstorm",
    "uipath_plan_diff",
    "uipath_plan_ground",
    "uipath_plan_review",
    "uipath_answer",
    "uipath_assistant_context",
    "uipath_assistant_route",
    # ensure_project_structure no longer hand-writes scaffolds; it returns
    # success or refuses + routes to create_project. Read-only in practice.
    "uipath_workflow_ensure_project",
    # status getter; surfaces session metadata only.
    "uipath_workflow_session_status",
}

DESTRUCTIVE = {
    # doc
    "uipath_doc_write_doc",
    # library
    "uipath_library_approve_proposal",
    "uipath_library_reject_proposal",
    # skill
    "uipath_skill_update",
    "uipath_skill_lessons_approve",
    # agent orchestration (transitively destructive)
    "uipath_agent_bootstrap",
    "uipath_agent_plan",
    "uipath_agent_execute",
    "uipath_agent_ba",
    "uipath_agent_sa",
    # memory
    "uipath_memory_save",
    "uipath_memory_append",
    # design
    "uipath_design_approve",
    "uipath_design_reject",
    # workflow
    "uipath_workflow_write_file",
    "uipath_workflow_install_package",
    "uipath_workflow_validate_loop",
    "uipath_workflow_build_and_verify",
    "uipath_workflow_create_project",
    "uipath_workflow_run",
    "uipath_workflow_debug",
    "uipath_workflow_run_command",
    "uipath_workflow_deploy",
    "uipath_workflow_publish",
    "uipath_plan_save",
    "uipath_plan_refine",
    "uipath_plan_accept",
    "uipath_plan_reject",
    "uipath_plan_publish",
    "uipath_plan_spec_new",
    "uipath_plan_plan_new",
    "uipath_plan_tasks_new",
    "uipath_plan_uiplan_new",
}

STAGING = {
    # safe queue/append; nothing on disk in data/library or in a UiPath project
    # is mutated until a separate destructive tool runs.
    "uipath_library_propose_section",
    "uipath_library_propose_chapter",
    "uipath_skill_insights_add",
    "uipath_design_propose",
    "uipath_plan_status_set",
    "uipath_plan_new",
}


def _all_tools():
    tools = []
    for getter in ALL_GETTERS:
        tools.extend(getter())
    return tools


def test_every_tool_has_annotations():
    for tool in _all_tools():
        assert tool.annotations is not None, f"{tool.name} is missing ToolAnnotations"


@pytest.mark.parametrize("name", sorted(READ_ONLY))
def test_read_only_tools(name):
    tool = next(t for t in _all_tools() if t.name == name)
    assert tool.annotations.readOnlyHint is True, f"{name} should be readOnlyHint=True"


@pytest.mark.parametrize("name", sorted(DESTRUCTIVE))
def test_destructive_tools(name):
    tool = next(t for t in _all_tools() if t.name == name)
    assert tool.annotations.destructiveHint is True, (
        f"{name} should be destructiveHint=True"
    )
    assert tool.annotations.readOnlyHint is False, (
        f"{name} should be readOnlyHint=False"
    )


@pytest.mark.parametrize("name", sorted(STAGING))
def test_staging_tools(name):
    tool = next(t for t in _all_tools() if t.name == name)
    assert tool.annotations.destructiveHint is False, (
        f"{name} stages a proposal; destructiveHint should be False"
    )
    assert tool.annotations.readOnlyHint is False, (
        f"{name} writes to a queue; readOnlyHint should be False"
    )


def test_classification_covers_every_tool():
    classified = READ_ONLY | DESTRUCTIVE | STAGING
    actual = {t.name for t in _all_tools()}
    missing = actual - classified
    extra = classified - actual
    assert not missing, f"Tools without classification: {sorted(missing)}"
    assert not extra, f"Classified names not registered: {sorted(extra)}"


def test_approve_vs_propose_boundary():
    """Pin the staging-vs-commit split: propose stages, approve commits."""
    tools = {t.name: t for t in _all_tools()}
    assert tools["uipath_library_propose_chapter"].annotations.destructiveHint is False
    assert tools["uipath_library_approve_proposal"].annotations.destructiveHint is True
