"""Tests for session history search."""

from uipath_claude.query.session_search import search_session_history


def test_search_session_history_returns_empty_for_empty_query():
    """Return no results when query is empty."""
    history = [{"role": "user", "content": "hello"}]
    assert search_session_history(history, "") == []
    assert search_session_history(history, "   ") == []


def test_search_session_history_is_case_insensitive():
    """Match search query regardless of case."""
    history = [
        {"role": "user", "content": "Build an Invoice BOT"},
        {"role": "assistant", "content": "Sure, here is the bot design."},
    ]

    result = search_session_history(history, "bot")
    assert len(result) == 2


def test_search_session_history_returns_recent_matches_first_and_honors_limit():
    """Return latest matches first with the provided limit."""
    history = [
        {"role": "user", "content": "first invoice step"},
        {"role": "assistant", "content": "second invoice step"},
        {"role": "user", "content": "third invoice step"},
        {"role": "assistant", "content": "final note"},
    ]

    result = search_session_history(history, "invoice", limit=2)
    assert result == [
        {"role": "user", "content": "third invoice step"},
        {"role": "assistant", "content": "second invoice step"},
    ]


def test_search_session_history_returns_empty_when_limit_is_zero():
    """Return no results when limit is zero."""
    history = [
        {"role": "user", "content": "invoice reminder"},
        {"role": "assistant", "content": "invoice response"},
    ]

    assert search_session_history(history, "invoice", limit=0) == []


def test_search_session_history_returns_empty_when_limit_is_negative():
    """Return no results when limit is negative."""
    history = [
        {"role": "user", "content": "invoice reminder"},
        {"role": "assistant", "content": "invoice response"},
    ]

    assert search_session_history(history, "invoice", limit=-2) == []
