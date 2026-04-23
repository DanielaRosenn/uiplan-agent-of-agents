"""End-to-end /pdd lifecycle for an RPA process: real publish + deploy.

Opt-in: requires ``UIPATH_RUN_DEPLOY_TESTS=1`` AND ``uip`` on PATH AND
``UIPATH_ORCHESTRATOR_URL`` to be set (i.e. an active ``uip login`` session).

The LLM is patched to return canned PDD/SDD/ADD/TDD/impl text so the test
exercises the lifecycle plumbing rather than the model. Scaffold, validate,
publish, and deploy are real.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from uipath_claude.query import pdd_lifecycle


pytestmark = pytest.mark.skipif(
    os.environ.get("UIPATH_RUN_DEPLOY_TESTS") != "1" or shutil.which("uip") is None,
    reason="set UIPATH_RUN_DEPLOY_TESTS=1 and have `uip` on PATH to run these",
)


def _stamp() -> str:
    return time.strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex[:6]


@pytest.mark.asyncio
async def test_pdd_lifecycle_e2e_rpa_publish_and_deploy(tmp_path: Path, auth_required):
    process_name = f"PddLifecycleSmokeRpa{_stamp()}"

    canned = AsyncMock(side_effect=[
        "# PDD\nbuild a hello world process",
        "# SDD\nsingle Sequence with WriteLine",
        "# ADD\nsingle workflow, no integrations",
        "# TDD\nrun Main.xaml; smoke test only",
        "# IMPL\nuse the scaffold's Main.xaml",
    ])

    folder = os.environ.get("UIPATH_DEFAULT_FOLDER") or os.environ.get("UIPATH_FOLDER_PATH") or "Shared"

    with patch.object(pdd_lifecycle, "invoke_agent_llm", new=canned):
        result = await pdd_lifecycle.run_pdd_lifecycle(
            "build a hello world process",
            project_type="process",
            deploy=True,
            folder=folder,
            output_root=tmp_path,
            process_name=process_name,
        )

    assert result.get("status") == "ok", result

    stages = result["stages"]
    assert stages["pdd"]["status"] == "ok"
    assert stages["scaffold"]["status"] == "ok"
    assert stages["validate"]["status"] == "ok"
    assert stages["publish"]["status"] == "ok"
    assert stages["deploy"]["status"] == "ok"

    proc = subprocess.run(
        ["uip", "or", "processes", "list", "--folder", folder, "--output", "json"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    combined = (proc.stdout or "") + (proc.stderr or "")
    assert process_name in combined, (
        f"expected {process_name} in `uip or processes list` output but did not find it.\n{combined[:2000]}"
    )
