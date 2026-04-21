# UiPath CLI Reference

> Companion to `CLAUDE.md`. **Read this before running CLI commands you aren't 100% sure about.** This file covers exact command syntax, flags, authentication, and CI/CD patterns for the three UiPath CLIs: `uipcli` (.NET), `uipath` (Python), and `uip` (Node.js).

The allow-list of CLI verbs scanned by the submodule guard lives in [uipath-cli.verbs.json](uipath-cli.verbs.json). Keep the two in sync when you update this doc.

---

## Part 1 - `uipcli` (the .NET CLI)

### 1.1 What it is, what it covers

`uipcli` is UiPath's official command-line tool for the full RPA lifecycle. It handles RPA projects (XAML), coded automations (C#), libraries, test projects, API workflows, solutions, and assets. It is **required** for CI/CD and is the tool all Orchestrator plugins (Azure DevOps, Jenkins) ultimately call.

**Current version (verified April 2026):** `25.10.13` - distributed via NuGet and UiPath Official Public Feed.

### 1.2 Installation

**Global .NET tool (preferred for dev machines and CI):**

```bash
# Windows
dotnet tool install --global UiPath.CLI.Windows --version 25.10.*

# Linux (requires .NET 8 Runtime)
dotnet tool install --global UiPath.CLI.Linux --version 25.10.*

# macOS (ARM64 / Apple Silicon only - Intel Macs not supported)
dotnet tool install --global UiPath.CLI.macOS --version 25.10.*

# Legacy Windows projects that aren't part of a Solution
dotnet tool install --global UiPath.CLI.Windows.Legacy --version 25.10.*
```

**Verify:**
```bash
uipcli --version
```

**Prerequisites:**
- `.NET 8 Desktop Runtime` (Windows) / `.NET 8 Runtime` (Linux/macOS)
- UiPath Studio 25.10+ for creating projects this CLI will pack
- UiPath Orchestrator 25.10+ as the deploy target

**Version pinning rule:** CLI version must be >= Studio version used to create the project, and <= Orchestrator version on the target. Mismatches cause pack failures or silent runtime issues.

### 1.3 Global flags

| Flag | Purpose |
|---|---|
| `--version` | Print CLI version |
| `--help`, `-h` | Show help for a command/sub-command |
| `--traceLevel <None|Critical|Error|Warning|Information|Verbose>` | Log verbosity |
| `--disableTelemetry` | Opt out of anonymous usage telemetry |

### 1.4 Authentication

Every command that touches Orchestrator needs auth. Three options (CLI supports all, CI should use option 1):

**Option 1 - External App (OAuth client credentials, CI-friendly):**
```bash
uipcli package deploy <pkg.nupkg> <orch-url> <tenant> \
  --accountForApp <org> \
  --applicationId <client-id> \
  --applicationSecret <secret> \
  --applicationScope "OR.Execution OR.Folders"
```
Starting in 25.10, if you omit `--applicationScope` the CLI applies service-specific defaults (covers most common ops).

**Option 2 - Personal Access Token (user-bound, for scripts):**
```bash
uipcli package deploy <pkg.nupkg> <orch-url> <tenant> \
  -a <account> \
  -t <PAT>
```

**Option 3 - Username/password (on-prem only):**
```bash
uipcli package deploy <pkg.nupkg> <orch-url> <tenant> \
  -u <username> \
  -p <password>
```

**Solutions tasks:** **only Option 1** (External App) is supported. Machine or interactive sign-in not accepted.

### 1.5 Task catalog

`uipcli` groups commands as `<task> <subtask>`. Top-level tasks:

| Task | Subtasks | Use case |
|---|---|---|
| `package` | `restore`, `analyze`, `pack`, `deploy` | Standalone project lifecycle (**no `delete`** - removed in 25.10) |
| `solution` | `restore`, `analyze`, `pack`, `upload-package`, `delete-package`, `download-package`, `download-config`, `deploy`, `deploy-activate`, `deploy-uninstall` | Multi-project bundles (Automation Cloud only) |
| `test` | `run` | Execute test sets / test projects |
| `job` | `run` | Kick off a job in Orchestrator |
| `asset` | `deploy`, `delete` | Manage Orchestrator assets |
| `run` | (JSON-driven) | Execute any task from a JSON config file |
| `config` | `get`, `set` | Read/write CLI config |

### 1.6 Detailed command reference

#### `package restore`

Restore NuGet dependencies for a project.

```bash
uipcli package restore <project_path> \
  [--libraryOrchestratorUrl <url>] \
  [--libraryOrchestratorTenant <tenant>] \
  [-A <org> -I <app-id> -S <secret>] \
  [--disableBuiltInNugetFeeds] \
  [--traceLevel Information]
```

Use before `analyze` or `pack` on a clean checkout or after `project.json` changes.

---

#### `package analyze` - Blocking gate

Run Workflow Analyzer against the project. **The single most important command in any CI flow.**

```bash
uipcli package analyze <project_path> \
  --resultPath <output.json> \
  [--analyzerTraceLevel <None|Critical|Error|Warning|Information|Verbose>] \
  [--stopOnRuleViolation] \
  [--treatWarningsAsErrors] \
  [--ignoredRules "ST-USG-010,ST-NMG-004"] \
  [--governanceFilePath <path-to-uipath.policy.default.json>]
```

**What to do with the output:**
- Parse `<output.json>`, filter `severity == "Error"` -> if count > 0, **fail the pipeline**.
- Surface warnings to the user; don't auto-fail on them unless the user explicitly opted in.
- Validation errors (red squiggles in Studio) are NOT caught by `analyze` - that's a Studio-only check. `pack` also doesn't validate. Only Studio fully validates the XAML.

**Limitation:** `uipcli package analyze` has limited rule customization compared to the legacy `UiPath.Studio.CommandLine.exe analyze` which accepts a full `RuleConfig.json`. For granular rule configuration, fall back to:

```bash
"C:\Program Files\UiPath\Studio\UiPath.Studio.CommandLine.exe" \
  analyze <project.json> \
  --ruleConfig "<path-to-RuleConfig.json>" \
  --output "<path-to-results.json>"
```

---

#### `package pack`

Build the project into a `.nupkg`.

```bash
uipcli package pack <project_path> \
  -o <output_folder> \
  [-v <version> | --autoVersion] \
  [--outputType <Process|Library|Tests|Objects>] \
  [--splitOutput] \
  [--libraryOrchestratorUrl <url> --libraryOrchestratorTenant <tenant>] \
  [-A <org> -I <app-id> -S <secret>] \
  [--libraryOrchestratorApplicationScope "OR.Folders OR.BackgroundTasks ..."] \
  [--libraryOrchestratorFolder <folder>] \
  [--governanceFilePath <uipath.policy.default.json>] \
  [--certificatePath <cert.pfx> --certificatePassword <pwd> --certificateAlgorithm <sha256>] \
  [-l <en-US|...>] \
  [--repositoryUrl <url> --repositoryCommit <sha> --repositoryBranch <branch> --repositoryType <GitHub|AzureDevOps|...>] \
  [--projectUrl <automation-hub-idea-url>] \
  [--releaseNotes "<text>"] \
  [--disableBuiltInNugetFeeds] \
  [--traceLevel Information]
```

**Notes:**
- `--outputType` is auto-detected from `project.json` `designOptions.outputType`; only pass it to override.
- `-v` wins over `--autoVersion`. Use explicit versions for releases, auto for CI dev builds.
- `--libraryOrchestrator*` flags are only needed if the project has library dependencies from Orchestrator feeds.
- `pack` does NOT run the Workflow Analyzer and does NOT validate XAML. Always run `analyze` first.
- Repo metadata flags (`--repositoryUrl`, etc.) inject git info into the `.nuspec` for traceability - use them in CI.
- `--certificatePath` / `--certificatePassword` sign the output package.

---

#### `package deploy`

Upload a `.nupkg` to an Orchestrator feed, optionally creating a release.

```bash
uipcli package deploy <package.nupkg> <orchestrator_url> <tenant> \
  -A <org> -I <app-id> -S <secret> \
  [--applicationScope "OR.Execution OR.Folders"] \
  [--orchestratorFolder <folder>] \
  [--createProcess]
```

`--createProcess` creates the release in the target folder after upload. Without it, you get a package available in the feed but no runnable process.

> **Note:** `uipcli` does **not** expose a `package delete` verb in 25.10. To remove a package, use Orchestrator UI or, if it's part of a Solution, `uipcli solution delete-package`.

---

#### `test run`

Execute tests against Orchestrator (legacy Orchestrator Testing Module OR Test Manager in 25.10+).

```bash
uipcli test run <project_path_or_pkg> <orchestrator_url> <tenant> \
  -a <org> \
  --projectKey <test-project-key> \
  [-A <org> -I <app-id> -S <secret>] \
  [--environment <env>] \
  [--folder_organization_unit <folder>] \
  [--testset <test-set-name>] \
  [--result_path <junit-output.xml>] \
  [--out <junit|uipath>] \
  [--attachRobotLogs] \
  [--timeout <seconds>]
```

**Test Manager transition (critical):**
- Cloud Orchestrator Testing Module -> **discontinued Jan 1, 2026**.
- Automation Suite Testing Module -> **removed April 2026** (6 months after 2.2510 feature parity).
- On-prem MSI -> continues indefinitely.

For new projects, default to Test Manager.

---

#### `job run`

Kick off a job in Orchestrator.

```bash
uipcli job run <process_name> <orchestrator_url> <tenant> \
  -A <org> -I <app-id> -S <secret> \
  [--folder_organization_unit <folder>] \
  [--priority <Low|Normal|High>] \
  [--robots <robot-names>] \
  [--user <user>] \
  [--machine <machine>] \
  [--input_arguments <json>] \
  [--fail_when_job_fails true] \
  [--timeout <seconds>] \
  [--wait true] \
  [--job_result <output.json>]
```

Useful for post-deploy smoke tests. With `--wait true`, blocks until completion and returns non-zero on job failure - perfect for gating CD.

---

#### `asset deploy` / `asset delete`

```bash
uipcli asset deploy <csv-file> <orchestrator_url> <tenant> \
  -A <org> -I <app-id> -S <secret> \
  [--folder_organization_unit <folder>]
```

CSV format: `Name,Type,Value` (types: `Text`, `Bool`, `Integer`, `Credential`). For `Credential`, value is `username::password`.

### 1.7 Solution commands (Automation Cloud only)

Solutions are multi-project deployable bundles. CLI support arrived with 25.10. Verb names below are taken directly from `uipcli solution --help`.

#### `solution restore`

```bash
uipcli solution restore <solution_path>
```

#### `solution analyze`

```bash
uipcli solution analyze <solution_path> \
  --resultPath <output.json>
```

#### `solution pack`

```bash
uipcli solution pack <solution_path> \
  -v <version>    # REQUIRED - no auto-increment \
  -o <output_folder>
```

**Gotcha:** Unlike standalone projects, Solutions do NOT auto-bump version. You must pass `-v`.

#### `solution upload-package`

```bash
uipcli solution upload-package <solution.uipx> <orchestrator_url> \
  -A <org> -I <app-id> -S <secret> \
  --applicationScope "OR.Solutions"
```

#### `solution deploy`

```bash
uipcli solution deploy <solution_name> <version> <orchestrator_url> \
  -A <org> -I <app-id> -S <secret> \
  --targetFolder <folder> \
  [--bindings <path/to/env-bindings.json>]
```

#### `solution deploy-activate`

Combined deploy + activate in one call. Prefer over running `deploy` then activating separately.

```bash
uipcli solution deploy-activate <solution_name> <version> <orchestrator_url> \
  -A <org> -I <app-id> -S <secret> \
  --targetFolder <folder> \
  [--bindings <path/to/env-bindings.json>]
```

#### `solution download-config`

Pulls the bindings/config template for a deployment - fill it in and pass to `deploy --bindings`. Note: **singular** `download-config`, not `download-configs`.

```bash
uipcli solution download-config <solution_name> <version> <orchestrator_url> \
  -A <org> -I <app-id> -S <secret> \
  -o <output.json>
```

#### `solution download-package`

Download an uploaded solution package back to disk (for audit / rehydration).

```bash
uipcli solution download-package <solution_name> <version> <orchestrator_url> \
  -A <org> -I <app-id> -S <secret> \
  -o <output_folder>
```

#### `solution deploy-uninstall`

Uninstall (remove) an activated deployment. **Destructive on shared tenants.**

```bash
uipcli solution deploy-uninstall <deployment_id> <orchestrator_url> \
  -A <org> -I <app-id> -S <secret>
```

#### `solution delete-package`

Remove an uploaded package (not a deployment).

```bash
uipcli solution delete-package <solution_name> <version> <orchestrator_url> \
  -A <org> -I <app-id> -S <secret>
```

### 1.8 Exit codes & parsing

| Exit code | Meaning |
|---|---|
| `0` | Success |
| `1` | Generic failure - parse stdout/stderr for details |
| `2` | Invalid arguments |
| non-zero from `analyze` | Rule violations at Error severity (when `--stopOnRuleViolation`) |
| non-zero from `test run` | At least one test failed |
| non-zero from `job run --wait true --fail_when_job_fails true` | Job failed in Orchestrator |

Always redirect `--resultPath` / `--result_path` to files and parse them as JSON/XML. Don't rely on stdout scraping.

---

## Part 2 - `uipath` (the Python CLI)

### 2.1 What it is, what it covers

`uipath` is the agent developer CLI, shipped as a PyPI package. It handles the local dev -> test -> publish loop for Python-based coded agents (LangGraph, LlamaIndex, generic). For packaging and deployment, it currently wraps `uipcli` under the hood (downloaded on first use).

**Version policy:** pin with a floating range in `pyproject.toml`, for example `uipath>=2.8,<3`. Verified against `uipath 2.8.40` (April 2026).

### 2.2 Installation

**Preferred (`uv`, matching the project's Python conventions):**
```bash
uv init my-agent
cd my-agent
uv add uipath                   # base SDK + CLI
uv add uipath-langchain         # LangGraph extension
uv add uipath-llamaindex        # LlamaIndex extension
```

**Alternative (pip):**
```bash
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
.venv\Scripts\Activate.ps1      # Windows PowerShell
pip install "uipath>=2.8,<3" "uipath-langchain>=0.8,<1"
```

**Verify:**
```bash
uipath -lv
# Prints: uipath version X.Y.Z, uipath-langchain version X.Y.Z
```

**Prerequisites:**
- Python 3.11+ (3.10 may work for some packages but 3.11 is the supported floor).
- `uv` strongly preferred for dep management.

### 2.3 Global environment variables

| Variable | Purpose |
|---|---|
| `UIPATH_BASE_URL` | Base URL for authentication (e.g., `https://cloud.uipath.com/<org>/<tenant>`) |
| `UIPATH_CLIENT_ID` | External App client id for unattended auth |
| `UIPATH_CLIENT_SECRET` | External App client secret |
| `UIPATH_URL` | Legacy override of the auth domain |
| `UIPATH_PROJECT_ID` | Required for `uipath pull` / `uipath push` (Studio Web sync) |
| `UIPATH_DISABLE_SSL_VERIFY` | Disable SSL verification (dev only, not recommended) |
| `REQUESTS_CA_BUNDLE` | Custom CA bundle for SSL |
| `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` | Standard proxy config |
| `UIPATH_FOLDER_PATH` | Default Orchestrator folder for `invoke`/`publish` |

### 2.4 Commands

Verbs exposed by `uipath --help` in 2.8.40: `auth`, `new`, `init`, `run`, `pack`, `publish`, `invoke`, `deploy`, `eval`, `pull`, `push`.

#### `uipath auth`

Authenticate with UiPath Cloud. Supports interactive (browser OAuth) and unattended (client credentials).

```bash
# Interactive (default - opens browser)
uipath auth

# With cloud target
uipath auth --cloud      # default
uipath auth --staging
uipath auth --alpha

# Unattended / CI
uipath auth \
  --base-url https://cloud.uipath.com/<org>/<tenant> \
  --client-id <uuid> \
  --client-secret <secret>
```

Populates `.env` with tokens. Re-run when tokens expire.

---

#### `uipath new`

Scaffold a new agent project.

```bash
uipath new <agent_name>
# Creates: main.py, langgraph.json, pyproject.toml
# main.py uses: from uipath_langchain.chat import UiPathChat
#               llm = UiPathChat(model="gpt-4o-mini-2024-07-18")
# langgraph.json is minimal: {"graphs": {"agent": "./main.py:graph"}}
# Prints next steps: uipath init, uipath run
```

---

#### `uipath init`

Generate config/metadata files from your code. **Run after every schema change** (input/output schema, graph definition, function signatures).

```bash
uipath init
# Produces:
# - uipath.json           (schema, runtimeOptions, packOptions)
# - bindings.json         (connections, assets placeholders)
# - .uipath/*             (agent metadata)
# - *.mermaid diagram(s)  (when graph parses)
# - .env (if missing, requires UIPATH_BASE_URL / UIPATH_CLIENT_ID / UIPATH_CLIENT_SECRET)
# - CLAUDE.md, AGENTS.md, .agent/*  (unless --no-agents-md-override is passed)
```

`uipath init` needs successful auth to parse the graph fully. On auth failure it still emits `uipath.json` and `bindings.json` but exits non-zero and skips the agent-metadata files.

**Important:** pass `--no-agents-md-override` when the repo already has a maintained `CLAUDE.md` / `AGENTS.md` that you don't want overwritten.

---

#### `uipath run`

Execute the agent locally with JSON input.

```bash
# Basic
uipath run agent '{"topic": "UiPath"}'

# With input file
uipath run agent --input-file inputs/test1.json

# With debugging (requires debugpy)
uv pip install debugpy
uipath run agent '{"topic": "x"}' --debug
```

Outputs go to stdout; structured logs include timestamps.

---

#### `uipath pack`

Package the project into a `.nupkg`.

```bash
uipath pack [--nolock]
# Reads pyproject.toml [project] section:
#   name, version, description, authors
# Produces: <name>.<version>.nupkg in ./
```

Flags: only `--nolock` (skip `uv.lock` regeneration). No other flags in 2.8.40.

`pyproject.toml` must have a valid `[project]` table with `name`, `version`, `description`, `authors`. Missing fields cause pack to fail cryptically.

On first run, `uipath pack` downloads `uipcli` to `~/.uipath/cli/` - tolerate the delay.

---

#### `uipath publish`

Upload the most recently packed `.nupkg` to Orchestrator.

```bash
# Interactive feed selection
uipath publish

# To personal workspace
uipath publish -w

# To tenant processes feed
uipath publish -t

# From an explicit file
uipath publish -f <path/to/package.nupkg>
```

Flags: `-t` (tenant), `-w` (my workspace), `-f <file>` (explicit nupkg path).

After publish, the CLI prints a **process configuration link** - use it to set environment variables for the process (env vars are NOT packed into the agent; they're configured per-environment in Orchestrator).

---

#### `uipath invoke`

Start a job on an already-published process.

```bash
uipath invoke agent '{"topic": "UiPath"}'
# Prints: job started + monitor link
```

Operates like `run` but against the cloud deployment, not local code.

---

#### `uipath deploy`

Deploy the packed agent to Orchestrator. Accepts the same `-t / -w / -f` selection as `publish` plus folder / process arguments. Use `uipath deploy --help` on the installed version for the authoritative flag list.

---

#### `uipath eval`

Run an evaluation set against an agent.

```bash
uipath eval <entry-point> \
  --eval-set <path/to/eval-set.json> \
  [--num-workers 4] \
  [--output-file <results.json>] \
  [--no-report] \
  [--silent]
```

Gate CI promotion on the score threshold (e.g., >= 0.85 on the golden set).

---

#### `uipath pull` / `uipath push`

Sync with Studio Web projects.

```bash
# Requires UIPATH_PROJECT_ID env var
export UIPATH_PROJECT_ID=<uuid>

uipath pull      # pull remote Studio Web project -> local files
uipath push      # push local files -> Studio Web project
```

Use when collaborating with non-coders who edit in Studio Web browser UI.

---

### 2.5 Project config files

| File | Purpose | Who writes it |
|---|---|---|
| `pyproject.toml` | Python deps, project metadata | You |
| `langgraph.json` | Graph entry points (LangGraph) | `uipath new` scaffolds; you maintain |
| `agent_framework.json` | Agent entry points (generic) | You |
| `llama_index.json` | Entry points (LlamaIndex) | You |
| `uipath.json` | UiPath project metadata | `uipath init` |
| `bindings.json` | Resource bindings (connections, assets) | `uipath init`, you fill in |
| `project.uiproj` | Studio/Orchestrator project file | `uipath init` |
| `.env` | Local secrets + UiPath tokens | `uipath auth` |
| `.uipath/` | Metadata + state | `uipath init` |

**Rule:** never hand-edit `.uipath/*.json`. Re-run `uipath init` instead.

### 2.6 Example `langgraph.json` (what `uipath new` emits)

```json
{
  "graphs": {
    "agent": "./main.py:graph"
  }
}
```

Optionally add `"dependencies": ["."]` and `"env": ".env"` when you need them.

### 2.7 Example `pyproject.toml` (minimum)

```toml
[project]
name = "my-agent"
version = "0.0.1"
description = "my-agent"
authors = [{ name = "First Last", email = "me@example.com" }]
requires-python = ">=3.11"
dependencies = [
    "uipath>=2.8,<3",
    "uipath-langchain>=0.8,<1",
    "langgraph>=0.2",
]
```

---

## Part 3 - `uip` (the unified Node.js CLI)

`uip` (`@uipath/cli`) is the umbrella CLI used by the UiPath/skills submodule for skill-level operations. It is installed automatically by `skills/hooks/ensure-uip.sh` at session start.

### 3.1 Install

```bash
npm install -g @uipath/cli
npm install -g @uipath/servo        # Windows-only live UI automation
uip tools install @uipath/rpa-tool   # additional tooling
uip --version
```

### 3.2 Selected verbs

Consult the relevant `skills/skills/<skill>/SKILL.md` for authoritative usage. Common verbs:

- `uip rpa list-instances --format json` - list open Studio Desktop instances.
- `uip codedapp ...` - scaffold / build / debug Coded (Web/Action) Apps.
- `uip case ...` - Case Management preview.
- `uip df ...` - Data Fabric entity/record operations.
- `uip servo ...` - live UI automation for verification.
- `uip feedback send ...` - submit a feedback report to UiPath.
- `uip tools install <pkg>` - install auxiliary tools.

Use `uip <verb> --help` for exact flags.

---

## Part 4 - CI/CD patterns

### 4.1 GitHub Actions - RPA project

```yaml
name: UiPath CI
on:
  push:
    branches: [main, develop]
  pull_request:

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup UiPath CLI
        uses: Mikael-RnD/setup-uipath@v2
        with:
          platform-version: '25.10'

      - name: Restore dependencies
        run: uipcli package restore project.json

      - name: Analyze
        run: |
          uipcli package analyze project.json `
            --resultPath analyzer-results.json `
            --treatWarningsAsErrors
        shell: pwsh

      - name: Upload analyzer results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: analyzer-results
          path: analyzer-results.json

      - name: Pack
        run: |
          uipcli package pack project.json `
            -o output `
            --autoVersion `
            --repositoryUrl "${{ github.server_url }}/${{ github.repository }}" `
            --repositoryCommit "${{ github.sha }}" `
            --repositoryBranch "${{ github.ref_name }}" `
            --repositoryType GitHub
        shell: pwsh

      - name: Deploy to Dev (main branch only)
        if: github.ref == 'refs/heads/main'
        env:
          UIPATH_ORG: ${{ secrets.UIPATH_ORG }}
          UIPATH_APP_ID: ${{ secrets.UIPATH_APP_ID }}
          UIPATH_APP_SECRET: ${{ secrets.UIPATH_APP_SECRET }}
        run: |
          uipcli package deploy output\*.nupkg `
            https://cloud.uipath.com/ `
            DefaultTenant `
            -A "$env:UIPATH_ORG" `
            -I "$env:UIPATH_APP_ID" `
            -S "$env:UIPATH_APP_SECRET" `
            --orchestratorFolder "Dev" `
            --createProcess
        shell: pwsh
```

### 4.2 GitHub Actions - Python agent

```yaml
name: Agent CI
on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive   # so the skills submodule guard can run

      - name: Install uv
        uses: astral-sh/setup-uv@v3

      - name: Setup Python
        run: uv python install 3.11

      - name: Install deps
        run: uv sync

      - name: Run unit tests
        run: uv run pytest

      - name: Submodule guard
        run: uv run python -m uipath_claude.skills.submodule_guard --strict

      - name: uipath init
        env:
          UIPATH_BASE_URL: ${{ secrets.UIPATH_BASE_URL }}
          UIPATH_CLIENT_ID: ${{ secrets.UIPATH_CLIENT_ID }}
          UIPATH_CLIENT_SECRET: ${{ secrets.UIPATH_CLIENT_SECRET }}
        run: uv run uipath init --no-agents-md-override

      - name: uipath pack
        run: uv run uipath pack --nolock

      - name: Publish to personal workspace (main only)
        if: github.ref == 'refs/heads/main'
        env:
          UIPATH_BASE_URL: ${{ secrets.UIPATH_BASE_URL }}
          UIPATH_CLIENT_ID: ${{ secrets.UIPATH_CLIENT_ID }}
          UIPATH_CLIENT_SECRET: ${{ secrets.UIPATH_CLIENT_SECRET }}
        run: uv run uipath publish -w
```

### 4.3 Azure DevOps - Solutions pipeline

```yaml
trigger:
  branches: { include: [main] }

pool:
  vmImage: windows-latest

variables:
  SOLUTION_PATH: $(Build.SourcesDirectory)/solution
  SOLUTION_VERSION: 1.$(Build.BuildId).0

stages:
  - stage: Build
    jobs:
      - job: PackSolution
        steps:
          - task: UseDotNet@2
            inputs: { version: '8.0.x' }

          - powershell: dotnet tool install --global UiPath.CLI.Windows --version 25.10.*
            displayName: Install uipcli

          - powershell: |
              uipcli solution restore $(SOLUTION_PATH)
              uipcli solution analyze $(SOLUTION_PATH) `
                --resultPath $(Build.ArtifactStagingDirectory)/analyze.json
            displayName: Restore + Analyze

          - powershell: |
              uipcli solution pack $(SOLUTION_PATH) `
                -v $(SOLUTION_VERSION) `
                -o $(Build.ArtifactStagingDirectory)
            displayName: Pack

          - publish: $(Build.ArtifactStagingDirectory)
            artifact: solution

  - stage: DeployDev
    dependsOn: Build
    jobs:
      - deployment: DeployToDev
        environment: Dev
        strategy:
          runOnce:
            deploy:
              steps:
                - download: current
                  artifact: solution
                - powershell: |
                    uipcli solution upload-package $(Pipeline.Workspace)/solution/*.uipx `
                      https://cloud.uipath.com/ `
                      -A "$(UIPATH_ORG)" -I "$(UIPATH_APP_ID)" -S "$(UIPATH_APP_SECRET)" `
                      --applicationScope "OR.Solutions"
                    uipcli solution deploy-activate <solution-name> $(SOLUTION_VERSION) `
                      https://cloud.uipath.com/ `
                      -A "$(UIPATH_ORG)" -I "$(UIPATH_APP_ID)" -S "$(UIPATH_APP_SECRET)" `
                      --targetFolder "Dev" `
                      --bindings bindings/dev.json
```

### 4.4 CI optimization tips

- **NuGet restore is the slowest step.** Cache `%USERPROFILE%\.nuget\packages` (Windows) or `~/.nuget/packages` (Linux) between runs. On GitHub Actions: `actions/cache` keyed on `project.json` hash.
- **Pre-install CLI as a Docker layer** if you run many jobs on the same image - saves ~30s per job.
- **Parallelize analyze + tests** when you have multiple sub-projects in a Solution.
- **Fail fast on analyze.** A failed analyze saves 5+ minutes of pack/deploy work downstream.
- **Fail fast on submodule guard.** Run `python -m uipath_claude.skills.submodule_guard --strict` before anything else in the pipeline.

---

## Part 5 - Compatibility matrix (25.10)

| Component | Min version | Notes |
|---|---|---|
| UiPath CLI (25.10) | 25.10.x | Must equal or exceed Studio version |
| UiPath Studio | 25.10+ | Packaging version must match CLI |
| UiPath Robot | 25.10+ | |
| UiPath Orchestrator | 25.10+ | |
| .NET Runtime | 8.x | Desktop Runtime on Windows |
| Python | 3.11+ | For `uipath` CLI and SDKs |
| macOS | ARM64 only | Intel not supported |

**Legacy (Windows - Legacy projects):** use `UiPath.CLI.Windows.Legacy`. These cannot be included in Solutions.

---

## Part 6 - Quick cheatsheet

### Daily dev loop (RPA project)

```bash
uipcli package restore project.json
uipcli package analyze project.json --resultPath analyze.json
# inspect analyze.json; if errors, fix and loop
uipcli package pack project.json -o output --autoVersion
uipcli package deploy output\*.nupkg https://cloud.uipath.com/ DefaultTenant \
  -A <org> -I <app-id> -S <secret> \
  --orchestratorFolder Dev --createProcess
```

### Daily dev loop (agent)

```bash
uv sync
uipath init --no-agents-md-override           # after schema changes
uipath run agent '{"input":"test"}'            # local test
pytest                                         # unit tests
uipath pack --nolock                           # produces .nupkg
uipath publish -w                              # personal workspace
uipath invoke agent '{"input":"smoke"}'        # smoke against deployed
```

### Solution lifecycle

```bash
uipcli solution restore <solution-path>
uipcli solution analyze <solution-path> --resultPath analyze.json
uipcli solution pack <solution-path> -v 1.0.0 -o output
uipcli solution upload-package output\*.uipx <orch-url> -A <org> -I <id> -S <secret>
uipcli solution deploy-activate <name> 1.0.0 <orch-url> -A <org> -I <id> -S <secret> \
  --targetFolder Dev --bindings bindings/dev.json
```

---

## Part 7 - References

- [Official CLI docs (25.10)](https://docs.uipath.com/cicd-integrations/standalone/2025.10/user-guide/about-uipath-cli)
- [CLI command reference by task](https://docs.uipath.com/cicd-integrations/standalone/2025.10/user-guide/about-uipath-cli-tasks)
- [Solutions with CLI](https://docs.uipath.com/cicd-integrations/standalone/2025.10/user-guide/working-with-solutions)
- [Compatibility matrix](https://docs.uipath.com/cicd-integrations/standalone/2025.10/user-guide/compatibility-matrix)
- [`uipath` Python CLI docs](https://uipath.github.io/uipath-python/cli/)
- [`uipath-langchain` SDK](https://github.com/UiPath/uipath-langchain-python)
- [`uipath-python` SDK](https://github.com/UiPath/uipath-python)
- [UiPath/skills](https://github.com/UiPath/skills) (this repo's `skills/` submodule)
- [setup-uipath GitHub Action](https://github.com/Mikael-RnD/setup-uipath)
