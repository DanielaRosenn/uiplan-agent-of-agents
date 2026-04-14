"""Skill picking matrix tests for common user intents.

This module tests the skill selection logic to ensure the agent picks
the correct skill based on user intent. The matrix covers:

1. RPA workflows (XAML) - mail, Excel, UI automation
2. Coded workflows (C#) - Integration Service, custom logic
3. Documentation - PDD, SDD
4. Platform operations - Orchestrator, deployment

Each test validates that the skill picker correctly identifies intent
and selects the most appropriate skill.
"""

import pytest
from uipath_claude.cli.app import _debug_skill_selection, _select_relevant_skills


def _skills_fixture() -> list[dict]:
    """Comprehensive skill fixture covering all major skill types."""
    return [
        {
            "name": "uipath-rpa",
            "description": "Generate and edit UiPath XAML RPA workflows for Studio.",
            "triggers": ["workflow", "xaml", "outlook email", "ui automation", "excel", "mail"],
        },
        {
            "name": "uipath-rpa-workflows",
            "description": "Legacy alias for RPA workflows.",
            "triggers": ["workflow", "xaml"],
        },
        {
            "name": "uipath-coded-workflows",
            "description": "Legacy coded workflow alias using C# and .cs files.",
            "triggers": ["coded workflow", ".cs", "csharp"],
        },
        {
            "name": "uipath-platform",
            "description": "UiPath platform operations - Orchestrator, deployment, Integration Service.",
            "triggers": ["orchestrator", "deploy", "integration service", "connector"],
        },
        {
            "name": "uipath-maestro-flow",
            "description": "Create and manage UiPath Flow projects.",
            "triggers": ["flow", "maestro", "agentic"],
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


def _skills_fixture_with_planner() -> list[dict]:
    return [
        {
            "name": "uipath-planner",
            "description": "Plan multi-skill execution and disambiguate UiPath requests.",
            "triggers": [],
        },
        *_skills_fixture(),
    ]


class TestRPAWorkflowSkillPicking:
    """Tests for RPA workflow intent detection."""

    def test_outlook_email_workflow(self):
        skills = _skills_fixture()
        selected = _select_relevant_skills(
            "Build a UiPath workflow that reads Outlook emails and logs subjects",
            skills,
        )
        assert selected
        assert selected[0]["name"] == "uipath-rpa"

    def test_outlook_last_30_days_print_subjects_project(self):
        skills = _skills_fixture()
        prompt = (
            "Create a UiPath automation project that reads Outlook emails and prints "
            "to the screen the last subjects from the last 30 days"
        )
        selected = _select_relevant_skills(prompt, skills)
        assert selected
        assert selected[0]["name"] == "uipath-rpa"

    def test_excel_read_write_workflow(self):
        skills = _skills_fixture()
        selected = _select_relevant_skills(
            "Create a workflow that reads data from Excel and writes to another file",
            skills,
        )
        assert selected
        assert selected[0]["name"] == "uipath-rpa"

    def test_ui_automation_workflow(self):
        skills = _skills_fixture()
        selected = _select_relevant_skills(
            "Build a workflow with UI automation to click buttons and type text",
            skills,
        )
        assert selected
        assert selected[0]["name"] == "uipath-rpa"

    def test_generic_workflow_request(self):
        skills = _skills_fixture()
        selected = _select_relevant_skills(
            "Create a UiPath workflow",
            skills,
        )
        assert selected
        assert selected[0]["name"] == "uipath-rpa"

    def test_xaml_explicit_request(self):
        skills = _skills_fixture()
        selected = _select_relevant_skills(
            "Generate XAML for a simple automation",
            skills,
        )
        assert selected
        assert selected[0]["name"] == "uipath-rpa"


class TestCodedWorkflowSkillPicking:
    """Tests for coded workflow intent detection."""

    def test_coded_workflow_explicit(self):
        skills = _skills_fixture()
        selected = _select_relevant_skills(
            "Create a coded workflow in .cs using CSharp",
            skills,
        )
        assert selected
        assert selected[0]["name"] == "uipath-coded-workflows"

    def test_cs_file_request(self):
        skills = _skills_fixture()
        selected = _select_relevant_skills(
            "Write a .cs file for my UiPath project",
            skills,
        )
        assert selected
        assert selected[0]["name"] == "uipath-coded-workflows"

    def test_csharp_explicit(self):
        skills = _skills_fixture()
        selected = _select_relevant_skills(
            "Create a C# coded workflow",
            skills,
        )
        assert selected
        assert selected[0]["name"] == "uipath-coded-workflows"


class TestIntegrationServiceSkillPicking:
    """Tests for Integration Service intent detection."""

    def test_connector_request(self):
        skills = _skills_fixture()
        selected = _select_relevant_skills(
            "Use the Jira connector to create issues",
            skills,
        )
        assert selected
        assert any("platform" in s["name"].lower() for s in selected)

    def test_integration_service_explicit(self):
        skills = _skills_fixture()
        selected = _select_relevant_skills(
            "Call Integration Service API",
            skills,
        )
        assert selected
        assert any("platform" in s["name"].lower() for s in selected)


class TestDocumentationSkillPicking:
    """Tests for documentation intent detection."""

    def test_pdd_request(self):
        skills = _skills_fixture()
        selected = _select_relevant_skills(
            "Please create a full PDD for the invoice process",
            skills,
        )
        assert selected
        assert selected[0]["name"] == "pdd-creation"

    def test_process_definition_document(self):
        skills = _skills_fixture()
        selected = _select_relevant_skills(
            "Generate a process definition document",
            skills,
        )
        assert selected
        assert selected[0]["name"] == "pdd-creation"

    def test_sdd_request(self):
        skills = _skills_fixture()
        selected = _select_relevant_skills(
            "Generate an SDD with architecture and flow details for this automation",
            skills,
        )
        assert selected
        assert selected[0]["name"] == "sdd-flow-canvas"

    def test_solution_design_document(self):
        skills = _skills_fixture()
        selected = _select_relevant_skills(
            "Create a solution design document",
            skills,
        )
        assert selected
        assert selected[0]["name"] == "sdd-flow-canvas"


class TestFlowSkillPicking:
    """Tests for Maestro Flow intent detection."""

    def test_flow_project_request(self):
        skills = _skills_fixture()
        selected = _select_relevant_skills(
            "Create a new Flow project",
            skills,
        )
        assert selected
        assert any("flow" in s["name"].lower() or "maestro" in s["name"].lower() for s in selected)

    def test_maestro_explicit(self):
        skills = _skills_fixture()
        selected = _select_relevant_skills(
            "Build a Maestro agentic workflow",
            skills,
        )
        assert selected
        assert any("flow" in s["name"].lower() or "maestro" in s["name"].lower() for s in selected)


class TestSkillPickingEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_minimum_threshold_filters_irrelevant(self):
        skills = _skills_fixture()
        selected = _select_relevant_skills("hello there", skills)
        assert selected == []

    def test_deterministic_ordering_for_equal_scores(self):
        skills = [
            {"name": "alpha-skill", "description": "foo", "triggers": []},
            {"name": "beta-skill", "description": "foo", "triggers": []},
        ]
        selected = _select_relevant_skills("foo", skills, max_items=2)
        assert [item["name"] for item in selected] == ["alpha-skill", "beta-skill"]

    def test_debug_trace_includes_scores(self):
        skills = _skills_fixture()
        traces = _debug_skill_selection("Create an SDD architecture document", skills)
        assert traces
        assert any(trace.startswith("sdd-flow-canvas:") for trace in traces)

    def test_max_items_limit_respected(self):
        skills = _skills_fixture()
        selected = _select_relevant_skills(
            "Create a workflow with Excel and email",
            skills,
            max_items=1,
        )
        assert len(selected) <= 1

    def test_canonical_name_preferred_over_alias(self):
        skills = _skills_fixture()
        selected = _select_relevant_skills(
            "Build a UiPath workflow",
            skills,
        )
        assert selected
        assert selected[0]["name"] == "uipath-rpa"

    def test_empty_skills_list_returns_empty(self):
        selected = _select_relevant_skills("Create a workflow", [])
        assert selected == []

    def test_empty_input_returns_empty(self):
        skills = _skills_fixture()
        selected = _select_relevant_skills("", skills)
        assert selected == []


class TestPlannerOverridesSelection:
    """When uipath-planner is loaded, ambiguous prompts should prefer it."""

    def test_what_can_i_build_selects_planner(self):
        skills = _skills_fixture_with_planner()
        selected = _select_relevant_skills("What can I build?", skills)
        assert selected and selected[0]["name"] == "uipath-planner"

    def test_build_and_deploy_selects_planner(self):
        skills = _skills_fixture_with_planner()
        selected = _select_relevant_skills(
            "I need to build and deploy this to orchestrator",
            skills,
        )
        assert selected and selected[0]["name"] == "uipath-planner"


class TestSkillPickingMatrix:
    """Comprehensive matrix test covering all intent-to-skill mappings."""

    @pytest.mark.parametrize("prompt,expected_skill", [
        ("Read emails from Outlook", "uipath-rpa"),
        ("Create Excel automation", "uipath-rpa"),
        ("Build UI automation workflow", "uipath-rpa"),
        ("Generate XAML workflow", "uipath-rpa"),
        ("Create coded workflow in C#", "uipath-coded-workflows"),
        ("Write .cs file", "uipath-coded-workflows"),
        ("Create PDD document", "pdd-creation"),
        ("Generate SDD architecture", "sdd-flow-canvas"),
        ("Create Flow project", "uipath-maestro-flow"),
        (
            "UiPath automation: read Outlook inbox and show subjects from the last 30 days",
            "uipath-rpa",
        ),
    ])
    def test_intent_to_skill_mapping(self, prompt, expected_skill):
        skills = _skills_fixture()
        selected = _select_relevant_skills(prompt, skills)
        assert selected, f"No skill selected for: {prompt}"
        assert selected[0]["name"] == expected_skill, \
            f"Expected {expected_skill} for '{prompt}', got {selected[0]['name']}"
