"""Integration test bootstrap.

Auto-loads ``.env`` from the repo root before pytest evaluates ``pytest.mark.skipif``
marks on integration modules, and provides a fail-loud fixture that surfaces
``uip login`` state for end-to-end tests that talk to a real Orchestrator.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess

import pytest


def pytest_configure(config: pytest.Config) -> None:  # noqa: D401 - pytest hook
    """Populate environment from repo-root ``.env`` so integration skipif marks see it."""
    try:
        from uipath_claude.cli.app import _load_dotenv_from_cwd
    except Exception:
        return
    try:
        _load_dotenv_from_cwd()
    except Exception:
        # Best-effort: missing .env should not break collection.
        pass


@pytest.fixture(scope="module")
def uip_login_status() -> dict:
    """Return parsed ``uip login status --output json`` payload.

    Skips the test if ``uip`` is not on PATH.
    """
    uip_path = shutil.which("uip")
    if uip_path is None:
        pytest.skip("uip CLI not installed")

    try:
        proc = subprocess.run(
            [uip_path, "login", "status", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            shell=False,
        )
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"uip login status failed to execute: {exc}")

    raw = (proc.stdout or "") + "\n" + (proc.stderr or "")
    payload: dict = {}
    # uip emits a JSON envelope but may surround it with TLS warnings/log lines.
    # Use raw_decode at every '{' to ignore both leading and trailing junk.
    decoder = json.JSONDecoder()
    idx = 0
    while idx < len(raw):
        i = raw.find("{", idx)
        if i < 0:
            break
        try:
            payload, _ = decoder.raw_decode(raw[i:])
            break
        except Exception:  # noqa: BLE001
            idx = i + 1
    if not isinstance(payload, dict):
        payload = {}
    payload.setdefault("_returncode", proc.returncode)
    payload.setdefault("_raw", raw[:1500])
    return payload


@pytest.fixture
def auth_required(uip_login_status: dict) -> dict:
    """Fail loud if uip auth is missing or expired (no silent skip)."""
    data = uip_login_status.get("Data") or uip_login_status.get("data") or {}
    status = (
        (data.get("Status") if isinstance(data, dict) else None)
        or uip_login_status.get("Status")
        or ""
    )
    if str(status).lower() != "loggedin":
        pytest.fail(
            "uip login is missing or expired (status="
            f"{status!r}). Run `uip login -t Test --interactive` and retry. "
            f"Raw: {uip_login_status.get('_raw', '')[:400]}"
        )

    url = os.environ.get("UIPATH_ORCHESTRATOR_URL", "").strip()
    if not url or "YOUR_ACCOUNT" in url:
        pytest.fail(
            "UIPATH_ORCHESTRATOR_URL is empty or still a placeholder "
            f"({url!r}). Set it in .env to the real Test tenant URL."
        )
    return uip_login_status
