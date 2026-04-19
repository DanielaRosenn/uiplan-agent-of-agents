"""Unified UiPath Ask AI / documentation query (SDK skill or HTTP endpoint)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
from langchain_core.tools import tool

from uipath_claude.tools._result import ToolOutcome


def _skills_askai_dir() -> Path:
    return (
        Path(__file__).resolve().parent.parent.parent.parent
        / "skills"
        / "skills"
        / "uipath-askai"
    )


def query_uipath_documentation(question: str) -> ToolOutcome:
    """
    Ask authoritative UiPath documentation: prefer bundled uipath-askai skill SDK,
    else HTTP endpoint from UIPATH_ASKAI_ENDPOINT (+ optional UIPATH_ASKAI_API_KEY).
    """
    skills_path = _skills_askai_dir()
    if skills_path.exists():
        sys.path.insert(0, str(skills_path))
        try:
            from uipath_askai_client import UiPathAskAIClient

            config_path = skills_path / "uipath_askai_config.json"
            if not config_path.exists():
                return ToolOutcome(
                    ok=False,
                    message=(
                        "uipath_askai_config.json not configured. "
                        "See skills/skills/uipath-askai/UIPATH_ASKAI_SETUP.md"
                    ),
                )

            client = UiPathAskAIClient(str(config_path))
            result = client.ask(question)

            if result.get("success"):
                return ToolOutcome(ok=True, message=client.format_response(result))
            return ToolOutcome(
                ok=False,
                message=f"Error querying UiPath docs: {result.get('error', 'Unknown error')}",
            )
        except ImportError as e:
            return ToolOutcome(ok=False, message=f"Error importing UiPath Ask AI client: {e}")
        except Exception as e:
            return ToolOutcome(ok=False, message=f"Error querying UiPath docs: {e}")
        finally:
            if str(skills_path) in sys.path:
                sys.path.remove(str(skills_path))

    endpoint = os.getenv("UIPATH_ASKAI_ENDPOINT", "").strip()
    api_key = os.getenv("UIPATH_ASKAI_API_KEY", "").strip()
    if not endpoint:
        return ToolOutcome(
            ok=False,
            message=(
                "UiPath Ask AI not available: install skills/skills/uipath-askai/ "
                "or set UIPATH_ASKAI_ENDPOINT (and UIPATH_ASKAI_API_KEY if required). "
                "For local smoke verification set "
                "UIPATH_ASKAI_ENDPOINT=mock://localfixture."
            ),
        )

    if endpoint.startswith("mock://"):
        fixture = endpoint[len("mock://"):] or "localfixture"
        body = (
            f"[mock askai] question={question!r}\n"
            f"This is a deterministic local fixture response from the\n"
            f"`mock://{fixture}` endpoint. Configure UIPATH_ASKAI_ENDPOINT to a\n"
            f"real Ask AI URL for production answers.\n"
            f"SOURCE: askai-mock"
        )
        return ToolOutcome(ok=True, message=body)

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    payload = {"query": question}
    try:
        response = httpx.post(endpoint, json=payload, headers=headers, timeout=60.0)
        response.raise_for_status()
        data = response.json()
        text = str(data.get("answer") or data.get("result") or data)
        return ToolOutcome(ok=True, message=text)
    except Exception as exc:
        return ToolOutcome(ok=False, message=f"AskAI HTTP request failed: {exc}")


@tool
def uipath_askai_tool(query: str) -> str:
    """Query UiPath documentation via unified Ask AI (SDK or HTTP)."""
    return query_uipath_documentation(query).to_text()
