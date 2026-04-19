"""Tests for uipath_claude.llm.routing.failures."""
from __future__ import annotations

from uipath_claude.llm.routing.failures import FailureCategory, classify_failure


def test_unsupported_throughput_is_model_related():
    msg = (
        "An error occurred (ValidationException): Invocation of model ID "
        "anthropic.claude-sonnet-4-5-20250929-v1:0 with on-demand throughput isn't supported."
    )
    result = classify_failure(msg)
    assert result.category is FailureCategory.UNSUPPORTED_THROUGHPUT
    assert result.model_related is True
    assert result.hint and "inference profile" in result.hint


def test_model_not_found_is_model_related():
    result = classify_failure("ResourceNotFoundException: model not found")
    assert result.category is FailureCategory.MODEL_NOT_FOUND
    assert result.model_related is True


def test_access_denied_is_model_related():
    result = classify_failure("AccessDeniedException: not authorized to invoke model")
    assert result.category is FailureCategory.ACCESS_DENIED_FOR_MODEL
    assert result.model_related is True


def test_rate_limit_is_not_model_related():
    result = classify_failure("ThrottlingException: too many requests")
    assert result.category is FailureCategory.RATE_LIMIT
    assert result.model_related is False


def test_unknown_error_classified_as_other():
    result = classify_failure("Some weird parser error")
    assert result.category is FailureCategory.OTHER
    assert result.model_related is False


def test_classify_handles_exception_with_response_dict():
    class BotoLikeError(Exception):
        def __init__(self, code: str, message: str) -> None:
            super().__init__(message)
            self.response = {"Error": {"Code": code, "Message": message}}

    err = BotoLikeError(
        "ValidationException",
        "on-demand throughput isn't supported for this model",
    )
    result = classify_failure(err)
    assert result.category is FailureCategory.UNSUPPORTED_THROUGHPUT
    assert result.model_related is True
