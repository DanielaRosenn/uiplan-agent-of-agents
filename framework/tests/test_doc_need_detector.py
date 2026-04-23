"""Tests for documentation need detection."""

import pytest
from uipath_claude.query.intent_classifier import IntentType, classify_intent
from uipath_claude.query.doc_need_detector import (
    DocNeedLevel,
    detect_documentation_need,
    ComplexityIndicators,
)


class TestDocNeedDetector:
    """Tests for documentation need detection based on project complexity."""

    def test_simple_workflow_no_doc_needed(self):
        """Simple workflow should not require documentation."""
        result = detect_documentation_need("Send an email with attachment")
        assert result.level == DocNeedLevel.NONE
        assert result.recommended_docs == []

    def test_integration_suggests_sdd(self):
        """Integration with external system suggests SDD."""
        result = detect_documentation_need(
            "Create workflow that reads from Salesforce and updates SAP"
        )
        assert result.level in (DocNeedLevel.RECOMMENDED, DocNeedLevel.REQUIRED)
        assert "sdd" in result.recommended_docs

    def test_human_approval_suggests_pdd(self):
        """Human-in-the-loop suggests PDD."""
        result = detect_documentation_need(
            "Build invoice processing with manager approval for amounts over 10k"
        )
        assert result.level in (DocNeedLevel.RECOMMENDED, DocNeedLevel.REQUIRED)
        assert "pdd" in result.recommended_docs

    def test_agentic_workflow_suggests_add(self):
        """AI/Agent components suggest ADD."""
        result = detect_documentation_need(
            "Create an AI agent that analyzes documents and makes decisions"
        )
        assert "add" in result.recommended_docs

    def test_enterprise_project_requires_full_docs(self):
        """Enterprise-scale project requires full documentation."""
        result = detect_documentation_need(
            "Build enterprise invoice processing system with SAP integration, "
            "Salesforce CRM sync, manager approvals, compliance reporting, "
            "multi-department routing, and audit trail"
        )
        assert result.level == DocNeedLevel.REQUIRED
        assert "pdd" in result.recommended_docs
        assert "sdd" in result.recommended_docs

    def test_explicit_doc_type_requested(self):
        """Explicit doc request returns that doc type."""
        result = detect_documentation_need("Create a PDD for this process")
        assert result.level == DocNeedLevel.REQUIRED
        assert "pdd" in result.recommended_docs
        assert result.explicit_request is True

    def test_complexity_indicators_detected(self):
        """Should detect various complexity indicators."""
        result = detect_documentation_need(
            "Build workflow with Oracle database, REST API, exception handling, "
            "retry logic, and notification system"
        )
        indicators = result.indicators
        assert indicators.has_integration is True
        assert indicators.has_error_handling is True


class TestDocumentationIntent:
    """Tests for documentation-related intent classification."""

    def test_explicit_pdd_request(self):
        """Explicit PDD request should return DOCUMENTATION intent."""
        intent, reason = classify_intent("Create a PDD for invoice processing")
        assert intent == IntentType.DOCUMENTATION
        assert "pdd" in reason.lower() or "documentation" in reason.lower() or "doc" in reason.lower()

    def test_explicit_sdd_request(self):
        """Explicit SDD request should return DOCUMENTATION intent."""
        intent, reason = classify_intent("I need an SDD for this automation")
        assert intent == IntentType.DOCUMENTATION

    def test_help_me_document_request(self):
        """Help me document request should return DOCUMENTATION intent."""
        intent, reason = classify_intent("Help me document this process")
        assert intent == IntentType.DOCUMENTATION

    def test_process_definition_request(self):
        """Process definition request should return DOCUMENTATION intent."""
        intent, reason = classify_intent("I need to create a process definition")
        assert intent == IntentType.DOCUMENTATION

    def test_technical_design_request(self):
        """Technical design request should return DOCUMENTATION intent."""
        intent, reason = classify_intent("Create a technical design document")
        assert intent == IntentType.DOCUMENTATION

    def test_simple_build_not_documentation(self):
        """Simple build request should NOT return DOCUMENTATION."""
        intent, _ = classify_intent("Create a workflow that sends an email")
        assert intent != IntentType.DOCUMENTATION

    def test_add_button_not_documentation(self):
        """Add button request should NOT return DOCUMENTATION (avoid false positive on 'add')."""
        intent, _ = classify_intent("Add a button to the form")
        assert intent != IntentType.DOCUMENTATION
        assert intent == IntentType.BUILD
