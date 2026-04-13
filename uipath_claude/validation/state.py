"""Validation state contract for generated project checks."""

from dataclasses import dataclass, field


@dataclass
class ValidationState:
    """Normalized validation state for project validation results."""

    success: bool = False
    fully_validated: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    project_path: str = ""
