"""Secret redaction rules for BUILD_LOG.md audit entries.

Rules are intentionally conservative: prefer redacting too much over leaking secrets
into the per-project audit trail.
"""
from __future__ import annotations

import re
from typing import Iterable

_REDACTED = "***REDACTED***"

# Argv flag patterns whose VALUE (next argv item, or =value) must be masked.
_SECRET_FLAGS: tuple[str, ...] = (
    "--password",
    "--client-secret",
    "--token",
    "--access-token",
    "--refresh-token",
    "--api-key",
    "--connection-string",
    "--sql-connection-string",
    "--input-arguments",
)

# Substring matchers (case-insensitive) inside free-text values.
_SECRET_KEY_HINTS: tuple[str, ...] = (
    "password=",
    "pwd=",
    "client_secret",
    "clientsecret",
    "x-api-key",
    "authorization:",
    "bearer ",
    "apikey=",
    "api_key=",
    "user id=",
    "uid=",
    "trusted_connection=false",
)

# Regexes that mask secrets inside multi-line text payloads.
_SECRET_REGEXES: tuple[re.Pattern[str], ...] = (
    re.compile(r"(Password\s*=\s*)([^;\s\"']+)", re.IGNORECASE),
    re.compile(r"(Pwd\s*=\s*)([^;\s\"']+)", re.IGNORECASE),
    re.compile(r"(User\s*Id\s*=\s*)([^;\s\"']+)", re.IGNORECASE),
    re.compile(r"(Uid\s*=\s*)([^;\s\"']+)", re.IGNORECASE),
    re.compile(r"(Bearer\s+)([A-Za-z0-9._\-]+)"),
    re.compile(r"(\"sqlConnectionString\"\s*:\s*\")([^\"]*)(\")"),
    re.compile(r"(client_secret\s*=\s*)([^&\s\"']+)", re.IGNORECASE),
)


def redact_argv(argv: Iterable[str]) -> list[str]:
    """Return a copy of argv with secret-bearing flag values masked."""
    out: list[str] = []
    items = list(argv)
    i = 0
    while i < len(items):
        token = items[i]
        # --flag=value style
        matched = False
        for flag in _SECRET_FLAGS:
            if token == flag and i + 1 < len(items):
                out.append(token)
                out.append(_REDACTED)
                i += 2
                matched = True
                break
            if token.startswith(flag + "="):
                out.append(f"{flag}={_REDACTED}")
                i += 1
                matched = True
                break
        if matched:
            continue
        # Hint-based scrub for inline strings (e.g. a connection string passed as a positional arg)
        out.append(redact_text(token))
        i += 1
    return out


def redact_text(text: str) -> str:
    """Mask secrets inside arbitrary text (stdout/stderr/argv values)."""
    if not text:
        return text
    redacted = text
    for pattern in _SECRET_REGEXES:
        redacted = pattern.sub(lambda m: _mask_match(m), redacted)
    lower = redacted.lower()
    if any(hint in lower for hint in _SECRET_KEY_HINTS):
        # Keep the line shape but flag the hit; downstream readers will know
        # to look at the original via a privileged channel.
        return f"{redacted}  [secret-hint]"
    return redacted


def _mask_match(match: re.Match[str]) -> str:
    groups = match.groups()
    if len(groups) == 2:
        return f"{groups[0]}{_REDACTED}"
    if len(groups) == 3:
        return f"{groups[0]}{_REDACTED}{groups[2]}"
    return _REDACTED
