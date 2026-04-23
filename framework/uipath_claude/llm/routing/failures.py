"""Failure classifier for the fallback engine.

Distinguishes model-related provider failures (eligible for fallback) from
all other failures (not eligible). Pattern matches Bedrock-style errors but
is provider-agnostic.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class FailureCategory(str, Enum):
    UNSUPPORTED_THROUGHPUT = "unsupported_throughput"
    MODEL_NOT_FOUND = "model_not_found"
    ACCESS_DENIED_FOR_MODEL = "access_denied_for_model"
    RATE_LIMIT = "rate_limit"
    OTHER = "other"


@dataclass(frozen=True)
class ClassifiedFailure:
    category: FailureCategory
    model_related: bool
    hint: str | None = None


def _msg(error: BaseException | str) -> str:
    if isinstance(error, str):
        return error
    parts = [str(error)]
    response: Any = getattr(error, "response", None)
    if isinstance(response, dict):
        err = response.get("Error") or {}
        if isinstance(err, dict):
            code = err.get("Code")
            message = err.get("Message")
            if code:
                parts.append(str(code))
            if message:
                parts.append(str(message))
    return " | ".join(parts)


def classify_failure(error: BaseException | str) -> ClassifiedFailure:
    """Classify an error into a fallback-eligibility bucket."""
    text = _msg(error).lower()

    if "on-demand throughput isn" in text or "inference profile" in text:
        return ClassifiedFailure(
            FailureCategory.UNSUPPORTED_THROUGHPUT,
            True,
            "Model requires an inference profile id (e.g. 'us.<model>') or ARN.",
        )

    if (
        "model not found" in text
        or "could not be found" in text
        or "resourcenotfoundexception" in text
    ):
        return ClassifiedFailure(
            FailureCategory.MODEL_NOT_FOUND,
            True,
            "Verify the model id and region; fallback model will be tried.",
        )

    if "accessdenied" in text or "not authorized" in text or "access denied" in text:
        return ClassifiedFailure(
            FailureCategory.ACCESS_DENIED_FOR_MODEL,
            True,
            "Account/role lacks access to this model id; fallback will be tried.",
        )

    if (
        "throttling" in text
        or "too many requests" in text
        or ("rate" in text and "limit" in text)
    ):
        return ClassifiedFailure(FailureCategory.RATE_LIMIT, False)

    return ClassifiedFailure(FailureCategory.OTHER, False)
