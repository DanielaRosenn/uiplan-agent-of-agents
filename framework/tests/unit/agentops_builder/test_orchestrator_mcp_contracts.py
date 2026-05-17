from __future__ import annotations

from framework.agentops_builder.mcp.orchestrator_integration import (
    APPROVAL_GATED_ACTION_WRAPPERS,
    READ_ONLY_WRAPPERS,
    is_non_prod_target,
    redact_payload,
    wrap_action_call,
    wrap_read_only_call,
)


def test_orchestrator_wrapper_lists_present() -> None:
    assert READ_ONLY_WRAPPERS
    assert APPROVAL_GATED_ACTION_WRAPPERS


def test_redaction_scrubs_sensitive_fields() -> None:
    payload = {
        "token": "abc",
        "nested": {"client_secret": "def", "ok": "value"},
        "items": [{"authorization": "ghi"}],
    }
    redacted = redact_payload(payload)
    assert redacted["token"] == "***REDACTED***"
    assert redacted["nested"]["client_secret"] == "***REDACTED***"
    assert redacted["nested"]["ok"] == "value"
    assert redacted["items"][0]["authorization"] == "***REDACTED***"


def test_read_only_wrappers_are_ready_without_approval() -> None:
    wrapped = wrap_read_only_call("orchestrator.list_jobs", {"token": "abc"})
    assert wrapped.approval_required is False
    assert wrapped.readiness.ready is True
    assert wrapped.payload["token"] == "***REDACTED***"


def test_action_wrapper_blocks_without_explicit_approval() -> None:
    wrapped = wrap_action_call(
        "orchestrator.start_job",
        {"job": "invoice"},
        folder="Shared-Dev",
        approved=False,
    )
    assert wrapped.approval_required is True
    assert wrapped.readiness.ready is False
    assert wrapped.readiness.blocked_reason


def test_action_wrapper_blocks_prod_target_even_with_approval() -> None:
    wrapped = wrap_action_call(
        "orchestrator.start_job",
        {"job": "invoice"},
        folder="Production Finance",
        approved=True,
    )
    assert wrapped.readiness.ready is False
    assert wrapped.readiness.non_prod_target is False


def test_is_non_prod_target_token_aware_detection() -> None:
    assert is_non_prod_target("product-team-dev") is True
    assert is_non_prod_target("Shared Dev") is True
    assert is_non_prod_target("non-prod-shared") is True
    assert is_non_prod_target("Production Finance") is False
    assert is_non_prod_target("shared_prod") is False

