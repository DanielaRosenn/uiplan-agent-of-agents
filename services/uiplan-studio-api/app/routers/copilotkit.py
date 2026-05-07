from __future__ import annotations

from fastapi import APIRouter, Request

from app.copilot_runtime import (
    copilot_generate_response_payload,
    copilot_info_payload,
)

router = APIRouter()


@router.get("/copilotkit/info")
def copilotkit_info_endpoint() -> dict:
    return copilot_info_payload()


@router.get("/copilotkit")
def copilotkit_runtime_info() -> dict:
    return copilot_info_payload()


@router.post("/copilotkit")
async def copilotkit_runtime(request: Request) -> dict:
    body = await request.json()
    method = str(body.get("method", ""))
    operation = str(body.get("operationName", ""))

    if method == "info":
        return copilot_info_payload()

    if operation in {"AvailableAgents", "availableAgents"}:
        agents = copilot_info_payload().get("agents", {})
        available_agents = (
            [
                {"id": agent_id, "name": agent_id, **metadata}
                for agent_id, metadata in agents.items()
            ]
            if isinstance(agents, dict)
            else agents
        )
        return {"data": {"availableAgents": {"agents": available_agents}}}

    if operation in {"LoadAgentState", "loadAgentState"}:
        variables = body.get("variables", {})
        data = variables.get("data", {}) if isinstance(variables, dict) else {}
        thread_id = body.get("threadId") or data.get("threadId") or "local"
        return {
            "data": {
                "loadAgentState": {
                    "threadId": thread_id,
                    "threadExists": False,
                    "state": {},
                    "messages": [],
                }
            }
        }

    if operation in {"GenerateCopilotResponse", "generateCopilotResponse"}:
        return {
            "data": {
                "generateCopilotResponse": copilot_generate_response_payload()
            }
        }

    return {"data": {}}
