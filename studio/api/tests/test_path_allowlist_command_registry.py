from pathlib import Path

import pytest

from app.generation_contracts.command_registry import get_command_registry
from app.generation_contracts.path_allowlist import SCAFFOLD_PREFIXES, validate_target_path


@pytest.mark.parametrize(
    "target_path",
    [
        "/tmp/outside.md",
        "../outside.md",
        ".env",
        "config/tenant.secret.json",
        "skills/skills/uipath-rpa/SKILL.md",
        "node_modules/pkg/index.js",
        "Node_Modules/pkg/index.js",
        ".git/config",
        ".Git/config",
        "dist/app.js",
    ],
)
def test_validate_target_path_rejects_unsafe_targets(tmp_path: Path, target_path: str) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    with pytest.raises(ValueError):
        validate_target_path(
            bundle_root=bundle_root,
            target_path=target_path,
            stage_id="01-plan",
            file_kind="document",
        )


def test_validate_target_path_allows_plan_and_scaffold_targets(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    plan_target = validate_target_path(
        bundle_root=bundle_root,
        target_path="docs/plan.md",
        stage_id="01-plan",
        file_kind="document",
    )
    scaffold_target = validate_target_path(
        bundle_root=bundle_root,
        target_path="projects/Agent.Intake/pyproject.toml",
        stage_id="02-scaffold",
        file_kind="project_scaffold",
    )

    assert plan_target == bundle_root / "docs" / "plan.md"
    assert scaffold_target == bundle_root / "projects" / "Agent.Intake" / "pyproject.toml"


@pytest.mark.parametrize(
    ("stage_id", "file_kind", "target_path"),
    [
        ("01-plan", "document", "projects/Agent.Intake/pyproject.toml"),
        ("01-plan", "document", "scaffold/manifest.json"),
        ("02-scaffold", "project_scaffold", "docs/plan.md"),
        ("02-scaffold", "project_scaffold", "plan/readiness.md"),
    ],
)
def test_validate_target_path_rejects_wrong_stage_prefixes(
    tmp_path: Path,
    stage_id: str,
    file_kind: str,
    target_path: str,
) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    with pytest.raises(ValueError):
        validate_target_path(
            bundle_root=bundle_root,
            target_path=target_path,
            stage_id=stage_id,
            file_kind=file_kind,
        )


def test_validate_target_path_rejects_unknown_stage_id(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    with pytest.raises(ValueError, match="unsupported stage id"):
        validate_target_path(
            bundle_root=bundle_root,
            target_path="docs/plan.md",
            stage_id="03-apply",
            file_kind="document",
        )


def test_command_registry_contains_first_scope_commands_without_external_mutation() -> None:
    registry = get_command_registry()
    commands = {command.command_id: command for command in registry.commands}

    assert {"plan.markdown.readiness", "scaffold.manifest.readiness"}.issubset(commands)
    assert all(command.mutation_classification != "external-mutation" for command in registry.commands)
    assert all(command.required_confirmation is False for command in registry.commands)


def test_scaffold_registry_allowed_path_inputs_align_with_allowlist_prefixes() -> None:
    registry = get_command_registry()
    scaffold_command = next(
        command for command in registry.commands if command.command_id == "scaffold.manifest.readiness"
    )
    expected_globs = {f"{prefix}**" for prefix in SCAFFOLD_PREFIXES}

    assert set(scaffold_command.allowed_path_inputs) == expected_globs
