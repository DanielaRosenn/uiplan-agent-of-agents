"""Tests for feedback loop state and question detection."""

from uipath_claude.query.feedback_loop import (
    FeedbackLoop,
    detect_clarifying_question,
)


def test_feedback_loop_tracks_questions():
    loop = FeedbackLoop(max_questions=2)
    loop.record_question("What email provider?")
    assert loop.state.questions_asked == 1
    assert loop.state.awaiting_response is True
    assert loop.state.pending_question == "What email provider?"


def test_feedback_loop_max_questions():
    loop = FeedbackLoop(max_questions=2)
    loop.record_question("Q1")
    loop.record_response("A1")
    loop.record_question("Q2")
    loop.record_response("A2")
    assert loop.should_ask_more() is False


def test_feedback_loop_context_summary():
    loop = FeedbackLoop()
    loop.record_question("Q1")
    loop.record_response("A1")
    summary = loop.get_context_summary()
    assert "Q1" in summary and "A1" in summary


def test_feedback_loop_reset():
    loop = FeedbackLoop(max_questions=2)
    loop.record_question("Q")
    loop.reset()
    assert loop.state.questions_asked == 0
    assert loop.state.pending_question is None
    assert not loop.state.responses


def test_detect_clarifying_question_positive():
    text = "Which email provider would you like to use? Outlook or Gmail?"
    q = detect_clarifying_question(text)
    assert q is not None
    assert "?" in q


def test_detect_clarifying_question_negative_code():
    text = 'var x = a > b ? 1 : 2;'
    assert detect_clarifying_question(text) is None


def test_detect_clarifying_question_plain_prose_no_question():
    text = "Here is a summary of the workflow steps."
    assert detect_clarifying_question(text) is None
