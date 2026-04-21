"""Tests for intent_classifier."""

import pytest

from uipath_claude.query.intent_classifier import IntentType, classify_intent


@pytest.mark.parametrize(
    "text,expected,reason_substr",
    [
        ("What is UiPath Orchestrator?", IntentType.QUESTION, "question"),
        ("How does the queue work?", IntentType.QUESTION, "question"),
        ("Create an Outlook workflow that reads email", IntentType.BUILD, "build"),
        ("Build a dispatcher", IntentType.BUILD, "build"),
        ("automate", IntentType.AMBIGUOUS, "vague"),
        ("help", IntentType.AMBIGUOUS, "vague"),
        ("Automate my email.", IntentType.AMBIGUOUS, "vague"),
        ("automate my email", IntentType.AMBIGUOUS, "vague"),
        (
            "Explain in bullet points what belongs in a minimal UiPath Studio "
            "project.json for a Windows VB workflow project, and what Main.xaml is for.",
            IntentType.QUESTION,
            "question",
        ),
        ("Explain what project.json contains", IntentType.QUESTION, "question"),
        ("What is Main.xaml for?", IntentType.QUESTION, "question"),
        (
            "can you read an sdd and build a project according to it?",
            IntentType.BUILD,
            "build",
        ),
        ("create a sdd for invoice processing", IntentType.DOCUMENTATION, "doc"),
        ("what is an sdd?", IntentType.QUESTION, "question"),
        ("use the pdd to build the agent", IntentType.BUILD, "build"),
        (
            "can you help me build a project if i provide with sdd?",
            IntentType.QUESTION,
            "capability",
        ),
        ("could you explain how queues work?", IntentType.QUESTION, "capability"),
        ("are you able to read an SDD?", IntentType.QUESTION, "capability"),
        ("can you build a dispatcher", IntentType.BUILD, "build"),
        ("do we have this in books?", IntentType.QUESTION, "question"),
        ("is there a sample for invoices?", IntentType.QUESTION, "question"),
        ("where is the planner skill?", IntentType.QUESTION, "question"),
        ("which book contains retry patterns?", IntentType.QUESTION, "question"),
        ("does the library have a chapter on triggers?", IntentType.QUESTION, "question"),
        ("build a workflow that sends email", IntentType.BUILD, "build"),
        ("create a pdd", IntentType.DOCUMENTATION, "doc"),
        ("random unparseable noun phrase here", IntentType.AMBIGUOUS, "default"),
        (
            "what's coreipc?https://github.com/UiPath/coreipc",
            IntentType.QUESTION,
            "question",
        ),
        ("what's coreipc?", IntentType.QUESTION, "question"),
        ("who's the owner?", IntentType.QUESTION, "question"),
        ("tell me about orchestrator", IntentType.QUESTION, "question"),
        ("create an invoice processor", IntentType.BUILD, "build"),
        ("build X and write Y", IntentType.BUILD, "build"),
        ("did you create the project?", IntentType.QUESTION, "status_question"),
        ("did you build the workflow?", IntentType.QUESTION, "status_question"),
        ("have you created the project?", IntentType.QUESTION, "status_question"),
        ("have you built the workflow?", IntentType.QUESTION, "status_question"),
        ("was the project created?", IntentType.QUESTION, "status_question"),
    ],
)
def test_classify_intent(text: str, expected: IntentType, reason_substr: str) -> None:
    intent, reason = classify_intent(text)
    assert intent == expected
    assert reason_substr in reason
