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
    ],
)
def test_classify_intent(text: str, expected: IntentType, reason_substr: str) -> None:
    intent, reason = classify_intent(text)
    assert intent == expected
    assert reason_substr in reason
