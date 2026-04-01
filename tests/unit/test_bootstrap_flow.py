"""Tests for Sprint 2 bootstrap flow.

Tests the complete BA -> SA -> HITL -> Developer -> QA pipeline
using mock LLM responses to avoid real API calls.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from langchain_core.messages import HumanMessage, AIMessage

from agent.state import ProjectState
from agent.nodes.ba_persona import ba_persona, _extract_json_from_response
from agent.nodes.sa_persona import sa_persona
from agent.nodes.hitl_node import hitl_node, format_hitl_display
from agent.nodes.developer_node import developer_node, _generate_project_json
from agent.nodes.qa_node import qa_node, _validate_artifacts


# ── Sample data ──────────────────────────────────────────────


SAMPLE_PDD = {
    "process_name": "InvoiceProcessor",
    "process_description": "Reads invoices from email and enters them into SAP",
    "trigger": "Scheduled daily at 8 AM",
    "input_data": ["Email inbox", "SAP credentials"],
    "output_data": ["Processed invoice count", "Error report"],
    "steps": [
        {"step": 1, "description": "Read unread emails with attachments", "application": "Outlook"},
        {"step": 2, "description": "Extract invoice data from PDF", "application": "PDF Reader"},
        {"step": 3, "description": "Enter data into SAP", "application": "SAP"},
    ],
    "business_rules": ["Only process invoices over $100"],
    "exceptions": ["Invalid PDF format", "SAP connection timeout"],
    "frequency": "Daily",
    "volume": "50-100 invoices per day",
}

SAMPLE_SDD = {
    "project_name": "InvoiceProcessor",
    "namespace": "Company.Finance.InvoiceProcessor",
    "template_type": "coded-workflow",
    "target_framework": "Windows",
    "language": "C#",
    "coded_activities": [
        {
            "class_name": "ReadEmails",
            "purpose": "Read unread emails with invoice attachments",
            "inputs": ["inboxFolder"],
            "outputs": ["emailList"],
            "dependencies": ["UiPath.Mail.Activities"],
        },
        {
            "class_name": "ExtractInvoiceData",
            "purpose": "Extract structured data from PDF invoices",
            "inputs": ["pdfPath"],
            "outputs": ["invoiceData"],
            "dependencies": ["UiPath.PDF.Activities"],
        },
    ],
    "config_keys": [
        {"key": "SAPUrl", "description": "SAP system URL", "default_value": ""},
        {"key": "InboxFolder", "description": "Email folder to monitor", "default_value": "Inbox"},
    ],
    "nuget_packages": [
        "UiPath.System.Activities",
        "UiPath.UIAutomation.Activities",
        "UiPath.Mail.Activities",
    ],
    "complexity": "moderate",
    "hitl_reason": None,
}


# ── BA Persona Tests ─────────────────────────────────────────


class TestExtractJson:
    def test_extract_json_from_code_block(self):
        content = 'Here is the PDD:\n```json\n{"process_name": "Test"}\n```\nDone.'
        result = _extract_json_from_response(content)
        assert result == {"process_name": "Test"}

    def test_extract_json_plain(self):
        content = '{"process_name": "Test"}'
        result = _extract_json_from_response(content)
        assert result == {"process_name": "Test"}

    def test_extract_json_none_for_text(self):
        content = "I need more information about your process."
        result = _extract_json_from_response(content)
        assert result is None


class TestBaPersona:
    @pytest.mark.asyncio
    async def test_ba_generates_pdd(self):
        """BA should produce PDD when description is sufficient."""
        pdd_json = json.dumps(SAMPLE_PDD)
        mock_response = AIMessage(content=f"Here is your PDD:\n```json\n{pdd_json}\n```")

        with patch("agent.nodes.ba_persona.ba_llm") as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)

            state = {
                "messages": [HumanMessage(content="Automate invoice processing from email to SAP")],
                "mode": "bootstrap",
                "current_phase": "ba",
            }

            result = await ba_persona(state)

        assert result["pdd"] == SAMPLE_PDD
        assert result["needs_clarification"] is False
        assert result["project_name"] == "InvoiceProcessor"

    @pytest.mark.asyncio
    async def test_ba_asks_clarification(self):
        """BA should ask for clarification when description is vague."""
        mock_response = AIMessage(content="What specific application do you use for invoices?")

        with patch("agent.nodes.ba_persona.ba_llm") as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)

            state = {
                "messages": [HumanMessage(content="automate invoices")],
                "mode": "bootstrap",
                "current_phase": "ba",
            }

            result = await ba_persona(state)

        assert result["needs_clarification"] is True
        assert "clarify_question" in result


# ── SA Persona Tests ─────────────────────────────────────────


class TestSaPersona:
    @pytest.mark.asyncio
    async def test_sa_generates_sdd(self):
        """SA should produce SDD from PDD."""
        sdd_json = json.dumps(SAMPLE_SDD)
        mock_response = AIMessage(content=f"```json\n{sdd_json}\n```")

        with patch("agent.nodes.sa_persona.sa_llm") as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)

            state = {
                "messages": [],
                "pdd": SAMPLE_PDD,
                "current_phase": "sa",
            }

            result = await sa_persona(state)

        assert result["sdd"] == SAMPLE_SDD
        assert result["requires_hitl"] is False  # moderate complexity
        assert result["template_type"] == "coded-workflow"

    @pytest.mark.asyncio
    async def test_sa_flags_hitl_for_complex(self):
        """SA should flag HITL for complex projects."""
        complex_sdd = {**SAMPLE_SDD, "complexity": "complex", "hitl_reason": "Too many activities"}
        sdd_json = json.dumps(complex_sdd)
        mock_response = AIMessage(content=f"```json\n{sdd_json}\n```")

        with patch("agent.nodes.sa_persona.sa_llm") as mock_llm:
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)

            state = {"messages": [], "pdd": SAMPLE_PDD, "current_phase": "sa"}
            result = await sa_persona(state)

        assert result["requires_hitl"] is True


# ── HITL Node Tests ──────────────────────────────────────────


class TestHitlNode:
    @pytest.mark.asyncio
    async def test_hitl_approved(self):
        state = {
            "messages": [HumanMessage(content="approved")],
            "sdd": SAMPLE_SDD,
        }
        result = await hitl_node(state)
        assert result["hitl_approved"] is True

    @pytest.mark.asyncio
    async def test_hitl_rejected(self):
        state = {
            "messages": [HumanMessage(content="rejected: needs more error handling")],
            "sdd": SAMPLE_SDD,
        }
        result = await hitl_node(state)
        assert result["hitl_approved"] is False
        assert "error handling" in result["hitl_feedback"]

    def test_format_hitl_display(self):
        display = format_hitl_display(SAMPLE_SDD)
        assert "InvoiceProcessor" in display
        assert "ReadEmails" in display
        assert "HUMAN REVIEW REQUIRED" in display


# ── Developer Node Tests ─────────────────────────────────────


class TestDeveloperNode:
    @pytest.mark.asyncio
    async def test_developer_generates_files(self):
        state = {
            "messages": [],
            "sdd": SAMPLE_SDD,
            "project_name": "InvoiceProcessor",
        }
        result = await developer_node(state)

        artifacts = result["artifacts"]
        assert "project.json" in artifacts
        assert "Main.cs" in artifacts
        assert "ReadEmails.cs" in artifacts
        assert "ExtractInvoiceData.cs" in artifacts

    @pytest.mark.asyncio
    async def test_developer_project_json_valid(self):
        state = {
            "messages": [],
            "sdd": SAMPLE_SDD,
            "project_name": "InvoiceProcessor",
        }
        result = await developer_node(state)

        proj = json.loads(result["artifacts"]["project.json"])
        assert proj["targetFramework"] == "Windows"
        assert proj["expressionLanguage"] == "CSharp"
        assert proj["name"] == "InvoiceProcessor"


# ── QA Node Tests ────────────────────────────────────────────


class TestQaNode:
    @pytest.mark.asyncio
    async def test_qa_passes_valid_artifacts(self):
        """QA should pass valid artifacts."""
        # First generate valid artifacts
        state = {"messages": [], "sdd": SAMPLE_SDD, "project_name": "InvoiceProcessor"}
        dev_result = await developer_node(state)

        qa_state = {
            "messages": [],
            "artifacts": dev_result["artifacts"],
            "qa_iterations": 0,
        }
        result = await qa_node(qa_state)

        assert result["validation_errors"] == []
        assert result["qa_report"]["passed"] is True

    @pytest.mark.asyncio
    async def test_qa_catches_missing_project_json(self):
        qa_state = {
            "messages": [],
            "artifacts": {"Main.cs": "// some code"},
            "qa_iterations": 0,
        }
        result = await qa_node(qa_state)

        assert len(result["validation_errors"]) > 0
        assert any("project.json" in e for e in result["validation_errors"])

    @pytest.mark.asyncio
    async def test_qa_catches_vb_syntax(self):
        bad_artifacts = {
            "project.json": json.dumps({
                "targetFramework": "Windows",
                "expressionLanguage": "CSharp",
            }),
            "Main.cs": "Dim x As String = \"hello\"",
        }
        qa_state = {"messages": [], "artifacts": bad_artifacts, "qa_iterations": 0}
        result = await qa_node(qa_state)

        assert len(result["validation_errors"]) > 0
        assert any("VB.Net" in e for e in result["validation_errors"])

    @pytest.mark.asyncio
    async def test_qa_catches_wrong_target(self):
        bad_artifacts = {
            "project.json": json.dumps({
                "targetFramework": "Portable",
                "expressionLanguage": "CSharp",
            }),
            "Main.cs": "using System;",
        }
        qa_state = {"messages": [], "artifacts": bad_artifacts, "qa_iterations": 0}
        result = await qa_node(qa_state)

        assert any("targetFramework" in e for e in result["validation_errors"])

    def test_validate_artifacts_directly(self):
        """Test the validation function directly."""
        good_artifacts = {
            "project.json": json.dumps({
                "targetFramework": "Windows",
                "expressionLanguage": "CSharp",
            }),
            "Main.cs": """using System;
namespace Company.Test {
    public class Main : CodedWorkflow {
        public void Execute() { }
    }
}""",
        }
        errors = _validate_artifacts(good_artifacts)
        assert errors == []

    @pytest.mark.asyncio
    async def test_qa_increments_iterations(self):
        qa_state = {
            "messages": [],
            "artifacts": {"Main.cs": "// code"},
            "qa_iterations": 0,
        }
        result = await qa_node(qa_state)
        assert result["qa_iterations"] == 1


# ── Routing Tests ────────────────────────────────────────────


class TestGraphRouting:
    def test_route_after_ba_to_sa(self):
        from agent.graph import route_after_ba
        state = {"pdd": SAMPLE_PDD, "needs_clarification": False}
        assert route_after_ba(state) == "sa"

    def test_route_after_ba_clarification(self):
        from agent.graph import route_after_ba
        from langgraph.graph import END
        state = {"needs_clarification": True}
        assert route_after_ba(state) == END

    def test_route_after_sa_to_developer(self):
        from agent.graph import route_after_sa
        state = {"requires_hitl": False}
        assert route_after_sa(state) == "developer"

    def test_route_after_sa_to_hitl(self):
        from agent.graph import route_after_sa
        state = {"requires_hitl": True}
        assert route_after_sa(state) == "hitl"

    def test_route_after_hitl_approved(self):
        from agent.graph import route_after_hitl
        state = {"hitl_approved": True}
        assert route_after_hitl(state) == "developer"

    def test_route_after_hitl_rejected(self):
        from agent.graph import route_after_hitl
        from langgraph.graph import END
        state = {"hitl_approved": False}
        assert route_after_hitl(state) == END

    def test_route_after_qa_passed(self):
        from agent.graph import route_after_qa
        from langgraph.graph import END
        state = {"validation_errors": [], "qa_iterations": 1}
        assert route_after_qa(state) == END

    def test_route_after_qa_failed_retry(self):
        from agent.graph import route_after_qa
        state = {"validation_errors": ["error"], "qa_iterations": 1}
        assert route_after_qa(state) == "developer"

    def test_route_after_qa_max_iterations(self):
        from agent.graph import route_after_qa
        from langgraph.graph import END
        state = {"validation_errors": ["error"], "qa_iterations": 2}
        assert route_after_qa(state) == END


# ── End-to-End Flow Test (mocked LLMs) ──────────────────────


class TestEndToEndFlow:
    @pytest.mark.asyncio
    async def test_full_bootstrap_no_hitl(self):
        """Test the full flow: BA -> SA -> Developer -> QA (no HITL)."""
        pdd_json = json.dumps(SAMPLE_PDD)
        sdd_json = json.dumps(SAMPLE_SDD)

        # Step 1: BA produces PDD
        with patch("agent.nodes.ba_persona.ba_llm") as mock_ba:
            mock_ba.ainvoke = AsyncMock(
                return_value=AIMessage(content=f"```json\n{pdd_json}\n```")
            )
            ba_state = {
                "messages": [HumanMessage(content="Process invoices from email to SAP")],
                "mode": "bootstrap",
                "current_phase": "ba",
            }
            ba_result = await ba_persona(ba_state)

        assert ba_result["pdd"] is not None
        assert ba_result["needs_clarification"] is False

        # Step 2: SA produces SDD (no HITL)
        with patch("agent.nodes.sa_persona.sa_llm") as mock_sa:
            mock_sa.ainvoke = AsyncMock(
                return_value=AIMessage(content=f"```json\n{sdd_json}\n```")
            )
            sa_state = {**ba_result, "messages": [], "pdd": ba_result["pdd"]}
            sa_result = await sa_persona(sa_state)

        assert sa_result["sdd"] is not None
        assert sa_result["requires_hitl"] is False

        # Step 3: Developer generates files
        dev_state = {
            "messages": [],
            "sdd": sa_result["sdd"],
            "project_name": sa_result.get("project_name", "InvoiceProcessor"),
        }
        dev_result = await developer_node(dev_state)

        assert "project.json" in dev_result["artifacts"]
        assert "Main.cs" in dev_result["artifacts"]

        # Step 4: QA validates
        qa_state = {
            "messages": [],
            "artifacts": dev_result["artifacts"],
            "qa_iterations": 0,
        }
        qa_result = await qa_node(qa_state)

        assert qa_result["validation_errors"] == []
        assert qa_result["qa_report"]["passed"] is True

        # Flow complete!
        print(f"\nEnd-to-end flow completed successfully!")
        print(f"  PDD: {ba_result['pdd']['process_name']}")
        print(f"  SDD: {sa_result['sdd']['project_name']}")
        print(f"  Artifacts: {list(dev_result['artifacts'].keys())}")
        print(f"  QA: PASSED")

    @pytest.mark.asyncio
    async def test_full_bootstrap_with_hitl(self):
        """Test the flow with HITL review step."""
        pdd_json = json.dumps(SAMPLE_PDD)
        complex_sdd = {**SAMPLE_SDD, "complexity": "complex", "hitl_reason": "Many activities"}
        sdd_json = json.dumps(complex_sdd)

        # BA
        with patch("agent.nodes.ba_persona.ba_llm") as mock_ba:
            mock_ba.ainvoke = AsyncMock(
                return_value=AIMessage(content=f"```json\n{pdd_json}\n```")
            )
            ba_result = await ba_persona({
                "messages": [HumanMessage(content="Process invoices")],
                "mode": "bootstrap",
                "current_phase": "ba",
            })

        # SA flags HITL
        with patch("agent.nodes.sa_persona.sa_llm") as mock_sa:
            mock_sa.ainvoke = AsyncMock(
                return_value=AIMessage(content=f"```json\n{sdd_json}\n```")
            )
            sa_result = await sa_persona({"messages": [], "pdd": ba_result["pdd"]})

        assert sa_result["requires_hitl"] is True

        # HITL approves
        hitl_result = await hitl_node({
            "messages": [HumanMessage(content="approved")],
            "sdd": sa_result["sdd"],
        })
        assert hitl_result["hitl_approved"] is True

        # Developer
        dev_result = await developer_node({
            "messages": [],
            "sdd": sa_result["sdd"],
            "project_name": "InvoiceProcessor",
        })

        # QA
        qa_result = await qa_node({
            "messages": [],
            "artifacts": dev_result["artifacts"],
            "qa_iterations": 0,
        })

        assert qa_result["validation_errors"] == []
        print(f"\nEnd-to-end flow with HITL completed successfully!")
