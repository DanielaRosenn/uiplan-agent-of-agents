"""Integration tests for documentation-driven development flow."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from uipath_claude.query.intent_classifier import classify_intent, IntentType
from uipath_claude.query.doc_need_detector import detect_documentation_need, DocNeedLevel
from uipath_claude.query.doc_router import route_to_doc_agent


class TestDocumentationFlowIntegration:
    """Integration tests for the full documentation flow."""

    def test_pdd_request_classifies_correctly(self):
        """PDD request should classify as DOCUMENTATION intent."""
        intent, reason = classify_intent("Create a PDD for invoice processing")
        assert intent == IntentType.DOCUMENTATION

    def test_pdd_request_detects_need(self):
        """PDD request should detect documentation need."""
        need = detect_documentation_need("Create a PDD for invoice processing")
        assert need.explicit_request is True
        assert "pdd" in need.recommended_docs
        assert need.level == DocNeedLevel.REQUIRED

    @pytest.mark.asyncio
    async def test_pdd_request_routes_to_ba(self):
        """PDD request should route to BA agent."""
        decision = await route_to_doc_agent(
            user_input="Create a PDD for invoice processing",
            recommended_docs=["pdd"],
        )
        assert decision.agent == "ba"
        assert decision.doc_type == "pdd"

    def test_complex_project_detects_multiple_docs(self):
        """Complex project should recommend multiple doc types."""
        need = detect_documentation_need(
            "Build enterprise invoice processing with SAP integration, "
            "manager approvals, compliance audit trail, and AI-based data extraction"
        )
        assert need.level in (DocNeedLevel.REQUIRED, DocNeedLevel.RECOMMENDED)
        assert len(need.recommended_docs) >= 2

    @pytest.mark.asyncio
    async def test_doc_flow_creates_pdd_before_sdd(self):
        """Flow should create PDD before SDD."""
        decision = await route_to_doc_agent(
            user_input="Create full documentation",
            recommended_docs=["pdd", "sdd", "tdd"],
        )
        assert decision.doc_type == "pdd"
        assert "sdd" in decision.next_docs
        assert "tdd" in decision.next_docs

    @pytest.mark.asyncio
    async def test_skips_existing_docs(self, tmp_path):
        """Should skip docs that already exist."""
        # Create existing PDD
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "pdd.md").write_text("# Existing PDD")
        
        decision = await route_to_doc_agent(
            user_input="Create documentation",
            recommended_docs=["pdd", "sdd"],
            project_dir=str(tmp_path),
        )
        # Should skip PDD and go to SDD
        assert decision.doc_type == "sdd"
        assert decision.agent == "sa"

    def test_simple_build_not_documentation(self):
        """Simple build request should not be classified as documentation."""
        intent, _ = classify_intent("Create a workflow that sends an email")
        assert intent != IntentType.DOCUMENTATION
        
        need = detect_documentation_need("Create a workflow that sends an email")
        assert need.level == DocNeedLevel.NONE

    @pytest.mark.asyncio
    async def test_sdd_request_routes_to_sa(self):
        """SDD request should route to SA agent."""
        decision = await route_to_doc_agent(
            user_input="Create an SDD for the system",
            recommended_docs=["sdd"],
        )
        assert decision.agent == "sa"
        assert decision.doc_type == "sdd"

    @pytest.mark.asyncio
    async def test_add_request_routes_to_sa(self):
        """ADD request should route to SA agent."""
        decision = await route_to_doc_agent(
            user_input="Create an Agent Design Document",
            recommended_docs=["add"],
        )
        assert decision.agent == "sa"
        assert decision.doc_type == "add"

    def test_agentic_project_suggests_add(self):
        """Project with AI components should suggest ADD."""
        need = detect_documentation_need(
            "Create an AI agent that uses Claude to analyze invoices and make decisions"
        )
        assert "add" in need.recommended_docs
