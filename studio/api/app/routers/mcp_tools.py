"""MCP tool catalog endpoint for AgentOps Builder."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from framework.agentops_builder.mcp.registry import (
    PHASE_TOOL_PLAN_MAPPING,
    contracts_by_category,
)

router = APIRouter(prefix="/agentops/mcp", tags=["agentops"])


class MCPToolCatalogItem(BaseModel):
    tool_id: str
    label: str
    category: str
    risk_level: str
    approval_requirement: str
    evidence_output: str
    direct_call_policy: str
    demo_safe_action: bool


class MCPToolCatalogCategory(BaseModel):
    category: str
    tools: list[MCPToolCatalogItem] = Field(default_factory=list)


class MCPToolCatalogResponse(BaseModel):
    categories: list[MCPToolCatalogCategory]
    phase_tool_mapping: dict[str, list[str]]
    risk_levels: list[str]
    approval_requirements: list[str]
    demo_safe_actions: list[str]


@router.get("/tools", response_model=MCPToolCatalogResponse)
def get_mcp_tool_catalog() -> MCPToolCatalogResponse:
    grouped = contracts_by_category()
    categories: list[MCPToolCatalogCategory] = []
    risk_levels: set[str] = set()
    approval_requirements: set[str] = set()
    demo_safe_actions: list[str] = []

    for category_name in sorted(grouped):
        items: list[MCPToolCatalogItem] = []
        for contract in grouped[category_name]:
            risk_levels.add(contract.risk_level.value)
            approval_requirements.add(contract.approval_requirement.value)
            if contract.demo_safe_action:
                demo_safe_actions.append(contract.tool_id)
            items.append(
                MCPToolCatalogItem(
                    tool_id=contract.tool_id,
                    label=contract.label,
                    category=contract.category.value,
                    risk_level=contract.risk_level.value,
                    approval_requirement=contract.approval_requirement.value,
                    evidence_output=contract.evidence_output,
                    direct_call_policy=contract.direct_call_policy.value,
                    demo_safe_action=contract.demo_safe_action,
                )
            )
        categories.append(MCPToolCatalogCategory(category=category_name, tools=items))

    return MCPToolCatalogResponse(
        categories=categories,
        phase_tool_mapping={k: list(v) for k, v in PHASE_TOOL_PLAN_MAPPING.items()},
        risk_levels=sorted(risk_levels),
        approval_requirements=sorted(approval_requirements),
        demo_safe_actions=sorted(set(demo_safe_actions)),
    )

