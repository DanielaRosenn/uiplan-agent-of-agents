# Templates (generated)

**Do not edit these files directly.**

They are generated from the outer repository's canonical templates by
`scripts/sync-shared-templates.mjs` (runs on `postinstall`, `predev`,
`prebuild`, and via `pnpm sync:templates`).

| This file | Edit instead |
|---|---|
| `pdd.md` | `templates/pdd-template.md` (outer repo) |
| `sdd.md` | `templates/sdd-template.md` (outer repo) |
| `tdd.md` | `templates/tdd-template.md` (outer repo) |
| `add.md` | `templates/agent-spec-template.md` (outer repo) |

## Workflow

1. Edit the source file in the outer repo's `templates/` directory.
2. Run `pnpm sync:templates` from the outer repo root.
3. Commit the regenerated file inside this submodule:
   ```
   cd agent
   git add uipath_claude/templates
   git commit -m "chore(templates): sync from outer"
   ```
4. Bump the submodule pointer in the outer repo:
   ```
   cd ..
   git add agent
   git commit -m "chore: bump agent submodule"
   ```
