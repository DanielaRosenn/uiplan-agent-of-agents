# UiPath End-to-End Workflows

> Companion to `CLAUDE.md`. Step-by-step flows for each paradigm: from zero to deployed, including AI-assistant-driven development, Studio Web, Maestro, Coded Apps, and Solutions. When you know the paradigm, jump to the relevant section.

**Contents:**
1. Scaffold a new project (any paradigm)
2. §RPA - Classic/coded RPA workflow
3. §CodedAutomation - C# coded automations
4. §LangGraphAgent / §CodedAgent - Python agents
5. §StudioWeb - Browser-based RPA workflows
6. §Maestro - BPMN orchestration
7. §CodedApp - Apps development
8. §ApiWorkflow - API workflows
9. §Solution - Multi-project bundles
10. §AI-assistant-driven builds - end-to-end with Cursor/Claude Code
11. §Troubleshooting - common failures and fixes

---

## 1. Scaffold

**Before scaffolding, pick the paradigm** - they are not freely convertible:

```
Is it pure UI automation (clicking, typing in apps)?
  -> RPA (XAML or coded C#)
Is it an LLM-driven task (reasoning, tool use, document understanding)?
  -> Coded Agent (Python; LangGraph, LlamaIndex, or generic)
Is it a business process spanning people + bots + agents + systems?
  -> Maestro process
Is it a user-facing app / form / dashboard?
  -> Coded App (Studio Web or `uip codedapp`)
Is it a pure API integration (HTTP, no UI)?
  -> API Workflow
Is it multiple of the above bundled together?
  -> Solution (wraps the sub-projects)
```

### Scaffold commands

| Paradigm | Command |
|---|---|
| RPA (XAML) | Open Studio Desktop -> New Project -> Blank Process; AI does not scaffold XAML from scratch |
| Coded Automation | Studio Desktop -> Coded Workflow template |
| LangGraph Agent | `uv init <name> && cd <name> && uv add uipath uipath-langchain langgraph && uv run uipath new <name>` |
| Generic Python Agent | `uv init <name> && cd <name> && uv add uipath && uv run uipath new <name>` |
| LlamaIndex Agent | `uv init <name> && cd <name> && uv add uipath uipath-llamaindex && uv run uipath new <name>` |
| Studio Web (RPA/App) | Browser -> studio.uipath.com -> Create |
| Maestro process | Studio Web -> New Process (BPMN canvas) |
| Coded App / Coded Action App | `uip codedapp <scaffold-verb>` (see `skills/skills/uipath-coded-apps/SKILL.md`) |
| Solution | Studio Web -> Solutions -> Create Solution (Automation Cloud only) |

---

## 2. §RPA - RPA workflow (XAML) {#rpa}

### Dev flow (human-driven, AI-assisted)

```
  +---------------------------------------------------------+
  |  1. Clone repo                                           |
  |  2. Open project.json in Studio Desktop                  |
  |  3. AI scaffolds helper workflows / argues with analyzer |
  |  4. Human designs / connects activities in Studio        |
  |  5. AI runs analyze + pack + test locally                |
  |  6. Commit -> PR -> CI runs analyze + pack + test        |
  |  7. Merge -> CD deploys to Dev folder                    |
  |  8. Human validates in Orchestrator                      |
  |  9. Promote to Test / Prod via pipeline                  |
  +---------------------------------------------------------+
```

### Commands - day-to-day

```bash
# First time on a fresh clone
uipcli package restore project.json

# Before every commit
uipcli package analyze project.json --resultPath analyze.json
# -> Inspect analyze.json. If errors > 0, fix in Studio.

# Before testing a build
uipcli package pack project.json -o output --autoVersion

# Run local tests (test project must exist)
uipcli test run Tests\project.json https://cloud.uipath.com/ <tenant> \
  -A <org> -I <app-id> -S <secret> \
  --testset "Smoke" --result_path test-results.xml
```

### AI-assistant boundaries for XAML {#xaml-ai-edits}

XAML is XML under the hood. AI assistants can safely edit XAML for:
- Changing literal values inside `<InArgument>` / `<OutArgument>` (e.g., a URL, a file path, a boolean flag).
- Adding `<ui:LogMessage>` activities at well-known insertion points (start of `Main.xaml`, inside catch blocks).
- Renaming variables/arguments **only if** also updating every reference (use find-replace, not blind edit).
- Updating `project.json` metadata (name, version, description, dependencies).

AI assistants should NOT:
- Create new XAML workflows from scratch (structural errors cascade silently - Studio catches them).
- Add new activities of types not already present in the workflow (namespace imports and dependencies get tricky).
- Edit `.xaml.metadata.json` files (auto-generated).
- Touch the `.local/` subfolder.

If the user asks for a structural XAML change, propose the change in prose, let the human make it in Studio, then help validate via `analyze`.

### REFramework specifics

REFramework defines a canonical state-machine pattern. The four states are:

1. **Initialization** - read Config.xlsx, open apps, initialize queues/assets.
2. **Get Transaction Data** - pull the next item from the queue (or data table).
3. **Process Transaction** - business logic for a single transaction.
4. **End Process** - close apps, clean up, send summary.

Notes:
- `Config.xlsx` is the source of truth for settings - treat it as data, check it in.
- Queue-driven projects: the AI can help design queue item schemas and generate the C# to `Add Queue Item`, but not rewire the state machine.
- Logs: every `Process.xaml` invocation should log `TransactionNumber` + `TransactionItem.Reference`.

---

## 3. §CodedAutomation - Coded automations (C#) {#codedautomation}

Coded Workflows are pure C# projects created from the "Coded Workflow" template in Studio. They live alongside XAML in the same `project.json`.

### Dev flow

1. **Scaffold**: Studio Desktop -> New -> Coded Workflow (`.cs` file in `project.json` tree).
2. **Edit** in Studio OR in Cursor/VS Code - the files are just C#. Full AI assistance works.
3. **Build & run**: Studio Desktop has a "Run" button that compiles and executes. CLI: `uipcli package pack` also compiles.
4. **Test**: same `uipcli test run` flow as RPA. Coded Test projects are a dedicated project type (`--outputType Tests`).

### AI editing latitude

Coded Workflows are the sweet spot for AI assistance:
- AI can write complete workflows end-to-end.
- AI can refactor, add methods, split files, add tests.
- AI should respect the `UiPath.CodedWorkflows` namespace and use the injected `workflow` context object (don't instantiate your own activity classes).
- Modern experience conventions apply - no `.NET Framework`, no VB.

### Common pattern - calling existing XAML from C#

```csharp
public override async Task Execute(CodedWorkflowContext context)
{
    var input = new Dictionary<string, object> { ["CustomerId"] = "C-12345" };
    var output = await RunWorkflow("Subworkflows/GetCustomer.xaml", input);
    var name = output["CustomerName"]?.ToString();
    Log($"Retrieved customer: {name}");
}
```

---

## 4. §LangGraphAgent / §CodedAgent - Python coded agents {#langgraphagent}

### End-to-end flow

```
  +--------------------------------------------------------------+
  |  uv init       ->  uv add uipath uipath-langchain langgraph  |
  |       v                          v                           |
  |  pyproject.toml            uipath new <name>                 |
  |                                  v                           |
  |                     main.py + langgraph.json                 |
  |                                  v                           |
  |                          uipath auth                         |
  |                                  v                           |
  |                          uipath init                         |
  |                                  v                           |
  |           (uipath.json, bindings.json, *.mermaid)            |
  |                                  v                           |
  |        +----  uipath run '{...}'  ----+  <- local dev loop   |
  |        |                              |                      |
  |        v                              v                      |
  |      pytest                      iterate code                |
  |        v                                                     |
  |   uipath pack                                                |
  |        v                                                     |
  |   uipath publish -w                                          |
  |        v                                                     |
  |   (set env vars via returned config link)                    |
  |        v                                                     |
  |   uipath invoke agent '{"input":"smoke"}'                    |
  |        v                                                     |
  |   promote to tenant feed via Solutions pipeline              |
  +--------------------------------------------------------------+
```

### Minimum project structure

```
my-agent/
├── main.py                     # graph definition + state
├── langgraph.json              # entry point config
├── pyproject.toml
├── uv.lock
├── .env.example                # document required env vars
├── .gitignore                  # include .env, .venv, .uipath/cache
├── README.md
├── tests/
│   ├── test_main.py
│   └── fixtures/
│       └── sample_input.json
└── docs/
    ├── ARCHITECTURE.md
    └── hitl-design.md
```

After `uipath init`, expect these to appear (all generated, check in except `.env`):

```
├── .uipath/
├── uipath.json
├── bindings.json
├── agent.mermaid
└── project.uiproj
```

### Minimum `main.py` (what `uipath new` produces)

```python
from typing import TypedDict
from langgraph.graph import StateGraph, END
from uipath_langchain.chat import UiPathChat


class State(TypedDict):
    input: str
    output: str


llm = UiPathChat(model="gpt-4o-mini-2024-07-18")


def node_process(state: State) -> State:
    result = llm.invoke([{"role": "user", "content": state["input"]}])
    return {"input": state["input"], "output": result.content}


workflow = StateGraph(State)
workflow.add_node("process", node_process)
workflow.set_entry_point("process")
workflow.add_edge("process", END)
graph = workflow.compile()
```

### Minimum `langgraph.json`

`uipath new` emits the simplest form:

```json
{
  "graphs": {
    "agent": "./main.py:graph"
  }
}
```

Add `"dependencies": ["."]` and `"env": ".env"` only when you actually need them.

### Human-in-the-loop (HITL) pattern

Default to UiPath Action Center, which is native, Maestro-compatible, and already integrated with `uipath-langchain`:

```python
from uipath_langchain.interrupt import interrupt_for_action

approval = interrupt_for_action(
    app_name="ApprovalApp",
    title="Request review",
    data={"customer": customer_id, "amount": amount},
)
if approval["decision"] == "approved":
    # proceed
    ...
```

Swap to a custom HITL platform (Adaptive Cards in Slack/Teams, etc.) only when the project's SDD explicitly requires it; reference `skills/skills/uipath-human-in-the-loop/SKILL.md` for the detailed pattern.

### Debugging

```bash
uv pip install debugpy

uipath run agent '{"topic":"x"}' --debug

# In VS Code / Cursor, attach to port (launch.json):
{
  "name": "Attach to uipath run",
  "type": "python",
  "request": "attach",
  "connect": { "host": "localhost", "port": 5678 }
}
```

### Eval / regression testing

Use `uipath eval` with an eval set. Structure:

```
evals/
├── eval-set.json        # inputs + expected outputs + evaluator refs
├── evaluators.py        # scoring functions
└── README.md
```

Run it:

```bash
uipath eval agent --eval-set evals/eval-set.json --output-file evals/results.json
```

Gate CI promotion on eval score threshold (for example, >= 0.85 on the golden set).

---

## 5. §StudioWeb - Studio Web (browser) {#studioweb}

Studio Web is UiPath's browser-based IDE. It's the primary tool for:
- Maestro BPMN modeling.
- Coded Apps (UI forms and dashboards).
- Lightweight RPA / API workflows.
- Agent design (visually - Autopilot integration).

### Cloud vs Local workspace

**Cloud workspace:**
- Project lives in Automation Cloud.
- Version control via snapshots (auto every 40min + on close + on publish).
- No git.
- Ideal for quick prototyping, non-developers.

**Local workspace (added Dec 2025):**
- Project saved on your machine.
- Built-in git integration (init, branch, commit, push, pull, resolve conflicts).
- Connects to GitHub / Azure DevOps / other git remotes.
- Ideal for version-controlled team development.

### Sync with CLI-driven development

Developers using Cursor/Claude Code locally can sync with a Studio Web project:

```bash
# In the local project dir
export UIPATH_PROJECT_ID=<studio-web-project-uuid>
uipath pull                  # bring remote state down
# ... edit locally in Cursor ...
uipath push                  # push up to Studio Web
```

This enables a hybrid model: business users collaborate in Studio Web; developers work in Cursor with the full CLI toolchain.

### Studio Web source control policies

Org admins can configure source control policies via Automation Ops:
- **GitHub**: install `UiPath-AutomationOps` app on repos; Studio Web commits via OAuth.
- **Azure DevOps** (preview): connect organization; policy-based repo access.

---

## 6. §Maestro - BPMN orchestration {#maestro}

Maestro is UiPath's cloud-native orchestration layer for long-running processes. It models with BPMN 2.0, decisions with DMN, and coordinates bots + agents + humans + APIs.

### Lifecycle

```
  Model           Implement        Operate         Monitor       Optimize
    v                 v                v              v              v
 Studio Web      Studio Web +     Orchestrator   Insights +     Process Mining
 (BPMN + DMN)    Maestro editor   + Maestro      Maestro        + Process App
                                  Instance Mgmt  dashboards
```

### Dev flow

1. **Model** (Studio Web): drag BPMN tasks, gateways, events. Use Autopilot for Maestro to prompt-generate initial diagrams. Save as `.bpmn`.
2. **Implement**: bind tasks to:
   - **User tasks** -> human roles (assignee via Orchestrator).
   - **Service tasks** -> Integration Service connectors OR custom automations OR agents.
   - **Script tasks** -> inline expressions (JavaScript is the default; C# expressions are deprecated, migrate to JS for any new work).
   - **Business Rules tasks** -> DMN decisions.
3. **Variables**: define process-scope variables in the editor; use JavaScript expressions for logic.
4. **Test**: Maestro has a Simulate/Debug mode in Studio Web.
5. **Publish**: publishes the process as a Solution.
6. **Deploy**: use Orchestrator Solutions UI or `uipcli solution deploy-activate`.
7. **Operate**: use Maestro Instance Management to pause / resume / retry / audit live instances.

### Key concepts

| Term | Meaning |
|---|---|
| Process Model | The BPMN diagram (the "what") |
| Implementation | The runtime bindings (the "how") |
| Solution | The deployable package containing the process + its resources |
| Instance | A single running execution of the process |
| Start event | The entry point; multiple per BPMN are allowed and identified by `filepath#displayname` |
| User task | A task assigned to a human; creates a work item in Orchestrator |
| Service task | A task bound to a connector, workflow, agent, or API |
| Exclusive gateway | If/else-style routing based on conditions |
| Timer event | Time-based trigger (e.g., "escalate after 24h") |

### Example - Purchase request approval

Reference pattern (from UiPath docs):

```
[Start: Request submitted]
     v
[Variables: Amount:number, RequesterEmail:string]
     v
[User task: Manager review]  ---- [Timer: 24h -> Escalate]
     v
[Exclusive gateway: Amount > 5000?]
     |-- true  -> [User task: CFO review] -> (join)
     +-- false -> ----------------------------> (join)
                           v
          [Service task: Create PO via connector]
                           v
          [Send task: Email outcome to RequesterEmail]
                           v
                        [End]
```

### AI assistant latitude in Maestro

- AI can read/summarize `.bpmn` files (they're XML).
- AI can help write DMN decision tables in XML.
- AI can write the code for any Service task that points to a coded agent or workflow.
- AI should NOT hand-edit `.bpmn` structure (easy to break layout / validation). Propose changes in words; let the human drag-and-drop.

### Maestro + REFramework

Maestro does NOT replace REFramework for transactional RPA. Use Maestro to orchestrate across bots + agents + people; use REFramework inside a bot that Maestro calls. See the [Maestro and ReFramework FAQ](https://docs.uipath.com/maestro/automation-cloud/latest/user-guide/maestro-and-reframework-faq).

---

## 7. §CodedApp - Coded Apps {#codedapp}

Apps in UiPath are forms, dashboards, and user-facing interfaces. "Coded Apps" are developed code-first via the `@uipath/uipath-typescript` SDK and packaged with `uip codedapp`; they can be deployed standalone or as part of a Solution (Unified Build).

### Key rules

- **VB-based Legacy Apps are deprecated.** New apps must use JavaScript/TypeScript and the Coded Apps toolchain. VB expressions inside existing Apps continue to work but new Apps should not rely on them.
- Public apps can be packaged/deployed as part of Unified Build solutions.
- `app.config.json` + `action-schema.json` mark a Coded App project. See `skills/skills/uipath-coded-apps/SKILL.md` for the full authoring guide.
- Apps ship as part of a Solution for multi-environment deployment.

### Dev flow

1. **Scaffold** via `uip codedapp` (see the skill).
2. **Design** the app UI using the `@uipath/uipath-typescript` SDK.
3. **Bind** app actions to processes, queues, assets, or agents (the "backend").
4. **Commit** to git (Local Workspace supported).
5. **Package** standalone or via Solution: the app sits alongside processes/agents in a Solution bundle.
6. **Deploy** via `uipcli solution deploy-activate` with the bindings file that maps app actions to the target environment's resources.
7. **Activate**: apps must be activated using the link provided by the deployment. Deployment activation fails if apps aren't activated.

### AI assistant role

Apps are UI-heavy. AI's strongest contribution is:
- Writing the TypeScript action handlers and data fetch logic.
- Writing the backend processes/agents the app calls.
- Generating sample data / mock inputs for app testing.
- Writing documentation for the app (user guide, admin guide).

Do not hand-edit the app design files inside Studio Web without the designer open.

---

## 8. §ApiWorkflow - API workflows {#apiworkflow}

API Workflows are cross-platform, HTTP-first workflows (no UI, no Windows desktop). They run on the serverless robot and are ideal for integrations, webhooks, orchestrated API calls.

### Key traits

- Project type: `ApiWorkflow` in `project.json`.
- Cross-platform: runs on Linux runners.
- No UI activities, no desktop automation.
- Treated identically to RPA by `uipcli` (same pack/analyze/deploy flow).

### When to use over a coded agent

| Use API Workflow when... | Use Coded Agent when... |
|---|---|
| Deterministic HTTP orchestration | LLM reasoning / planning needed |
| Simple request-response flows | Stateful multi-turn conversations |
| Tight integration with UiPath activities | Python ecosystem libraries needed |
| Business users will maintain the logic | Developer-only maintenance |

### CLI flow - identical to RPA

```bash
uipcli package restore project.json
uipcli package analyze project.json --resultPath analyze.json
uipcli package pack project.json -o output --autoVersion
uipcli package deploy output\*.nupkg <orch-url> <tenant> -A <org> -I <id> -S <secret>
```

---

## 9. §Solution - Multi-project Solutions {#solution}

Solutions bundle multiple projects (RPA, agents, apps, API workflows, libraries) into a single versioned, deployable unit. CLI support (25.10) enables full CI/CD integration.

### When to use a Solution

- End-to-end process spans multiple project types (e.g., RPA bot + Coded Agent + App + shared Library).
- Need environment-specific bindings centralized (dev/test/prod configs in one place).
- Want single-click deployment of an entire process.
- Using Maestro (Maestro processes always publish as Solutions).

### When NOT to use a Solution

- Single standalone process or library.
- On-prem / Automation Suite Orchestrator (CLI Solutions commands only work against Automation Cloud).
- Project includes a Windows - Legacy component (not supported in Solutions).

### Solution lifecycle

```
  +--------------------------------------------------------------+
  |  1. CREATE solution in Studio Web (or scaffold from template)|
  |  2. ADD projects (existing repos, or new sub-projects)       |
  |  3. DEFINE bindings (connections, assets, machines, roles)   |
  |  4. COMMIT to git (local workspace)                          |
  |                                                              |
  |  -- CI pipeline runs: --                                     |
  |  5. RESTORE deps (per sub-project)                           |
  |  6. ANALYZE each sub-project                                 |
  |  7. PACK solution (.uipx bundle containing sub-pkgs)         |
  |  8. UPLOAD-PACKAGE to Orchestrator Solutions                 |
  |                                                              |
  |  -- CD pipeline runs: --                                     |
  |  9. DEPLOY (creates deployment; inactive)                    |
  | 10. FILL BINDINGS (via download-config -> edit -> re-deploy) |
  | 11. DEPLOY-ACTIVATE (makes it live; triggers, schedules)     |
  | 12. MONITOR in Orchestrator Solutions tab                    |
  +--------------------------------------------------------------+
```

### Minimum Solution repo layout

```
solution-repo/
├── solution.uipx                # top-level solution descriptor
├── projects/
│   ├── Process.Alpha/           # RPA sub-project
│   │   ├── project.json
│   │   └── Main.xaml
│   ├── Agent.Beta/              # Coded agent sub-project
│   │   ├── langgraph.json
│   │   ├── main.py
│   │   └── pyproject.toml
│   └── Library.Shared/          # Shared library
│       └── project.json
├── bindings/
│   ├── dev.json
│   ├── test.json
│   └── prod.json
├── apps/                        # any Coded Apps
└── docs/
    └── solution-design.md
```

### Versioning rule - CRITICAL

Solutions do **NOT** auto-increment versions. You **must** pass `-v <version>` to `uipcli solution pack`. This is by design - enterprise teams control release numbering explicitly.

Common pattern in CI:

```yaml
SOLUTION_VERSION: 1.$(Build.BuildNumber).0    # Azure DevOps
# or
SOLUTION_VERSION: 1.$(github.run_number).0    # GitHub Actions
```

### Bindings - the environment mapping

`bindings.json` per environment maps abstract resources to concrete ones:

```json
{
  "connections": {
    "SalesforceConnection": "connection-id-dev-xyz"
  },
  "assets": {
    "ApiTimeout": { "value": 30, "type": "Integer" }
  },
  "machines": {
    "DefaultWorker": "machine-dev-01"
  },
  "roles": {
    "Approver": "group-dev-approvers"
  }
}
```

Use `uipcli solution download-config` on an existing deployment to generate the template for new environments.

### Activation states and what to do about them {#solution-activation-troubleshooting}

After deploy, Orchestrator evaluates readiness:

| Status | What it means | What to do |
|---|---|---|
| `Inactive (Ready to activate)` | Everything resolved | Run `uipcli solution deploy-activate` (or the Orchestrator UI) |
| `Inactive (Needs setup to activate)` | Bindings missing | `uipcli solution download-config` -> fill in -> re-deploy with `--bindings` |
| `Active` | Live | Monitor in Orchestrator |
| `Deploying` | In progress | Wait |
| `Failed` | Pack/upload/deploy failed | Check Orchestrator logs; `solution delete-package` and retry |

### Solutions + Maestro

Maestro processes ship exclusively as Solutions. When you publish a Maestro process, Studio Web creates a Solution package containing the BPMN + any bound sub-processes. Deploy via standard Solutions CLI.

### Solutions + Automation Ops Pipelines

UiPath provides a pre-built Solution Deployment Pipeline in the Marketplace. It pairs with a CSV config file (`PathToProjectJson,PackageName,OrchestratorFolder,ProcessName,RunTests`) mapping sub-projects to build steps. Use this when you don't want to roll your own CI; otherwise, use the CLI directly in GitHub Actions / Azure DevOps / Jenkins.

---

## 10. §AI-assistant-driven builds - end-to-end {#ai-assistant-driven}

This is the workflow **you**, the AI assistant, should execute when the user says "build me a UiPath X".

### Step 0 - Run project discovery

If `.claude/rules/project-context.md` doesn't exist (or the user asked to regenerate it), invoke the `uipath-project-discovery-agent` from `skills/agents/`. It returns a 200-line project summary (identity, dependencies, entry points, conventions). Write it to `.claude/rules/project-context.md` and use it as the factual basis for the rest of the flow.

### Step 1 - Understand what they want

Ask if unclear:
- Paradigm (RPA / Agent / Maestro / App / Solution)?
- Target environment (Dev / personal workspace / something else)?
- Existing project to extend, or greenfield?
- Timeline constraint (quick prototype vs production-ready)?

### Step 2 - Read before writing

- Scan repo: find `project.json`, `langgraph.json`, `solution.uipx`, `pyproject.toml`, `.bpmn` files.
- Determine paradigm (`CLAUDE.md` §1).
- Read the relevant §section of this doc.

### Step 3 - Scaffold

Follow §1 "Scaffold commands". For agents, the full bootstrap is:

```bash
cd /path/to/projects
uv init my-agent --python 3.11
cd my-agent
uv add uipath uipath-langchain langgraph
uv run uipath new my-agent     # generates main.py + langgraph.json
```

### Step 4 - Implement

Write the code. For agents:
- `main.py`: graph + state + nodes.
- `pyproject.toml`: `[project]` block with `name`, `version`, `description`, `authors`.
- `.env.example`: document required env vars (`UIPATH_BASE_URL`, `UIPATH_CLIENT_ID`, `UIPATH_CLIENT_SECRET`).
- `tests/`: at minimum, one happy-path pytest.

For RPA coded workflows:
- `.cs` files in the project tree.
- Use `UiPath.CodedWorkflows` namespace.
- Inject the workflow context; don't instantiate activities directly.

### Step 5 - Initialize UiPath project

```bash
uv run uipath init --no-agents-md-override
```

This generates `uipath.json`, `bindings.json`, mermaid diagram(s), and `project.uiproj`. The `--no-agents-md-override` flag prevents clobbering an existing `CLAUDE.md` / `AGENTS.md`.

**Verify** the mermaid diagram makes sense (it's a sanity check on your graph structure).

### Step 6 - Local test loop

```bash
uv run pytest
uv run uipath run agent '{"input": "sample"}'
```

### Step 7 - Analyze (RPA only)

```bash
uipcli package analyze project.json --resultPath analyze.json
```

Parse `analyze.json`. **If `severity == "Error"` count > 0, do not proceed.** Surface errors to the user, fix them in Studio (or in code if coded workflow), re-run.

### Step 8 - Pack

Agent:
```bash
uv run uipath pack --nolock
# Produces <name>.<version>.nupkg
```

RPA:
```bash
uipcli package pack project.json -o output --autoVersion
```

### Step 9 - Authenticate

```bash
# Agent - interactive OAuth
uv run uipath auth

# RPA - external app, done via CI secrets
```

### Step 10 - Publish to personal workspace (NOT tenant feed)

Agent:
```bash
uv run uipath publish -w
# Note the returned link - use it to configure env vars
```

RPA:
```bash
uipcli package deploy output\*.nupkg https://cloud.uipath.com/ <tenant> \
  -A <org> -I <app-id> -S <secret> \
  --orchestratorFolder "<user>-PersonalWorkspace" \
  --createProcess
```

### Step 11 - Smoke test

```bash
# Agent
uv run uipath invoke agent '{"input": "smoke"}'

# RPA
uipcli job run "<process_name>" https://cloud.uipath.com/ <tenant> \
  -A <org> -I <id> -S <secret> \
  --folder_organization_unit "<user>-PersonalWorkspace" \
  --wait true --fail_when_job_fails true \
  --job_result smoke-result.json
```

### Step 12 - Hand off

Report to the user:
- What was built (project name, paradigm, key logic).
- Where it lives (path, git branch).
- Analyzer output summary (0 errors, X warnings).
- Test / eval results (pass/fail count, score).
- Published location (personal workspace link).
- Smoke test result.
- Recommended next steps (merge, promote, add to Solution, etc.).

**Do not** merge to main, deploy to shared folders, or activate in Test/Prod without explicit user confirmation.

---

## 11. §Troubleshooting {#troubleshooting}

### Analyzer failures

**"Rule ST-USG-010: Unused variable"** -> remove the variable or mark it `[UsedImplicitly]` equivalent.

**"Rule ST-NMG-004: Variable naming convention"** -> rename to camelCase (variables) or PascalCase (arguments). Convention: variables `camelCase`, arguments `in_PascalCase` / `out_PascalCase` / `io_PascalCase`.

**"Rule ST-MRD-005: Package restrictions"** -> the project references a non-allowlisted package. Either add to allowlist (requires platform team) or swap for an approved alternative.

**"Rule SEC-001: Hardcoded credentials"** -> move to Orchestrator Asset, reference via `Get Credential` activity or `sdk.assets.retrieve()`.

### Pack failures

**"Could not find file 'project.json'"** -> cd into the project dir, or pass full path.

**"NuGet restore failed"** -> check network, clear NuGet cache (`dotnet nuget locals all --clear`), check private feed credentials, verify `.nuget/nuget.config` is correct.

**"The specified version is invalid"** -> versions must be valid semver. `v1.0.0` is wrong; use `1.0.0`.

**"Mismatched CLI and Studio version"** -> upgrade CLI to match Studio, or pin Studio version to CLI version.

**"IResource incompatibility after library upgrade"** -> since Feb 2026, library references that previously used `.Name` must use `.FullName` to match the `IResource` contract. Rebuild dependent projects after upgrading the library.

### Deploy failures

**"Unauthorized" (401)** -> client credentials wrong, or scope missing. Check `--applicationScope` includes required scopes for the operation.

**"Folder not found"** -> classic folders are not supported since 2023.4. Migrate to modern folders.

**"Package already exists"** -> same version already uploaded. Bump version. `uipcli` does not provide a package-delete verb; remove via Orchestrator UI if needed.

### Agent runtime failures

**"Missing entry-point"** -> you changed `langgraph.json` but didn't re-run `uipath init`. Run it.

**"ModuleNotFoundError in Orchestrator"** -> `pyproject.toml` dependencies incomplete. Add the missing dep, `uipath pack`, `uipath publish` again.

**"LLM Gateway returned 429"** -> rate limited. Add retry/backoff; consider BYO-LLM for heavy workloads (via AI Trust Layer bring-your-own-LLM).

**"bindings.json invalid"** -> re-run `uipath init` to regenerate structure; fill in environment-specific values manually.

**"uipath init fails with Authorization required"** -> the CLI cannot parse the graph without a valid session. Run `uipath auth` or set `UIPATH_BASE_URL`/`UIPATH_CLIENT_ID`/`UIPATH_CLIENT_SECRET` in `.env` first.

### Solutions failures

**"Needs setup to activate"** -> bindings missing. Run `uipcli solution download-config`, fill it in, re-deploy with `--bindings`.

**"Apps activation failed"** -> apps in the solution must be activated explicitly via the returned link before the solution deployment can activate. Check the deployment config screen in Orchestrator.

**"Folder not supported on target tenant"** -> Solutions require the target tenant to have modern folders and the Solutions feature enabled (Automation Cloud only).

### Maestro failures

**"Variable not in scope after moving node"** -> since Feb 2026, Maestro auto-updates scope; if still seeing this, re-save the process and reload the canvas.

**"Start event not found in Orchestrator"** -> check that the start event has a `displayname`; Orchestrator references them as `filepath#displayname`.

**"C# expression will be removed"** -> migrate to JavaScript expressions. C# expressions in Maestro are deprecated; do not write new C# expressions.

### Git / Studio Web failures

**"Merge conflict in .xaml"** -> XAML conflicts are painful. Use Studio's built-in "Workflow Diff" / "Solve conflicts" tool rather than manual XML editing.

**"Studio Web can't edit files"** -> browser permission prompt must be granted. In Chrome/Edge: reload, allow file edit permission when prompted.

**"Local workspace disconnected from git"** -> use the Disconnect option only intentionally. To reconnect, initialize git again and push to remote.

### Submodule / rule set failures

**"Submodule guard failed: HEAD not in approved list"** -> someone advanced `skills/`. Either approve the new commit by appending it to `.uipath/skills-approved.sha`, or reset the submodule with `git -C skills checkout <approved-sha>`.

**"Submodule guard failed: dangling skill reference in CLAUDE.md"** -> the doc mentions a `uipath-*` skill that doesn't exist in `skills/skills/`. Fix the doc or install the skill as an extension under `extensions/skills/`.

---

## Quick navigation

| If you need to... | Jump to |
|---|---|
| Build an agent from zero | §LangGraphAgent + §AI-assistant-driven |
| Add CI to an RPA project | §RPA + `docs/uipath-cli.md` §CI-patterns |
| Design a Maestro process | §Maestro |
| Bundle multiple projects together | §Solution |
| Debug an analyzer failure | §Troubleshooting |
| Understand Studio Web vs CLI tradeoffs | §StudioWeb + `CLAUDE.md` §4 |
| Scaffold a compliant project | §1 + `CLAUDE.md` §9 |
