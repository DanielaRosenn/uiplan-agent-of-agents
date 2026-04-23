# Templates (generated)

**Do not edit these files directly.**

They are generated from the outer repository's canonical templates by
`ops/scripts/sync-shared-templates.mjs` (runs on `postinstall`, `predev`,
`prebuild`, and via `pnpm sync:templates`).

| This file | Edit instead |
|---|---|
| `pdd.md` | `templates/pdd-template.md` (outer repo) |
| `sdd.md` | `templates/sdd-template.md` (outer repo) |
| `tdd.md` | `templates/tdd-template.md` (outer repo) |
| `add.md` | `templates/agent-spec-template.md` (outer repo) |

## When to use which template

Use this section as the canonical guide for choosing PDD vs SDD vs ADD vs TDD (same workflow as the Claude Code CLI `read_doc_template` / project `docs/` tools).

**PDD (Process Design Document)** — First artifact. Capture business requirements, as-is vs to-be process, scope, and success criteria. Produced in the BA stage. Required before you produce an SDD or an ADD.

**SDD (Solution Design Document)** — Produced from an approved PDD in the SA stage. Describes target architecture, components, integrations, and data flows for a classic UiPath RPA solution (Studio, Robots, Orchestrator).

**ADD (Agent Design Document)** — Produced from an approved PDD when the solution is an **agentic** UiPath application (LLM-driven logic, Agents service, etc.). Use **instead of** an SDD, not in addition to it.

**TDD (Technical Design Document)** — Produced after an SDD or ADD in the Developer stage. Low-level, developer-facing design: modules, error handling, tests.

Decision rule:

> Classic RPA: PDD → SDD → TDD. Agentic: PDD → ADD → TDD.

Full guidance also lives here in this README; MCP tools `uipath_doc_read_template` / `uipath_doc_*` point operators at this file.

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
