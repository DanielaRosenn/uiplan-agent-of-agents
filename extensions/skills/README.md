# Team Extensions Skills

Skills in this folder are **team/project extensions** (not from UiPath/skills submodule).

## What Goes Here

- Hermes-inspired operational controls (tool policies, approval workflows)
- Project-specific playbooks (Cato templates, internal conventions)
- Overrides for UiPath skills (use same name to replace)
- Shared Cursor/CLI overlays such as UiPlan, Mermaid guidance, and compatibility redirects

## What Does NOT Go Here

- Direct edits to UiPath skills (those live in skills/ submodule)
- Personal/experimental skills (use ~/.cursor/skills or .uipath-claude/skills)

## Naming Conventions

- Use unique names that don't collide with UiPath skills unless intentionally overriding
- Prefix with team/project if needed: `cato-workflow-builder`, `hermes-tool-policy`

## Priority Order

When skill names collide, first source wins (see `uipath_claude.skills.sources` and [docs/SKILL_LAYOUT.md](../../docs/SKILL_LAYOUT.md)):

1. Paths listed in `.uipath-claude/config.yaml` under `skills.sources` (if present)
2. User (`~/.cursor/skills`) - personal overrides
3. Project (`.uipath-claude/skills`) - per-checkout overrides
4. **Extensions (this folder)** - team-shared extensions
5. UiPath Submodule (`skills/skills`) - official baseline
6. Templates (opt-in) - template-bundled skills

Cursor setup (`ops/scripts/setup-cursor.*`) generates `.cursor/skills` from the
official UiPath submodule plus this folder, so team overlays are available in
both Cursor and the Python CLI skill loader.

## Creating a New Skill

Each skill lives in its own subdirectory with a `SKILL.md` file:

```
extensions/skills/
  my-skill-name/
    SKILL.md          # Required - main skill document
    references/       # Optional - supporting docs
    ops/scripts/          # Optional - helper scripts
```

### SKILL.md Format

```yaml
---
name: my-skill-name
description: Use when [specific triggering conditions]
---

# My Skill Name

## When to Use
...

## Procedure
...
```

See [agentskills.io/specification](https://agentskills.io/specification) for the full spec.
