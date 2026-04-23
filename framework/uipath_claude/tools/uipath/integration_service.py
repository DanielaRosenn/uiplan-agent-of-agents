"""Integration Service connector smoke checks via UiPath CLI (when available)."""
from __future__ import annotations

import os
import shlex
import subprocess


def run_integration_service_connector_check() -> str:
    """
    Run a lightweight Integration Service / cloud connector check.

    Set UIPATH_INTEGRATION_SERVICE_CHECK_CMD to a full shell command (split with shlex)
    to override candidate subcommands for your CLI version.
    """
    custom = os.environ.get("UIPATH_INTEGRATION_SERVICE_CHECK_CMD")
    candidates: list[list[str]] = []
    if custom:
        candidates.append(shlex.split(custom))
    candidates.extend(
        [
            ["uipath", "integration", "connection", "list"],
            ["uipath", "integrations", "list"],
            ["uipath", "config"],
        ]
    )

    last_output = ""
    for cmd in candidates:
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=45,
                check=False,
            )
        except FileNotFoundError:
            return (
                "uipath CLI not found on PATH. Install UiPath CLI and authenticate, "
                "e.g. uipath auth --tenant Test"
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            last_output = str(exc)
            continue

        combined = "\n".join(
            p for p in (proc.stdout or "", proc.stderr or "") if p.strip()
        ).strip()
        if proc.returncode == 0 and combined:
            return f"OK ({' '.join(cmd)}):\n{combined[:2000]}"
        if combined:
            last_output = combined[:800]

    return (
        "Integration Service connector CLI check did not return a success output. "
        "Authenticate with uipath auth --tenant Test, or set "
        "UIPATH_INTEGRATION_SERVICE_CHECK_CMD to a working command for your CLI. "
        f"Last output: {last_output or 'none'}"
    )
