# UiPath Project Rule - Installation Guide

This folder contains a portable, submodule-backed rule set for UiPath projects. Drop the contents into the root of any UiPath repo.

## Layout

```
<your-uipath-repo>/
├── CLAUDE.md                      <- the rule itself (principles, hard gates, decision logic)
├── .cursorrules                   <- Cursor legacy pointer -> CLAUDE.md
├── .cursor/rules/uipath.mdc       <- Cursor modern rule (alwaysApply) -> CLAUDE.md
├── docs/
│   ├── uipath-cli.md              <- full CLI reference (load on demand)
│   ├── uipath-cli.verbs.json      <- CLI verb allow-list consumed by the submodule guard
│   └── uipath-workflows.md        <- end-to-end workflow patterns (load on demand)
├── skills/                        <- git submodule -> https://github.com/UiPath/skills
├── .uipath/skills-approved.sha    <- pinned allow-list of approved submodule commits
└── .githooks/                     <- pre-commit / pre-push hooks enforcing the guard
```

## Why this layout

**Layer 1 - `CLAUDE.md` (the rule):** short, stable, opinionated. Loaded into every AI assistant context. Contains decision logic and hard gates.

**Layer 2 - `.cursorrules` / `.cursor/rules/uipath.mdc`:** Cursor-specific pointers. Both exist so that old and new Cursor installations pick it up. Both point to `CLAUDE.md`.

**Layer 3 - `docs/uipath-*.md`:** heavy reference material (exhaustive CLI syntax, end-to-end flows for each paradigm, troubleshooting). Not loaded by default. The rule in Layer 1 tells the AI to read these on demand when it actually needs the details. This keeps context windows lean and keeps the AI from hallucinating CLI flags.

**Layer 4 - `skills/` submodule:** the live source of truth for per-paradigm skill logic, the project discovery agent, and session hooks. Tracks [github.com/UiPath/skills](https://github.com/UiPath/skills). The submodule guard (`python -m uipath_claude.skills.submodule_guard`) ensures the checked-out commit is on the approved list and that `CLAUDE.md` / `docs/*` don't reference skills that aren't present.

## How to install in a new repo

1. Copy `CLAUDE.md`, `.cursorrules`, the `.cursor/` folder, and the `docs/` folder into the root of your UiPath repo.
2. Add the UiPath/skills submodule:
   ```bash
   git submodule add https://github.com/UiPath/skills skills
   git submodule update --init --recursive
   ```
3. Seed the approved-commit file:
   ```bash
   mkdir -p .uipath
   git -C skills rev-parse HEAD > .uipath/skills-approved.sha
   ```
4. (Optional) install the git hooks:
   ```bash
   git config core.hooksPath .githooks
   ```
5. Commit.
6. Open the repo in Cursor / Claude Code. The rule activates automatically.
7. When the assistant needs exact CLI syntax, it reads `docs/uipath-cli.md`. When it needs an end-to-end flow, it reads `docs/uipath-workflows.md`. When you want to audit or tweak behavior, edit `CLAUDE.md`.

## Scope

Covers:
- Classic RPA (Studio, XAML, REFramework)
- Coded Automations (C# workflows)
- Coded Agents (Python; LangGraph, LlamaIndex, generic)
- Studio Web (browser IDE, Local + Cloud workspaces)
- Maestro (BPMN/DMN orchestration)
- Coded Apps (code-first, via `uip codedapp`)
- API Workflows
- Case Management (preview) and Data Fabric (preview) via the `uip` CLI
- Solutions (multi-project bundles)
- Full CLI lifecycle across the three CLIs: `uipcli` (.NET) + `uipath` (Python) + `uip` (Node.js) for dev/test/debug/analyze/pack/deploy/publish
- CI/CD (GitHub Actions, Azure DevOps, Jenkins)

## Tuning

- **Project-specific conventions** (package-name prefixes, HITL platform, template repos, folder layouts) live in `.claude/rules/project-context.md`, produced by the `uipath-project-discovery-agent`. Do **not** edit `CLAUDE.md §9` for project specifics.
- **§10 When to ask the human** - tighten or loosen the guardrails.
- **§12 Boundaries for the AI assistant** - expand/contract what the AI can do autonomously.

Rebuild `docs/uipath-cli.md` and `docs/uipath-cli.verbs.json` together when UiPath ships a new CLI version (currently 25.10.x; 26.x expected late 2026). Re-verify against live `--help` output before editing.

## Verification trail

The command/flag content in this bundle was verified live in April 2026 against `uipcli 25.10.13` and `uipath 2.8.40` on Windows. See [CLAUDE.md §14](../CLAUDE.md) for the concrete evidence.

## Credits

Research sources: UiPath official docs (`docs.uipath.com`), UiPath GitHub org (`UiPath/uipath-python`, `UiPath/uipath-langchain-python`, `UiPath/uipath-integrations-python`, `UiPath/skills`), UiPath Community Forum (incl. the CLI comparison gist by cprima and the CLI-for-enterprise-CI/CD article by Alexandru Iordan), and the UiPath Community Blog.
