# `/pdd` lifecycle

The `/pdd` slash command drives the full UiPath build lifecycle: from a one-paragraph brief, through six agent passes, into a scaffolded project that is validated, optionally executed, packaged, published, and deployed to Orchestrator.

- Entry point: [`uipath_claude/commands/pdd.py`](../uipath_claude/commands/pdd.py)
- Orchestrator: [`uipath_claude/query/pdd_lifecycle.py`](../uipath_claude/query/pdd_lifecycle.py) (`run_pdd_lifecycle`)
- Agents: [`uipath_claude/agents/`](../uipath_claude/agents/) (`ba`, `sa`, `add`, `tdd`, `developer`, `qa`)

## Quick reference

```
/pdd "<brief>" [--project-type process|maestro] [--deploy] [--folder <name>]
```

| Flag | Default | Effect |
|------|---------|--------|
| `--project-type` / `--type` | `process` | `process` -> `uip rpa` toolchain. `maestro` -> `uip flow` toolchain. |
| `--deploy` | off | After validate, also run `run`, `publish`, and `deploy` stages on a real Orchestrator tenant. Without it, the lifecycle stops at QA on the implementation plan. |
| `--no-deploy` | (default) | Explicitly disable deploy. |
| `--folder` | `Shared` | Orchestrator folder used by the deploy stage. |

Examples:

```text
/pdd "Read invoices from Outlook and queue them"
/pdd --deploy --folder Shared "Read invoices from Outlook and queue them"
/pdd --project-type maestro --deploy "Triage support tickets across email and Slack"
```

## Naming: SDD vs lifecycle TDD

In this repository the words mean **different artefacts** in the same `/pdd` pipeline:

| Term | Meaning here |
| --- | --- |
| **SDD** | Solution Design Document produced by the **`sdd`** stage (SA agent), seeded from the PDD. |
| **Lifecycle TDD** | The **`tdd`** stage output (`docs/tdd/<stamp>.md`): technical + test design seeded from the ADD. It is **not** the same document as the SDD. |
| **“TDD” in the methodology sense** | Red/green/refactor test-first coding — a **general software practice**, not the name of the `tdd` stage file unless context says so. |

Do not conflate **SDD** with the **`tdd`** stage artefact; both are produced in sequence for the default UiPath lifecycle ([stages table](#stages) below).

## Stages

Defined as `STAGES = ("pdd", "sdd", "add", "tdd", "scaffold", "implement", "validate", "run", "publish", "deploy")`. Every stage records `{"status": "ok"|"failed"|"skipped", ...}` in the result `stages` map. The first failed stage short-circuits the lifecycle and returns `failed_at=<stage>` plus `error=<message>`.

| # | Stage | Driver | Notes |
|---|-------|--------|-------|
| 1 | `pdd` | `BAAgent` via `invoke_agent_llm` | Markdown PDD persisted via `BootstrapArtifactWriter.write_pdd` |
| 2 | `sdd` | `SAAgent` | Seeded with the PDD text |
| 3 | `add` | `ADDAgent` | Architecture Design Document, seeded with the SDD |
| 4 | `tdd` | `TDDAgent` | Technical + test design, seeded with the ADD |
| 5 | `scaffold` | `_scaffold_process` (RPA: `create_project` tool) or `_scaffold_maestro` (`uip solution new` + `uip flow init` + `uip solution project add`) | Creates `generated/automation/<stamp>/<project>/` |
| 6 | `implement` | `DeveloperAgent` | Writes `IMPLEMENTATION_PLAN.md` into the project; agent receives PDD/SDD/ADD/TDD as context |
| 7 | `validate` | `build_and_verify_workflow` (RPA) or `uip flow validate` (maestro) | Runs the validator gate |
| 8 | `run` | `build_and_verify_workflow(run_after_validate=True)` (RPA). Maestro is `skipped` (requires cloud auth, covered by integration tests). | Only when `--deploy` |
| 9 | `publish` | `deploy_tool.publish_project` | Pack + publish `.nupkg` to Orchestrator. Only when `--deploy`. |
| 10 | `deploy` | `deploy_tool.deploy_to_orchestrator_v2` | Create the Orchestrator process under `--folder`. Only when `--deploy`. |

When `deploy=False`, stages 8/9/10 are recorded as `{"status": "skipped", "reason": "deploy=False"}`, and a final QA pass runs against the implementation plan (`QAAgent` -> `BootstrapArtifactWriter.write_qa`).

## Sub-agent invocation model

All six agents (BA/SA/ADD/TDD/Developer/QA) run through one shared helper: [`uipath_claude/query/agent_invoke.py`](../uipath_claude/query/agent_invoke.py) `invoke_agent_llm(engine, system_prompt, user_message)`. This is a single Bedrock turn with `tools=[]` — sub-agents in the lifecycle do **not** spawn nested tool-use loops. Tool execution (`create_project`, `build_and_verify_workflow`, `publish_project`, `deploy_to_orchestrator_v2`) happens directly inside the dedicated lifecycle stages.

The `skills` list on each agent class is metadata only and is currently not auto-loaded into `invoke_agent_llm`. Agents rely on their system prompts for behaviour; runtime tools live in the lifecycle stages.

## Output artefacts

Given `output_root` (defaults to current working directory) and a stamp like `20260419-101501-ab12cd34`:

```
<output_root>/
  docs/
    pdd/<stamp>.md
    sdd/<stamp>.md
    add/<stamp>.md
    tdd/<stamp>.md
    qa/<stamp>.md            # only when --no-deploy
  generated/automation/<stamp>/
    <ProjectName>/           # scaffolded UiPath project
      project.json (RPA) or *.flow (maestro)
      IMPLEMENTATION_PLAN.md
```

The result dict's `paths` key contains absolute paths to every artefact produced.

## Deploy branch

The `publish` and `deploy` stages call into [`uipath_claude/tools/deploy_tool.py`](../uipath_claude/tools/deploy_tool.py):

- RPA (`process`): `uip solution pack` -> `uip solution publish` -> `uip or processes create`.
- Maestro (`maestro`): `uip flow pack` -> `uip solution publish` -> `uip flow process create`.

Required environment for real deploys: `UIPATH_ORCHESTRATOR_URL`, `UIPATH_TENANT_NAME`, `UIPATH_ACCOUNT_NAME`, plus a valid `uip login` session (PAT or interactive). Tests check this via the `auth_required` fixture in [`tests/integration/conftest.py`](../tests/integration/conftest.py).

`publish_fn` and `deploy_fn` are exposed as parameters of `run_pdd_lifecycle` so integration tests can inject mocks.

## Failure semantics

- `_fail(stage, message)` returns `{"status": "failed", "failed_at": stage, "error": message, "stages": ..., "paths": ...}`.
- The CLI command formats this as `PDD lifecycle: FAILED at <stage>: <error>` followed by the per-stage status table and any artefact paths produced before the failure.
- Errors from agent tool wrappers that begin with `[ERROR]`, `[BLOCKED]`, or `[FAIL]` are also treated as failures (`_is_error_payload`).

## Related docs

- [SLASH_COMMANDS.md](SLASH_COMMANDS.md) - All in-chat slash commands, SDLC mapping, `UIPATH_CLAUDE_TOOL_PROFILE`.
- [USER_GUIDE.md](USER_GUIDE.md) - CLI usage, slash commands.
- [ARCHITECTURE.md](ARCHITECTURE.md) - Where `/pdd` fits in the broader runtime.
- [CURSOR_USER_GUIDE.md](CURSOR_USER_GUIDE.md) - MCP tool surface used inside the lifecycle.
- [SMOKE_TESTS.md](SMOKE_TESTS.md) - End-to-end scenarios.
