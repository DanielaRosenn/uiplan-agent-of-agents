"""Tests for documentation need detection."""

import pytest
from uipath_claude.query.intent_classifier import IntentType, classify_intent


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
