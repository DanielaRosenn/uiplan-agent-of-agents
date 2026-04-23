"""Detect when a project requires documentation based on complexity and scope."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class DocNeedLevel(str, Enum):
    """Level of documentation need."""
    
    NONE = "none"
    OPTIONAL = "optional"
    RECOMMENDED = "recommended"
    REQUIRED = "required"


@dataclass
class ComplexityIndicators:
    """Indicators of project complexity."""
    
    has_integration: bool = False
    has_human_approval: bool = False
    has_agentic_component: bool = False
    has_error_handling: bool = False
    has_compliance: bool = False
    has_multi_system: bool = False
    has_data_transformation: bool = False
    integration_count: int = 0
    
    @property
    def complexity_score(self) -> int:
        """Calculate overall complexity score (0-10)."""
        score = 0
        if self.has_integration:
            score += 2
        if self.has_human_approval:
            score += 4  # Human approval is a strong indicator of process complexity
        if self.has_agentic_component:
            score += 3
        if self.has_error_handling:
            score += 1
        if self.has_compliance:
            score += 2
        if self.has_multi_system:
            score += 2
        if self.has_data_transformation:
            score += 1
        score += min(self.integration_count, 3)
        return min(score, 10)


@dataclass
class DocNeedResult:
    """Result of documentation need detection."""
    
    level: DocNeedLevel
    recommended_docs: list[str] = field(default_factory=list)
    indicators: ComplexityIndicators = field(default_factory=ComplexityIndicators)
    explicit_request: bool = False
    reason: str = ""


# Patterns for detecting complexity indicators
# Named systems are counted individually for integration_count
_NAMED_SYSTEM_PATTERN = r"\b(salesforce|sap|oracle|servicenow|dynamics|workday|jira|confluence|mongodb|postgres|mysql)\b"

_INTEGRATION_PATTERNS = (
    r"\b(salesforce|sap|oracle|servicenow|dynamics|workday|jira|confluence)\b",
    r"\b(api|rest|soap|graphql|webhook)\b",
    r"\b(database|sql|mongodb|postgres|mysql)\b",
    r"\b(integration|connect|sync)\b",
)

_APPROVAL_PATTERNS = (
    r"\b(approv|review|sign.?off|authorize|confirm)\b",
    r"\b(manager|supervisor|human|manual)\b",
    r"\b(action.?center|hitl|human.?in.?the.?loop)\b",
)

_AGENTIC_PATTERNS = (
    r"\b(ai|agent|llm|gpt|claude|intelligent|ml|machine.?learning)\b",
    r"\b(decision|analyze|classify|predict|recommend)\b",
    r"\b(langchain|langgraph|openai|anthropic|bedrock)\b",
)

_ERROR_PATTERNS = (
    r"\b(error|exception|retry|fallback|recover)\b",
    r"\b(handle|catch|throw|fail)\b",
)

_COMPLIANCE_PATTERNS = (
    r"\b(compliance|audit|gdpr|hipaa|sox|pci|regulation)\b",
    r"\b(security|encrypt|sensitive|pii|phi)\b",
    r"\b(log|track|trace|report)\b",
)

_DOC_TYPE_PATTERNS = {
    "pdd": r"\b(pdd|process.?definition)\b",
    "sdd": r"\b(sdd|solution.?design)\b",
    "add": r"\b(add|agent.?design)\b",
    "tdd": r"\b(tdd|technical.?design)\b",
}


def _count_matches(text: str, patterns: tuple[str, ...]) -> int:
    """Count how many patterns match in text."""
    return sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))


def _detect_indicators(text: str) -> ComplexityIndicators:
    """Detect complexity indicators from user input."""
    lower = text.lower()
    
    # Count named systems individually (Salesforce, SAP, Oracle, etc.)
    named_systems = re.findall(_NAMED_SYSTEM_PATTERN, lower, re.IGNORECASE)
    named_system_count = len(named_systems)
    
    # Also check for generic integration patterns
    has_generic_integration = _count_matches(text, _INTEGRATION_PATTERNS) > 0
    
    # Integration count is the number of distinct named systems
    integration_count = max(named_system_count, 1 if has_generic_integration else 0)
    
    return ComplexityIndicators(
        has_integration=integration_count > 0 or has_generic_integration,
        has_human_approval=_count_matches(text, _APPROVAL_PATTERNS) > 0,
        has_agentic_component=_count_matches(text, _AGENTIC_PATTERNS) > 0,
        has_error_handling=_count_matches(text, _ERROR_PATTERNS) > 0,
        has_compliance=_count_matches(text, _COMPLIANCE_PATTERNS) > 0,
        has_multi_system=integration_count > 1,
        has_data_transformation="transform" in lower or "convert" in lower or "map" in lower,
        integration_count=integration_count,
    )


def _detect_explicit_doc_request(text: str) -> tuple[bool, list[str]]:
    """Check if user explicitly requested specific documentation."""
    lower = text.lower()
    requested = []
    
    for doc_type, pattern in _DOC_TYPE_PATTERNS.items():
        if re.search(pattern, lower, re.IGNORECASE):
            requested.append(doc_type)
    
    # Also check for generic documentation requests
    if re.search(r"\b(document|documentation)\b", lower):
        if not requested:
            requested.append("pdd")  # Default to PDD for business process docs
    
    return bool(requested), requested


def detect_documentation_need(user_input: str) -> DocNeedResult:
    """
    Detect whether a project requires documentation and which types.
    
    Args:
        user_input: The user's project description or request
        
    Returns:
        DocNeedResult with level, recommended docs, and indicators
    """
    indicators = _detect_indicators(user_input)
    explicit, explicit_docs = _detect_explicit_doc_request(user_input)
    
    if explicit:
        return DocNeedResult(
            level=DocNeedLevel.REQUIRED,
            recommended_docs=explicit_docs,
            indicators=indicators,
            explicit_request=True,
            reason="User explicitly requested documentation",
        )
    
    score = indicators.complexity_score
    recommended = []
    
    # Determine recommended doc types based on indicators
    if indicators.has_human_approval or indicators.has_compliance:
        recommended.append("pdd")
    
    if indicators.has_integration or indicators.has_multi_system:
        recommended.append("sdd")
    
    if indicators.has_agentic_component:
        recommended.append("add")
    
    # If multiple docs recommended, also suggest TDD
    if len(recommended) >= 2:
        recommended.append("tdd")
    
    # Determine level based on score
    if score >= 7:
        level = DocNeedLevel.REQUIRED
        reason = f"High complexity score ({score}/10) - documentation required"
    elif score >= 4:
        level = DocNeedLevel.RECOMMENDED
        reason = f"Moderate complexity ({score}/10) - documentation recommended"
    elif score >= 2:
        level = DocNeedLevel.OPTIONAL
        reason = f"Low complexity ({score}/10) - documentation optional"
    else:
        level = DocNeedLevel.NONE
        reason = "Simple project - no documentation needed"
        recommended = []
    
    return DocNeedResult(
        level=level,
        recommended_docs=recommended,
        indicators=indicators,
        explicit_request=False,
        reason=reason,
    )
