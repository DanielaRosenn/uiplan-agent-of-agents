# Contributing

This project is extensible along three axes: **skills**, **tools**, and **slash commands**. The official UiPath skills live in a git submodule (`skills/skills/`) and should not be edited in-place — always override from a higher-priority layer. See [docs/SKILL_LAYOUT.md](docs/SKILL_LAYOUT.md) for the full layering model.

## Add a skill

Skills are markdown playbooks (`SKILL.md`) with YAML frontmatter. The loader merges multiple roots; first source wins when two folders define the same skill `name`.

**Where to put a new skill**

| Intent | Location | In git? |
|---|---|---|
| Personal experiment | `~/.cursor/skills/<skill-name>/SKILL.md` | No |
| Per-checkout override | `.uipath-claude/skills/<skill-name>/SKILL.md` | No (gitignored) |
| Team-shared | `extensions/skills/<skill-name>/SKILL.md` | Yes |
| Official UiPath skill | `skills/skills/<skill-name>/SKILL.md` | Submodule — do not edit here |

**Minimum SKILL.md**

```markdown
---
name: my-skill
description: One sentence on what this skill teaches the agent.
triggers:
  - "when user mentions X"
  - "when building Y"
---

# My Skill

Procedure, constraints, examples. Keep it short; the whole file is injected into the model context when the skill matches.
```

Validate your skill registered: `uipath-claude chat` → `/skills`. The origin column shows the layer you added it to.

## Add a tool

Tools live under [uipath_claude/tools/](uipath_claude/tools/). Each tool is a Python function registered in a tool group. Follow the pattern in [uipath_claude/tools/skill_execution_tools.py](uipath_claude/tools/skill_execution_tools.py):

1. Add the function with a typed signature and a docstring (the docstring becomes the model-visible description).
2. Register it in the relevant tool group / profile in `uipath_claude/tools/profiles.py`.
3. If the tool performs a potentially destructive operation, gate it through `uipath_claude/tools/uipath/approval.py`.
4. Add a unit test under `tests/unit/tools/`.

Profiles (`safe`, `uipath-dev`, `all`) control which tools the agent sees. Default to `uipath-dev` or `all` only if the tool is clearly side-effect-free or gated.

## Add a slash command

Slash commands live under `uipath_claude/commands/`. Each command is a small module exposing a `run(session, args)` function and registered on the command registry:

1. Create `uipath_claude/commands/my_command.py` with a `run` function.
2. Register it in `uipath_claude/commands/registry.py` (or wherever the project currently centralizes registrations).
3. Document the command in `README.md` and [docs/USER_GUIDE.md](docs/USER_GUIDE.md).
4. Add a unit test under `tests/unit/commands/`.

Slash commands call into the same Python packages as the CLI, so keep business logic in `query/` or `tools/` and keep the command thin.

## Dev loop

```bash
# Install dev deps (once)
pip install -e ".[dev]"

# Lint + type + tests
ruff check .
black --check .
mypy uipath_claude
pytest

# Evaluations (longer running)
python run_evals.py
```

- `pytest -m "not integration"` to skip integration tests locally.
- `pytest tests/unit/<path>` to iterate on a single area.
- Run evaluations before merging anything that touches the executor, planner, or skill registry.

## Commit hygiene

- Keep diffs minimal; do not refactor unrelated code in the same PR.
- Update [CHANGELOG.md](CHANGELOG.md) under `## [Unreleased]` for any user-visible change.
- If you touch a skill or tool, verify `/skills` and `/status` still render cleanly.

## Review

Open a PR against `main`. A maintainer will run the evaluation framework and a manual smoke test (`uipath-claude start-project "InvoiceBot"` end-to-end) before merge.
