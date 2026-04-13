"""Test input routing logic."""

from uipath_claude.query.router import route_user_input


def test_route_slash_command():
    """Route /help as command."""
    route, payload = route_user_input("/help")
    assert route == "command"
    assert payload["command"] == "help"


def test_route_skill_invocation():
    """Route /skill invocation with name and query."""
    route, payload = route_user_input("/skill sample-skill build invoice flow")
    assert route == "skill"
    assert payload["skill_name"] == "sample-skill"
    assert payload["query"] == "build invoice flow"


def test_route_skill_usage_when_missing_args():
    """Route malformed skill invocation to usage path."""
    route, _payload = route_user_input("/skill sample-skill")
    assert route == "skill_usage"


def test_route_skill_usage_for_bare_skill_command():
    """Route bare /skill command to usage path."""
    route, _payload = route_user_input("/skill")
    assert route == "skill_usage"


def test_route_regular_text_to_llm():
    """Route plain text to llm handler."""
    route, payload = route_user_input("hello")
    assert route == "llm"
    assert payload["text"] == "hello"


def test_route_ambiguous_prompt_to_clarification():
    """Route vague requests to clarification flow."""
    route, payload = route_user_input("help me with this")
    assert route == "clarification"
    assert "clarify" in payload["question"].lower()


def test_route_vague_domain_prompt_to_clarification():
    """Route domain-only but vague prompts to clarification flow."""
    route, payload = route_user_input("help with excel")
    assert route == "clarification"
    assert "clarify" in payload["question"].lower()

