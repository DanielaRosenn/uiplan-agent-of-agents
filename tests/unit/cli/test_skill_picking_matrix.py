"""Skill picking matrix tests for common user intents."""

from uipath_claude.cli.app import _debug_skill_selection, _select_relevant_skills


def _skills_fixture() -> list[dict]:
    return [
        {
            "name": "uipath-rpa-workflows",
            "description": "Generate and edit UiPath XAML RPA workflows for Studio.",
            "triggers": ["workflow", "xaml", "outlook email", "ui automation"],
        },
        {
            "name": "uipath-coded-workflows",
            "description": "Create coded workflows using C# and .cs files.",
            "triggers": ["coded workflow", ".cs", "csharp"],
        },
        {
            "name": "pdd-creation",
            "description": "Generate Process Definition Documents for automation projects.",
            "triggers": ["pdd", "process definition document"],
        },
        {
            "name": "sdd-flow-canvas",
            "description": "Create Solution Design Document content and technical architecture.",
            "triggers": ["sdd", "solution design document", "architecture"],
        },
    ]


def test_skill_pick_rpa_for_outlook_workflow_intent():
    skills = _skills_fixture()
    selected = _select_relevant_skills(
        "Build a UiPath workflow that reads Outlook emails and logs subjects",
        skills,
    )
    assert selected
    assert selected[0]["name"] == "uipath-rpa-workflows"


def test_skill_pick_coded_for_cs_intent():
    skills = _skills_fixture()
    selected = _select_relevant_skills(
        "Create a coded workflow in .cs using CSharp",
        skills,
    )
    assert selected
    assert selected[0]["name"] == "uipath-coded-workflows"


def test_skill_pick_pdd_for_document_intent():
    skills = _skills_fixture()
    selected = _select_relevant_skills(
        "Please create a full PDD for the invoice process",
        skills,
    )
    assert selected
    assert selected[0]["name"] == "pdd-creation"


def test_skill_pick_sdd_for_solution_design_intent():
    skills = _skills_fixture()
    selected = _select_relevant_skills(
        "Generate an SDD with architecture and flow details for this automation",
        skills,
    )
    assert selected
    assert selected[0]["name"] == "sdd-flow-canvas"


def test_skill_debug_trace_includes_scores_for_review():
    skills = _skills_fixture()
    traces = _debug_skill_selection("Create an SDD architecture document", skills)
    assert traces
    assert any(trace.startswith("sdd-flow-canvas:") for trace in traces)
