# UiPath Full-Stack Project Rule

> **Who this is for:** AI coding assistants (Claude Code, Cursor, Windsurf, Copilot) working in UiPath repositories.
> **What this is:** Principles, decision logic, and hard gates. Command reference lives in `docs/uipath-cli.md`. End-to-end workflows live in `docs/uipath-workflows.md`. **Read the relevant doc before running any CLI command you're not 100% sure about.**

---

## 0. Identity & non-negotiables

You are working in a UiPath repository. Before doing anything:

1. **Identify the project type** by inspecting the repo (see §1). The project type dictates which CLI, which SDK, and which workflow applies.
2. **Never assume** - read `project.json`, `langgraph.json`, `agent_framework.json`, `pyproject.toml`, or `*.uiproj` first.
3. **The UiPath/skills submodule is the source of truth** for skill authoring guidance, agent personas, and session hooks. See §0a.

### Hard gates (never bypass)

- **Modern experience only.** C# expressions, Windows target, `.NET 8`. Never Classic, never VB.Net, never Windows-Legacy unless a legacy project explicitly requires it.
- **Never publish if `analyze` returns errors.** Warnings may be accepted with an explicit human sign-off; errors are blockers.
- **Never commit secrets.** Credentials go in Orchestrator Assets or environment variables referenced via `.env` (never checked in).
- **Never delete another developer's `.xaml`, `.py`, or project files** without an explicit instruction referencing the file by name.
- **Match CLI version to Studio/Orchestrator version.** Using a 24.x CLI on a 25.10 project will corrupt the package. See `docs/uipath-cli.md` §Compatibility.
- **Solutions are Automation Cloud only** via CLI (on-prem/Automation Suite do not support `uipcli solution` commands).
- **The `skills/` submodule is pinned.** Do not advance it to a new commit without updating `.uipath/skills-approved.sha` and running the submodule guard (`python -m uipath_claude.skills.submodule_guard`).

---

## 0a. Official UiPath AI-assistant tooling (defer to these first)

This project integrates the official UiPath skill and agent catalog as a **git submodule** at `skills/` pointing at [github.com/UiPath/skills](https://github.com/UiPath/skills). That repo - not this rule file - is the authoritative source for:

| Concern | Defer to |
|---|---|
| Per-paradigm skill logic (RPA, agents, Maestro, Case, Test, etc.) | `skills/skills/<skill>/SKILL.md` |
| Project discovery for fresh chats | `skills/agents/uipath-project-discovery-agent.md` |
| Session start-up (npm tool install, version checks) | `skills/hooks/hooks.json` + `skills/hooks/ensure-uip.sh` |
| Contribution rules for skills themselves | `skills/CLAUDE.md` |
| Files that `uipath init` generates in an agent project (`AGENTS.md`, `.agent/*`, `CLAUDE.md` inside the agent) | Generated on demand by the Python `uipath` CLI |

**Rules:**

- Never hand-roll a skill that already exists in `skills/skills/`. Extend or override via `extensions/skills/` (see [extensions/skills/README.md](extensions/skills/README.md)) instead.
- Never duplicate content from a `SKILL.md` into this `CLAUDE.md` - reference the skill id instead.
- Before running any `uip` command, the session-start hook must have succeeded. If it didn't, stop and ask the user to re-open the session.
- When `uipath init` emits its own `CLAUDE.md` / `AGENTS.md` inside a generated agent folder, **do not overwrite** this repo-level `CLAUDE.md`. Pass `--no-agents-md-override` or keep the generated files under the agent subfolder.

---

## 1. Project type detection

Before the first tool call, determine what kind of project you're in. This is **the** decision that drives everything else.

| Signal in repo | Project type | Primary CLI | Read next |
|---|---|---|---|
| `project.json` with `.xaml` files | Classic RPA / Coded Workflow | `uipcli` (UiPath.CLI.Windows 25.10+) | `docs/uipath-workflows.md` §RPA |
| `project.json` + `.cs` files, no `.xaml` | Coded Automation (C#) | `uipcli` | `docs/uipath-workflows.md` §CodedAutomation |
| `langgraph.json` + `pyproject.toml` + optional `project.uiproj` | LangGraph Coded Agent | `uipath` (Python) | `docs/uipath-workflows.md` §LangGraphAgent |
| `agent_framework.json` + `pyproject.toml` | Generic Coded Agent | `uipath` (Python) | `docs/uipath-workflows.md` §CodedAgent |
| `llama_index.json` + `pyproject.toml` | LlamaIndex Coded Agent | `uipath` (Python) | `docs/uipath-workflows.md` §LangGraphAgent |
| `solution.uipx` at root with sub-projects | Solution (multi-project) | `uipcli solution ...` | `docs/uipath-workflows.md` §Solution |
| `*.bpmn` files under a Studio Web project | Maestro process | Studio Web UI + Solutions CLI | `docs/uipath-workflows.md` §Maestro |
| `app.config.json` + `action-schema.json` | Coded App / Coded Action App | `uip codedapp` + Solution CLI | `docs/uipath-workflows.md` §CodedApp |
| `api-workflow.json` or `ApiWorkflow` project type | API Workflow | `uipcli` or Solution CLI | `docs/uipath-workflows.md` §ApiWorkflow |
| `caseplan.json` | Case Management (preview) | `uip case` | `skills/skills/uipath-maestro-case/SKILL.md` |

If **multiple** markers exist, you're in a Solution - treat the repo as such and work at the solution level unless explicitly told to operate on a single sub-project.

---

## 2. The three CLIs - when to use which

UiPath ships **three** distinct CLIs. They are not interchangeable.

```
Are you building/packaging/deploying a C# or XAML project, or a Solution?
  -> uipcli  (.NET, distributed via NuGet)

Are you building a Python coded agent (LangGraph, LlamaIndex, generic)?
  -> uipath  (Python, distributed via PyPI)

Do you need Studio Web sync, live UI interaction, rpa-tool, Case Management,
Data Fabric, Coded App scaffolding, or the discovery/skills tooling?
  -> uip     (Node.js, distributed via npm as @uipath/cli)
```

### `uipcli` (.NET, NuGet-distributed)

- **What:** The official CI/CD CLI. `UiPath.CLI.Windows`, `UiPath.CLI.Linux`, `UiPath.CLI.macOS`, `UiPath.CLI.Windows.Legacy`.
- **Use for:** Classic RPA, Coded Automations (C#), Libraries, Tests, Solutions, API Workflows, Apps (via Solutions).
- **Install:** `dotnet tool install --global UiPath.CLI.Windows --version 25.10.*` (requires .NET 8 Desktop Runtime).
- **Auth:** External App (Confidential) with OAuth2 client credentials. Service-specific default scopes apply in 25.10+.
- **Core verbs:** `package {restore|analyze|pack|deploy}`, `test run`, `job run`, `asset {deploy|delete}`, `solution {restore|analyze|pack|upload-package|delete-package|download-package|download-config|deploy|deploy-activate|deploy-uninstall}`, `run` (JSON-driven).
- **Note:** `uipcli package delete` does **not** exist in 25.10. Remove packages through Orchestrator UI or the Solutions commands.

### `uipath` (Python, PyPI-distributed)

- **What:** The agent developer CLI. Ships with `uipath` package; extended by `uipath-langchain`, `uipath-llamaindex`.
- **Use for:** Coded Agents (LangGraph, LlamaIndex, generic Python agents).
- **Install:** `uv add uipath` or `uv add uipath-langchain` (project-local, via `uv`, preferred over `pip`).
- **Auth:** `uipath auth` (browser OAuth) or `.env` with `UIPATH_BASE_URL` / `UIPATH_CLIENT_ID` / `UIPATH_CLIENT_SECRET`.
- **Core verbs:** `auth`, `new`, `init`, `run`, `pack`, `publish`, `invoke`, `deploy`, `eval`, `pull`, `push`.
- **Under the hood:** `uipath pack` currently downloads `uipcli` to do the actual packing. Tolerate the one-time download.

### `uip` (Node.js, npm-distributed)

- **What:** The **unified** UiPath CLI. Shipped as `@uipath/cli`.
- **Use for:** everything covered by the UiPath/skills submodule - skill install, project discovery helpers, `uip rpa`, `uip rpa-legacy`, `uip case`, `uip df`, `uip codedapp`, `uip rpa uia`, `uip feedback`, `uip tools install ...`.
- **Install:** `npm install -g @uipath/cli` (the `skills/hooks/ensure-uip.sh` session hook does this automatically).
- **Skills in this repo:** session start runs `skills/hooks/ensure-uip.sh` which installs `@uipath/cli` and `@uipath/rpa-tool`.

**Rule of thumb:**
- Python agent packaging/publishing -> `uipath`.
- RPA / Solutions CI -> `uipcli`.
- Skill-level ops (discovery, Case, Data Fabric, Coded Apps, live UI interaction, feedback) -> `uip`.

Solutions containing a Python agent pack at the solution level with `uipcli solution pack`; the agent sub-project still uses `uipath` for local dev loops.

---

## 3. The build loop (what an AI assistant must do)

Whenever you're about to publish, deploy, or hand off code, run this loop. **Do not skip steps.**

```
  +--------------------------------------------------------------+
  |                                                              |
  |   1. RESTORE    ->  2. ANALYZE  ->  3. TEST  ->  4. PACK     |
  |                         v              v                     |
  |                      (gate)        (gate)                    |
  |                         v              v                     |
  |                    5. DEPLOY   ->  6. SMOKE TEST (optional)  |
  |                                                              |
  +--------------------------------------------------------------+
```

### Decision logic at each step

**1. Restore** - always before analyze/pack if dependencies may be stale or the repo is fresh (clean clone, post-`git pull` on changed `project.json`).

**2. Analyze** - **blocking gate.** Parse the result. If `errors > 0`, stop and surface the errors to the user. Do not proceed to pack. Warnings: list them and ask whether to proceed.

**3. Test** - run project tests (`uipcli test run` for RPA, `uipath run` or `uipath eval` for agents) before pack. If tests fail, stop and surface failures.

**4. Pack** - produce the `.nupkg` locally first. Never pack straight to a remote feed from an assistant-driven flow without the user having seen the analyze+test results.

**5. Deploy** - only after explicit user confirmation for the target feed/folder. Default to the user's **personal workspace** feed unless they specify otherwise. Never deploy straight to Production.

**6. Smoke test** - optionally invoke the deployed process with a known-safe input to confirm it starts. Do not run real data through a fresh deploy.

### What to parse from tool output

- `analyze` output: read the JSON `--resultPath` file. Filter on `severity == "Error"`. Count, list, surface.
- `test run` output: JUnit/NUnit XML or JSON; surface failed test names and messages.
- `pack` output: confirm the resulting `.nupkg` path and version string; never proceed if the filename doesn't match expected naming.
- `deploy` output: capture the release/version ID; confirm against the Orchestrator link returned.

---

## 4. When to invoke Studio vs CLI vs Studio Web

| Situation | Right tool |
|---|---|
| Designing a new XAML workflow from scratch | Studio Desktop (human), then commit |
| Modifying an existing XAML - small change | Studio Desktop; AI can edit XAML directly only for known-safe patterns (see `docs/uipath-workflows.md` §XAML-AI-edits) |
| Any Python agent work | Cursor / Claude Code + `uipath` CLI |
| BPMN process modeling (Maestro) | Studio Web (browser) - no CLI equivalent |
| Building Coded Apps | Studio Web OR `uip codedapp` scaffold - package via Solutions CLI |
| CI/CD (pack, analyze, deploy) | `uipcli` in pipeline |
| Local agent dev loop | `uipath run` with hot-reload |
| End-to-end Solution deploy | `uipcli solution` commands |
| Live UI verification | `uip rpa uia` via the `uipath-interact` skill |
| Studio Desktop held a project open for validation or debug | Close it in-flow: `uip rpa close-project --project-dir "<projectRoot>"` (then process cleanup if needed — `docs/Testing_Guide.md`) |

**The AI assistant's role:** own the CLI-driven paths end-to-end. For Studio/Studio Web visual design, produce the design artifacts (BPMN diagrams as documentation, XAML scaffolds, workflow specs) and let the human drive the UI.

---

## 5. AI-assistant-driven workflow (the full pattern)

When the user asks you to "build a UiPath automation for X", follow this sequence:

1. **Run project discovery.** If `.claude/rules/project-context.md` doesn't exist, invoke the `uipath-project-discovery-agent` from `skills/agents/` to produce it. This populates project identity, dependencies, entry points, conventions.
2. **Clarify the paradigm.** Ask: RPA workflow, coded automation, coded agent, Maestro orchestration, Coded App, or Solution? Do not guess.
3. **Scaffold via CLI, not by hand.**
   - Python agent: `uipath new <name>` then `uipath init`.
   - RPA project: use Studio templates (human opens Studio). AI never hand-writes `project.json` from scratch.
   - Solution: `uipcli solution pack` on an existing solution tree, or start from a Marketplace / Studio Web template.
4. **Generate code.** Write the agent logic, activities, workflows, following the conventions discovered in step 1.
5. **Run the build loop** (§3) locally. Never skip analyze.
6. **Show the user the results** of analyze and tests before offering to publish.
7. **Publish to personal workspace** for the user to review. Never to tenant feed or Production from the assistant.
8. **Document** what was built in a `README.md` update and, if it's a real project, a PDD/SDD reference.

### Commands the assistant should run automatically

- `uipath init`, `uipath run` (local test), `uipcli package analyze`, `uipcli package pack`, `uipcli test run`, `uv sync`, `dotnet restore`.

### Commands that require explicit user confirmation first

- `uipcli package deploy`, `uipath publish`, `uipath invoke`, `uipcli solution deploy`, `uipcli solution deploy-activate`, `uipcli solution deploy-uninstall`, `uipcli solution delete-package`, any command targeting a non-personal feed.

### Commands the assistant should NEVER run without a human in the loop

- Anything targeting a Production folder.
- `uipcli solution deploy-uninstall` against a shared tenant.
- `job run` against live/business-critical processes.
- Deleting packages from shared feeds.

---

## 6. Testing strategy

- **Unit-ish tests for agents**: write `pytest` tests for pure Python logic (parsers, validators, formatters). Keep them fast and offline.
- **Integration tests for agents**: use `uipath run` with JSON input fixtures; snapshot the output.
- **RPA test cases**: use UiPath Testing Activities + Test Manager (25.10+; **Orchestrator Testing Module is deprecated, cloud cutoff Jan 1, 2026**). Target: 1 happy-path + 1 error-path per top-level workflow.
- **CI**: `uipcli test run` in the pipeline; gate promotion on JUnit output.
- **Eval for agents**: `uipath eval` with dataset + evaluators; gate promotion on eval score thresholds.

Minimum bar: every new production-bound project must have at least one end-to-end test and a documented manual smoke test script.

---

## 7. Authentication & secrets

- **Local dev**: `.env` (gitignored). Never commit `.env`. Use `.env.example` to document required keys. For the Python CLI, the required variables are `UIPATH_BASE_URL`, `UIPATH_CLIENT_ID`, `UIPATH_CLIENT_SECRET`.
- **CI/CD**: Orchestrator External App (Confidential) with minimum scopes. In 25.10+, omitting `--applicationScope` applies sensible defaults - use them unless you need broader access.
- **Agents at runtime**: pull secrets from `sdk.assets.retrieve(name=...)`, never hardcode. LLM keys via UiPath LLM Gateway by default; only override for a specific model requirement.
- **Never put a PAT in a repo, issue comment, ticket, or Slack.** If you see one in context, flag it to the user immediately.

---

## 8. Repo layout expectations

A well-formed UiPath repo looks like one of:

**RPA project:**
```
<repo-root>/
├── Main.xaml
├── project.json
├── .gitignore                # Studio-generated + .env
├── .cursorrules              # pointer to CLAUDE.md
├── CLAUDE.md                 # this file
├── docs/
│   ├── uipath-cli.md
│   ├── uipath-workflows.md
│   ├── PDD.md
│   └── SDD.md
├── Data/                     # input/output folders (gitignored if transient)
├── Tests/                    # test XAMLs
└── Framework/                # REFramework pieces if applicable
```

**Coded agent:**
```
<repo-root>/
├── main.py (or agent.py)
├── langgraph.json            # or agent_framework.json / llama_index.json
├── pyproject.toml
├── uv.lock
├── .env.example
├── .uipath/                  # generated by `uipath init`
├── uipath.json               # generated by `uipath init`
├── bindings.json             # generated by `uipath init`
├── CLAUDE.md
├── docs/
│   ├── uipath-cli.md
│   ├── uipath-workflows.md
│   └── ARCHITECTURE.md
└── tests/
```

**Solution:**
```
<repo-root>/
├── solution.uipx             # solution descriptor (25.10)
├── projects/
│   ├── Process.Alpha/
│   ├── Agent.Beta/
│   └── Library.Shared/
├── bindings/
│   ├── dev.json
│   ├── test.json
│   └── prod.json
└── ...
```

---

## 9. Project conventions (neutral defaults)

These are the defaults this rule enforces. Project-specific conventions belong in a project-local `CLAUDE.md` addendum or in `.claude/rules/project-context.md` produced by the discovery agent.

- **Modern experience only.** C#, Windows, .NET 8. No Classic, no VB.Net, no Windows-Legacy.
- **Package naming:** `<Org>.<Domain>.<ProcessName>` (PascalCase segments). Pick a stable `<Org>` prefix per repo and document it in the project-local context.
- **Version scheme:** Semver. Dev bumps patch automatically (`--autoVersion`); releases get explicit `-v` bumps. Solutions require explicit `-v` (no auto-bump).
- **Orchestrator folders:** one folder per business domain. Personal workspace for dev.
- **Logging:** structured logs. Include `bot=<package>` (or `agent=<package>`) as a field; route errors to the team's approval / escalation channel.
- **HITL:** default to UiPath Action Center (native, Maestro-compatible). Swap to a custom HITL platform only if the project explicitly requires it and justify it in the SDD.
- **Documentation:** every production project ships with a PDD (Process Design Doc) and SDD (Solution Design Doc) checked into `docs/`. Coded-agent projects additionally ship an ADD (Agent Design Doc) - see [docs/PDD_LIFECYCLE.md](docs/PDD_LIFECYCLE.md).
- **Test Manager:** migrate existing Orchestrator Testing Module test sets to Test Manager before Jan 1, 2026 (cloud cutoff).
- **Agents:** prefer LangGraph over LlamaIndex for stateful workflows; LlamaIndex for document-heavy / retrieval. Default to the UiPath LLM Gateway; only BYO-LLM with explicit justification.
- **Analyzer rules:** use the repo-local `uipath.policy.default.json` via `uipcli package analyze --governanceFilePath`. For per-rule configuration beyond what `uipcli analyze` supports, fall back to `UiPath.Studio.CommandLine.exe analyze --ruleConfig` with a `RuleConfig.json`.

---

## 10. When to ask the human

Don't ask about everything - that's annoying. Do ask before:

- Publishing to any non-personal feed.
- Deploying to any folder that isn't explicitly `Dev` or the user's personal workspace.
- Overwriting a `project.json` you didn't create.
- Introducing a new external dependency (NuGet package, Python library) not already in the project.
- Changing `.cursorrules`, `CLAUDE.md`, or `docs/uipath-*.md`.
- Any destructive action on shared resources: `solution deploy-uninstall`, `solution delete-package` on tenant feed, asset delete, queue purge.
- Advancing the `skills/` submodule to a new commit.

Don't ask before:

- Running `analyze`, `test`, `pack` locally.
- Running `uipath run` with test inputs.
- Editing code in response to a clear request.
- Adding a dependency that's already in `pyproject.toml` / `project.json` but not installed.
- Creating new files inside the project structure (tests, docs, helpers).

---

## 11. Error handling & recovery patterns

**"Project validation failed during pack":** `pack` and `analyze` don't validate - that's a Studio-only step. Open the project in Studio, fix the red squiggles, commit, retry.

**"NuGet restore is slow":** expected on clean CI agents. Pre-cache NuGet feeds in the pipeline (see `docs/uipath-cli.md` §CI-optimization).

**"CLI version mismatch with Studio":** re-pin both to the same version. 25.10 Studio = 25.10 CLI. Never package a 25.10 project with 24.x CLI.

**"Analyzer rules not being enforced in CI":** `uipcli package analyze` has limited rule customization. Use `UiPath.Studio.CommandLine.exe analyze` with `--ruleConfig` path to a shared `RuleConfig.json` for full rule control.

**"Solution deploy fails with 'Needs setup to activate'":** bindings not resolved. Download the deployment config with `uipcli solution download-config`, fill it in, re-activate. See `docs/uipath-workflows.md` §Solution-activation-troubleshooting.

**"Agent pack succeeds but publish says no package found":** `uipath publish` only sees the most-recently-packed `.nupkg` in the current directory. Pass `-f <file>` or cd into the dir first.

**"Submodule guard failed":** `skills/` drifted from the approved SHA. Run `git -C skills log` to inspect, then either:
- If the new commit is trusted: append it to `.uipath/skills-approved.sha` and commit.
- Otherwise: `git -C skills checkout <approved-sha>` and commit.

---

## 12. Boundaries for the AI assistant

**You are allowed to:**
- Read, write, and modify `.py`, `.cs`, `.xaml`, `.json`, `.yaml`, `.md` files in the project.
- Run the CLI verbs listed in §5 "automatically".
- Propose architecture changes; implement them after confirmation.
- Research UiPath docs and propose solutions grounded in citations (via the library MCP tools `uipath_library_*`, not raw file reads).

**You are not allowed to:**
- Access Orchestrator in a way that bypasses the CLI (no direct REST calls to tenant endpoints without user-provided PAT/credentials).
- Invent activity names or SDK methods - if you're not sure it exists, read `docs/uipath-cli.md` or consult the `uipath_library_*` MCP tools, or say so and ask.
- Commit on the user's behalf to a shared branch (`main`, `master`, `release/*`). Work on a feature branch; the user merges.
- Write C# expressions that call out to arbitrary shell commands or external binaries without explicit approval.
- Modify files inside `skills/` (that submodule is owned by UiPath upstream).

---

## 13. Quick reference pointers

| Need to... | Read |
|---|---|
| Know the exact flags for a CLI command | `docs/uipath-cli.md` |
| Walk through an end-to-end flow | `docs/uipath-workflows.md` |
| Find an activity-level doc | `uipath_doc_get_activity` MCP tool |
| Search the UiPath documentation library | `uipath_library_search` / `uipath_library_lookup` MCP tools |
| Set up a new project from zero | `docs/uipath-workflows.md` §Scaffold |
| Add the project to CI/CD | `docs/uipath-cli.md` §CI-samples |
| Debug a specific failure | `docs/uipath-workflows.md` §Troubleshooting |
| Author a PDD/SDD/ADD | [docs/PDD_LIFECYCLE.md](docs/PDD_LIFECYCLE.md) |
| Pick a skill | skim `skills/skills/<name>/SKILL.md` |

When in doubt: **read the docs before acting**, surface the plan to the user, then execute.

---

## 14. Verification trail

The commands and flags in this rule set were verified against a live UiPath stack on Windows in April 2026. If a command below surprises you, run `<command> --help` first and trust the live output over any doc. File an update if you find a drift.

### Environment

| Tool | Version |
|---|---|
| `uipcli` (UiPath.CLI.Windows) | `25.10.13` |
| `uipath` (Python CLI) | `2.8.40` |
| `uip` (`@uipath/cli`, Node.js) | tracked via the `skills/hooks/ensure-uip.sh` session hook |
| Python | `3.11+` |
| .NET | `.NET 8 Desktop Runtime` |
| `skills/` submodule commit | pinned in `.uipath/skills-approved.sha` (current HEAD: `3bf9b46442b294794a411f04b8f35c5d8eb5b01f`) |

### What was verified live

- `uipcli --help` - confirmed top-level verbs: `package`, `solution`, `test`, `job`, `asset`, `run`, `config`.
- `uipcli solution --help` - confirmed subcommand list: `restore`, `analyze`, `pack`, `upload-package`, `delete-package`, `download-package`, `download-config`, `deploy`, `deploy-activate`, `deploy-uninstall`. (Previous docs used `upload`, `deploy + activate`, `uninstall`, `delete`, `download-configs` - all superseded.)
- `uipcli package --help` - confirmed `restore`, `analyze`, `pack`, `deploy`. **No `delete` verb.** Any earlier doc referencing `uipcli package delete` is wrong.
- `uipcli test run --help` - correct flag is `-a/--projectKey`; project path is a positional.
- `uipath --help` - confirmed verbs: `auth`, `new`, `init`, `run`, `pack`, `publish`, `invoke`, `deploy`, `eval`, `pull`, `push`.
- `uipath new <name>` + `uipath init` - scaffolded a minimal LangGraph agent. Observed:
  - `main.py` uses `from uipath_langchain.chat import UiPathChat` and a default model of `gpt-4o-mini-2024-07-18`.
  - `langgraph.json` is minimal: `{"graphs": {"agent": "./main.py:graph"}}`.
  - `pyproject.toml` `dependencies` pin `uipath-langchain>=0.8.0,<0.9.0`; `requires-python = ">=3.11"`.
  - `uipath.json` and `bindings.json` are emitted even when `init` fails on authorization.
  - `uipath init` emits a `CLAUDE.md` / `AGENTS.md` inside the agent folder by default; pass `--no-agents-md-override` to preserve your own.
- `uipath eval --help` - real flags include `--eval-set`, `--num-workers`, `--no-report`, `--output-file`, `--silent`.

### What was removed/corrected vs the prior draft

- Removed `uipcli package delete` (does not exist).
- Corrected `uipcli solution` verb names (see above).
- Corrected the default Python CLI version hint to use a floating range (`uipath>=2.8,<3`) instead of a specific number.
- Replaced the LangGraph example import with `from uipath_langchain.chat import UiPathChat` and simplified `langgraph.json` to match `uipath new` output.
- Moved all project-specific conventions (package prefix, HITL platform, custom templates, LLM routing rules) out of this rule and into project-local context. This file is the portable baseline.
