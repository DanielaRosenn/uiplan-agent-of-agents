from __future__ import annotations

from app.generation_contracts.models import CommandRegistry, CommandRegistryEntry


def get_command_registry() -> CommandRegistry:
    return CommandRegistry(
        commands=[
            CommandRegistryEntry(
                command_id="plan.markdown.readiness",
                purpose="Check generated Plan markdown for required sections and citation markers.",
                owning_stage="01-plan",
                executable="python",
                fixed_args=[
                    "-m",
                    "pytest",
                    "studio/api/tests/test_stage_package_generation.py",
                ],
                working_directory_rule="repo_root",
                allowed_path_inputs=["docs/**/*.md", ".cursor/plans/**/*.md"],
                mutation_classification="read-only",
                required_confirmation=False,
                credential_requirements=[],
                output_summary_policy="Persist pass/fail count and first five assertion messages.",
            ),
            CommandRegistryEntry(
                command_id="scaffold.manifest.readiness",
                purpose="Check scaffold proposal manifests without creating project files.",
                owning_stage="02-scaffold",
                executable="python",
                fixed_args=[
                    "-m",
                    "pytest",
                    "studio/api/tests/test_stage_package_generation.py",
                ],
                working_directory_rule="repo_root",
                allowed_path_inputs=[
                    "projects/**",
                    "apps/**",
                    "services/**",
                    "studio/**",
                    "packages/**",
                    "libs/**",
                ],
                mutation_classification="read-only",
                required_confirmation=False,
                credential_requirements=[],
                output_summary_policy="Persist pass/fail count and first five assertion messages.",
            ),
        ]
    )
