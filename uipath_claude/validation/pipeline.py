"""Structural, activity, and Studio-backed validation for UiPath projects."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from uipath_claude.artifacts.materialize import (
    _locate_project_root,
    _validate_xaml_structure,
)
from uipath_claude.tools.uipath.cli_runner import run_uip_rpa_get_errors


@dataclass
class ValidationError:
    file: str
    line: int | None
    column: int | None
    code: str
    message: str
    severity: str
    category: str


@dataclass
class ValidationResult:
    valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    studio_ran: bool = False


class ValidationPipeline:
    """Run structural checks, optional activity validation, then ``uip rpa get-errors``."""

    MAX_FIX_ATTEMPTS = 5

    def _categorize_error(self, message: str) -> str:
        lower = message.lower()
        if "package" in lower or "nuget" in lower:
            return "package"
        if "type mismatch" in lower or "cannot convert" in lower:
            return "type"
        if "activity" in lower or "property" in lower:
            return "activity"
        if "xml" in lower or "parse" in lower:
            return "structure"
        return "logic"

    def _as_error(self, file: str, message: str, *, severity: str = "error") -> ValidationError:
        return ValidationError(
            file=file,
            line=None,
            column=None,
            code="",
            message=message,
            severity=severity,
            category=self._categorize_error(message),
        )

    def _run_structural_checks(
        self, project_path: Path, file_path: Path | None
    ) -> ValidationResult:
        errors: list[ValidationError] = []
        xamls = [file_path] if file_path and file_path.suffix.lower() == ".xaml" else []
        if not xamls:
            xamls = list(project_path.rglob("*.xaml"))
        for xaml in xamls:
            ok, msgs = _validate_xaml_structure(xaml)
            if not ok:
                for m in msgs:
                    errors.append(self._as_error(str(xaml), m))
        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def _run_activity_checks(self, project_root: Path) -> ValidationResult:
        if os.environ.get("UIPATH_SKIP_ACTIVITY_VALIDATION", "0").lower() in (
            "1",
            "true",
            "yes",
        ):
            return ValidationResult(valid=True)
        from uipath_claude.validation.activity_validator import validate_activities_in_xaml

        errors: list[ValidationError] = []
        for xaml in project_root.rglob("*.xaml"):
            ok, msgs = validate_activities_in_xaml(xaml)
            if not ok:
                for m in msgs:
                    errors.append(self._as_error(str(xaml), m))
        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def _run_studio_validation(
        self, project_root: Path, file_path: Path | None
    ) -> ValidationResult:
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []
        studio_ran = False
        xamls = [file_path] if file_path and file_path.suffix.lower() == ".xaml" else []
        if not xamls:
            xamls = list(project_root.rglob("*.xaml"))
        for xaml in xamls:
            rel = str(xaml.relative_to(project_root)).replace("\\", "/")
            # Two-pass, error-only validation to defeat Studio IPC stale-cache results.
            # See uipath_claude/tools/uipath/cli_runner.run_uip_rpa_get_errors and
            # docs/build-logs/README.md (validation contract).
            cli_result = run_uip_rpa_get_errors(
                project_root,
                file_path=rel,
                use_studio=True,
                min_severity="error",
                passes=2,
            )
            if cli_result.get("studio_required"):
                warnings.append(
                    self._as_error(
                        rel,
                        "Studio diagnostics unavailable. Start/open the project in UiPath Studio "
                        "to run `uip rpa get-errors`.",
                        severity="warning",
                    )
                )
                continue
            studio_ran = True
            for w in cli_result.get("warnings", []):
                warnings.append(self._as_error(rel, w, severity="warning"))
            if not cli_result.get("success", False):
                for e in cli_result.get("errors", []):
                    errors.append(self._as_error(rel, e))
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            studio_ran=studio_ran,
        )

    def validate(self, project_path: Path, file_path: Path | None = None) -> ValidationResult:
        structural = self._run_structural_checks(project_path, file_path)
        if not structural.valid:
            return structural

        project_root = _locate_project_root(project_path)
        if project_root is None:
            return ValidationResult(
                valid=True,
                errors=[],
                warnings=[
                    self._as_error(
                        str(project_path),
                        "No project.json found. Structural validation passed; "
                        "activity and Studio diagnostics not run.",
                        severity="warning",
                    ),
                ],
                studio_ran=False,
            )

        activity = self._run_activity_checks(project_root)
        if not activity.valid:
            return ValidationResult(
                valid=False,
                errors=[*structural.errors, *activity.errors],
                warnings=structural.warnings,
                studio_ran=False,
            )

        studio = self._run_studio_validation(project_root, file_path)
        return ValidationResult(
            valid=structural.valid and activity.valid and studio.valid,
            errors=[*structural.errors, *activity.errors, *studio.errors],
            warnings=[*structural.warnings, *activity.warnings, *studio.warnings],
            studio_ran=studio.studio_ran,
        )


def validation_result_to_chat_dict(
    project_path: Path, result: ValidationResult
) -> dict:
    """Shape compatible with ``validate_generated_project`` legacy consumers."""

    def _dump(err: ValidationError) -> str:
        if err.file:
            return f"[{err.file}] {err.message}"
        return err.message

    return {
        "valid": result.valid,
        "success": result.valid,
        "fully_validated": result.studio_ran,
        "errors": [_dump(e) for e in result.errors],
        "warnings": [_dump(w) for w in result.warnings],
        "project_path": str(project_path),
    }
