# Activity and Runtime Evidence Reference

This document provides the canonical contract for grounding activity choices, provisioning Orchestrator resources, proving local Studio validation, recording tenant runtime evidence, and capturing UAT/test-case proof in UiPlan bundles.

Use this reference when authoring `plan.md` and `tasks.md` to ensure every activity, resource, deployment, and test claim is backed by verifiable evidence.

## Activity selection grounding

Every non-trivial workflow activity used in a UiPath project must be grounded in authoritative documentation before implementation. This prevents placeholder-only workflows and ensures the generated project uses real, current activities with correct properties.

### Required grounding steps

1. **Identify the activity need**: based on the business process step (e.g., "read email messages", "add queue item", "write Excel range").

2. **Look up the activity**: use `uipath_doc_find_activity` or `uipath_doc_get_activity` MCP tools, or consult the UiPath library via `uipath_library_search` for activity guidance.

3. **Record activity evidence** in `plan.md` Activity Inventory and `tasks.md` activity checklist rows:
   - **Package ID**: the NuGet package name (e.g., `UiPath.Mail.Activities`).
   - **Activity name**: the display name (e.g., `Get Mail Messages`).
   - **Version or range**: the package version resolved from activity docs or project scaffold dependencies.
   - **Required scope**: whether the activity needs a particular parent container (e.g., `Use Outlook 365`, `Try Catch`).
   - **Required inputs/outputs**: key properties that must be configured (e.g., `MailFolder`, `Top`, `Messages`).
   - **Default XAML or Studio-generated evidence**: either the output from `uip rpa get-default-activity-xaml` or a snippet from a Studio-generated scaffold showing the activity tag and required properties.

4. **Verify the activity resolves**: after scaffolding or editing the workflow, run:
   ```powershell
   uip rpa get-errors --file-path "<workflow>.xaml" --project-dir "<project-root>" --output json
   ```
   and confirm no `UnresolvedActivity` errors appear for the activity.

### Activity evidence row format

In `tasks.md`, include an activity checklist table for each workflow artifact:

| Activity | Package | Version | Required Scope | Required Props | Default XAML / Evidence |
| --- | --- | --- | --- | --- | --- |
| `Get Mail Messages` | `UiPath.Mail.Activities` | `1.23.11` | `Use Outlook 365` | `MailFolder`, `Top`, `Messages` | `uip rpa get-default-activity-xaml` output or Studio-generated snippet |
| `Add Queue Item` | `UiPath.System.Activities` | (scaffold version) | None | `QueueName`, `ItemInformation` | Default XAML from activity doc |

### Forbidden practices

- **No hand-authored placeholder XAML**: do not manually write `<LogMessage>` or `<Assign>` tags and call them complete unless the task explicitly says scaffold-only and a production wiring task remains open.
- **No activities without doc lookup**: every activity beyond basic `Sequence`, `Flowchart`, `If`, `Assign`, `Log Message`, and `Try Catch` must be grounded in `uipath_doc_get_activity` or equivalent library/doc evidence.
- **No old dependencies copied from failed demos**: always use current package versions from the scaffold or activity doc lookup, not pinned old versions from a previous broken project.

## Orchestrator resource lifecycle

Orchestrator resources (queues, assets, folders, connections, bindings) must be explicitly declared, provisioned, verified, and bound before they can be used in deployed processes. Local-only proof is not enough for resources that require tenant-level existence.

### Resource lifecycle steps

1. **Declare**: list the resource in `plan.md` Bindings and Environment inventory with name, type, target folder, secret boundary, and provisioning command family.

2. **Provision**: before deploying a process that uses the resource, create it in the target Orchestrator folder:
   - **Queues**: `uip or queues create --name "<queue-name>" --folder-id "<folder-id>" --description "..." --output json`
   - **Assets** (non-secret): `uip or assets create --name "<asset-name>" --type Text --value "<value>" --folder-id "<folder-id>" --output json`
   - **Assets** (secret): use `[HANDOFF:Secrets]` and document the expected asset name, type, and scope; never commit secret values.
   - **Folders**: usually pre-existing; if a new folder is required and approved, use `uip or folders create --name "<folder-name>" --parent-id "<parent-folder-id>" --output json`.
   - **Connections**: managed via Integration Service or Studio Web connectors; record the connection name and required OAuth/credential handoff if not available.

3. **Verify existence**: after provisioning, confirm the resource exists:
   - **Queues**: `uip or queues list --folder-id "<folder-id>" --filter "name eq '<queue-name>'" --output json`
   - **Assets**: `uip or assets list --folder-id "<folder-id>" --filter "name eq '<asset-name>'" --output json`
   - **Folders**: `uip or folders get --id "<folder-id>" --output json`

4. **Bind**: ensure the deployed process or agent references the resource by name in code/config, and that bindings (for Solutions) or environment-specific config files map the resource correctly per environment (Dev, Test, Prod).

5. **Record evidence**: in `tasks.md`, include the provisioning command, existence verification output path, and the folder/environment context. Example:
   ```
   - Provisioned queue `InvoiceQueue` in folder `Shared/Test` via `uip or queues create ...`; verified existence with `uip or queues list ...`; evidence in `out/queue-create.json` and `out/queue-verify.json`.
   ```

### Resource evidence row format

In `tasks.md`, include a resource provisioning table for each Orchestrator-dependent task:

| Resource | Type | Target Folder | Provisioning Command | Verification Command | Evidence Path | Secret Boundary |
| --- | --- | --- | --- | --- | --- | --- |
| `InvoiceQueue` | Queue | `Shared/Test` | `uip or queues create ...` | `uip or queues list ...` | `out/queue-create.json` | None |
| `LLMApiKey` | Asset (text secret) | `Shared/Test` | `[HANDOFF:Secrets]` | `uip or assets list ...` | `out/asset-verify.json` | Credential |

### Forbidden practices

- **No resource names in code without provisioning proof**: do not deploy a process that references a queue or asset unless the resource provisioning and existence verification evidence is recorded in `tasks.md`.
- **No silent assumption of pre-existing resources**: always verify resource existence explicitly before deployment smoke tests; if the resource does not exist and cannot be created (permissions, policy), record a blocker class and stop.
- **No Production provisioning from AI sessions**: all resource creation commands must target non-Production folders (personal workspace, Dev, Test); Production resource changes require human approval and are marked `[HANDOFF:OrchestratorDeploy]`.

## Local Studio evidence

Before deploying a UiPath project to Orchestrator or publishing a package, prove the project is valid locally using Studio and CLI validation tools. This catches syntax errors, missing dependencies, unresolved activities, and analyzer rule violations before tenant-level failures.

### Required local validation commands

1. **Studio designer errors** (requires Studio and `uip rpa` CLI):
   ```powershell
   uip rpa get-errors --file-path "<workflow>.xaml" --project-dir "<project-root>" --output json
   ```
   Fail the task if `UnresolvedActivity`, syntax errors, or missing references appear in the output.

2. **Studio build** (requires Studio and `uip rpa` CLI):
   ```powershell
   uip rpa build "<project-root>" --output json
   ```
   Fail the task if the build does not succeed.

3. **Package analyzer** (requires `uipcli`):
   ```powershell
   uipcli package analyze "<project-root>/project.json" --resultPath "out/<name>-analyze.json"
   ```
   Parse the JSON output and count errors vs warnings. Errors are blocking; warnings require explicit human sign-off to proceed.

4. **Local smoke run** (optional, when safe):
   If the workflow can run locally without destructive side effects (e.g., writes to a safe local folder, reads fixture data), include a local run command and record the output:
   ```powershell
   uip rpa run "<project-root>" --input-path "fixtures/input.json" --output json
   ```
   Capture the exit code, output path, and observed log markers.

### Local evidence recording

In `tasks.md`, include a local validation evidence block for each project or package build task:

```markdown
**Local validation evidence**:
- `uip rpa get-errors` output: `out/get-errors.json` (0 errors)
- `uip rpa build` output: `out/build.json` (success)
- `uipcli package analyze` output: `out/analyze.json` (0 errors, 2 warnings accepted)
- Local smoke run (optional): `out/local-run.json` (exit 0, observed log marker "CorrelationId: ...")
```

### Forbidden practices

- **No pack/deploy without analyzer pass**: do not proceed to `uipcli package pack` or `uipcli package deploy` if `uipcli package analyze` returns errors.
- **No completion claims from analyze/pack alone**: local validation (get-errors, build, analyze) is necessary but not sufficient for deployment tasks; tenant runtime evidence is required for any task that includes deploy/publish/activate/job run language.
- **No skipping Studio validation when Studio is available**: if Studio and `uip rpa` CLI are present on the machine, always run `uip rpa get-errors` and `uip rpa build` before claiming a workflow is complete. If Studio is unavailable, record a blocker class and the closest safe validation evidence (analyzer only).

## Tenant evidence

Tenant evidence proves that a deployed package, process, or agent ran successfully in an Orchestrator folder and produced the expected runtime behavior. This is required for any deployment or smoke task in `tasks.md`.

### Required tenant evidence components

1. **Target folder**: the Orchestrator folder where the package/process/agent is deployed (must be non-Production: personal workspace, Dev, or Test).

2. **Package/process version**: the deployed package version string and process key, captured from deploy command output or Orchestrator UI/API.

3. **Job or agent invocation**:
   - For RPA/XAML processes: `uip or jobs start --process-key "<process-key>" --input-arguments "<safe-input-json>" --output json` and capture the returned job ID.
   - For coded agents: `uipath invoke --name "<agent-name>" --input "<safe-input-json>" --output json` or equivalent tenant invocation, and capture the agent run ID or job ID.

4. **Final state**: after the job/invocation completes, record the final state (Successful, Faulted, Stopped) from Orchestrator.

5. **Logs**: retrieve and inspect the job logs to confirm expected phase markers, correlation IDs, and business logic outputs:
   ```powershell
   uip or jobs logs --job-id "<job-id>" --output json
   ```
   Parse the log output and assert key log messages exist (e.g., "Phase: ReadMailbox", "CorrelationId: ...", "ProcessedInvoices: 3").

6. **Queue item or asset proof** (when applicable):
   - If the process adds queue items, query the queue and confirm items exist:
     ```powershell
     uip or queue-items list --queue-name "<queue-name>" --folder-id "<folder-id>" --output json
     ```
   - If the process updates an asset, retrieve the asset value and confirm it changed.

### Tenant evidence recording

In `tasks.md`, include a tenant runtime evidence block for each deployment/smoke task:

```markdown
**Tenant runtime evidence**:
- Deployed to folder: `Shared/Test` (folder ID: `<folder-id>`)
- Package version: `InvoiceProcessor` `1.0.5` (process key: `<process-key>`)
- Job started: `uip or jobs start ...` (job ID: `<job-id>`)
- Job final state: `Successful`
- Job logs: `uip or jobs logs ...` output in `out/job-logs.json` (observed markers: "Phase: Extract", "CorrelationId: abc123", "InvoicesProcessed: 3")
- Queue items: `uip or queue-items list ...` output in `out/queue-items.json` (3 items in `InvoiceQueue` with status `New`)
```

### Blocker class for unavailable tenant evidence

If tenant credentials, folder permissions, or runtime environment are unavailable, do not silently skip tenant evidence. Instead, record a structured blocker:

```json
{
  "blocker_class": "missing_tenant_auth_or_folder_permission",
  "attempted_commands": ["uip login", "uip or folders list", "uipcli package deploy"],
  "target_folder": "Shared/Test",
  "safe_local_evidence": ["uip rpa get-errors", "uip rpa build", "uipcli package analyze", "local smoke run"]
}
```

Write this blocker to `out/tenant-blocker.json` and reference it in the task evidence. Mark the task `local-ready` and keep the deploy/smoke task open with an explicit handoff.

### Forbidden practices

- **No completion from local pack alone**: if a task includes "deploy", "publish", "smoke", "job run", or "invoke" language, it is not complete until tenant runtime evidence (or a structured blocker) is recorded.
- **No silent "would deploy" wording**: do not write "would deploy to Test folder" or "ready to publish" without attempting the actual deploy command and recording the result or blocker.
- **No Production deployment from AI sessions**: all tenant mutation commands (deploy, publish, activate, job start, resource create) must target non-Production folders. Production changes require explicit human approval and are out of scope for automated implementation sessions.

## UAT/test evidence

UAT (User Acceptance Testing) and automated test-case evidence prove that the built automation meets acceptance criteria beyond static analyzer checks. This section is required for every production-bound user story.

### Test artifact types

1. **UiPath Testing Activities** (for RPA/XAML projects):
   - Create test workflows under `Tests/` using `UiPath.Testing.Activities` package.
   - Use `Test Case`, `Given`, `When`, `Then`, `Verify Expression`, and `Run Test Case` activities.
   - Run tests via `uipcli test run -a <projectKey> <projectPath>` and capture JUnit/NUnit XML or JSON output.

2. **pytest / eval** (for coded agents):
   - Write pytest test modules under `tests/` covering happy-path and failure-path scenarios.
   - Run `uv run pytest tests/test_<agent>.py -q --tb=short` and capture the result.
   - For agents with evaluation sets, run `uipath eval --eval-set <set> --num-workers 1 --output-file out/eval.json` and assert evaluation scores meet acceptance criteria.

3. **Manual Studio UAT** (when automated tests are not feasible):
   - Document a manual UAT scenario in `tasks.md` with step-by-step instructions, expected outcomes, and evidence capture (screenshots, log files, Studio session recording).
   - Execute the UAT scenario and record the results in a structured format (e.g., `out/uat-manual-results.md` or `out/uat-session-log.json`).

### Required UAT evidence components

1. **Test artifact path**: the file or folder containing the test workflows, pytest modules, or UAT documentation.

2. **Test execution command**: the exact command used to run the tests:
   - `uipcli test run -a <projectKey> <projectPath>` for RPA tests.
   - `uv run pytest <test-module> -q` for pytest.
   - `uipath eval ...` for agent evaluations.
   - Manual UAT: documented steps and evidence capture process.

3. **Test results**: the output path and parsed results:
   - For `uipcli test run`: JUnit XML or JSON with pass/fail counts and failure messages.
   - For pytest: console output with test summary and any assertion errors.
   - For eval: evaluation scores (accuracy, F1, latency) and comparison to thresholds.
   - For manual UAT: completed UAT checklist with observed outcomes and attached evidence files.

4. **Acceptance criteria mapping**: a table or list showing which `spec.md` acceptance criteria bullets are covered by which test cases.

### UAT evidence row format

In `tasks.md`, include a UAT/test evidence table for each production-bound user story:

| Scenario | Acceptance Criteria | Test Artifact | Execution Command | Result Path | Pass Criteria |
| --- | --- | --- | --- | --- | --- |
| Happy path: valid invoice | AC1, AC2 from spec | `Tests/ValidInvoice.xaml` | `uipcli test run -a <key> <path>` | `out/test-results.xml` | All tests pass, log shows "InvoiceValidated: true" |
| Failure path: invalid date | AC3 from spec | `Tests/InvalidDate.xaml` | `uipcli test run -a <key> <path>` | `out/test-results.xml` | Test passes, log shows "ValidationError: invalid date" |

### Forbidden practices

- **No UAT claims from analyzer/pack alone**: passing analyzer checks or producing a `.nupkg` is not UAT evidence. UAT requires actual test execution (automated or manual) and comparison to acceptance criteria.
- **No "would test" or "should test" wording**: if a task includes UAT/test language, it must produce a real test artifact and execution evidence, or record a structured blocker explaining why testing is not possible (e.g., missing test environment, unsafe destructive actions).
- **No placeholder test workflows**: a test workflow that only contains `LogMessage "Test placeholder"` is not UAT evidence. Test workflows must contain real `Verify Expression`, `Given`, `When`, `Then` activities that assert expected behavior against actual outputs.

## Evidence ledger and traceability

For every implementation phase or user story, maintain an **evidence ledger** in `tasks.md` that summarizes all grounding, validation, and runtime proof. This ledger is the single source of truth for sign-off and should be reviewable by BA, SA, Dev, and QA personas.

### Evidence ledger format

```markdown
## Evidence ledger: <User Story ID or Phase>

| Evidence Type | Artifact / Command | Output Path | Status | Notes |
| --- | --- | --- | --- | --- |
| Activity grounding | `uipath_doc_get_activity` for `Get Mail Messages` | `out/activity-doc.json` | ✓ | Package `UiPath.Mail.Activities` v1.23.11 |
| Activity grounding | `uipath_doc_get_activity` for `Add Queue Item` | `out/activity-doc-queue.json` | ✓ | Package `UiPath.System.Activities` (scaffold version) |
| Resource provisioning | `uip or queues create --name InvoiceQueue ...` | `out/queue-create.json` | ✓ | Queue exists in `Shared/Test` folder |
| Resource verification | `uip or queues list --filter "name eq 'InvoiceQueue'"` | `out/queue-verify.json` | ✓ | Queue ID: `<queue-id>` |
| Local validation | `uip rpa get-errors --file-path Main.xaml ...` | `out/get-errors.json` | ✓ | 0 errors |
| Local validation | `uip rpa build <projectRoot>` | `out/build.json` | ✓ | Build succeeded |
| Local validation | `uipcli package analyze project.json ...` | `out/analyze.json` | ✓ | 0 errors, 2 warnings (accepted) |
| Tenant deployment | `uipcli package deploy <package> --folder Shared/Test` | `out/deploy.json` | ✓ | Process key: `<process-key>` |
| Tenant smoke | `uip or jobs start --process-key <key> ...` | `out/job-start.json` | ✓ | Job ID: `<job-id>` |
| Tenant smoke | `uip or jobs logs --job-id <job-id>` | `out/job-logs.json` | ✓ | Observed: "Phase: Extract", "CorrelationId: abc123" |
| UAT | `uipcli test run -a <key> Tests/ValidInvoice.xaml` | `out/test-results.xml` | ✓ | All tests pass |
| UAT | `uipcli test run -a <key> Tests/InvalidDate.xaml` | `out/test-results.xml` | ✓ | Test passes, validation error logged |
```

### Traceability to spec acceptance criteria

For each user story, include a mapping table that shows which evidence rows prove which acceptance criteria:

| Acceptance Criteria (from spec.md) | Evidence Rows | Status |
| --- | --- | --- |
| AC1: System shall extract invoice number, date, and amount | Activity grounding, Local validation, Tenant smoke, UAT (valid invoice) | ✓ |
| AC2: System shall validate invoice date is not in the future | Activity grounding, Local validation, UAT (invalid date) | ✓ |
| AC3: System shall log a correlation ID for each invoice | Tenant smoke (job logs) | ✓ |

This traceability matrix is required for BA/QA sign-off and should be reviewable without diving into individual tool outputs.

## Summary

This reference codifies the four pillars of reliable UiPlan implementation:

1. **Activity grounding**: every non-trivial activity must be looked up via `uipath_doc_get_activity` or library search, and activity evidence rows must include package, version, scope, properties, and default XAML.

2. **Orchestrator resource lifecycle**: every queue, asset, folder, or connection must be explicitly declared, provisioned, verified, and bound, with evidence recorded in `tasks.md`.

3. **Local Studio evidence**: every project must pass `uip rpa get-errors`, `uip rpa build`, and `uipcli package analyze` before deployment, with structured output paths.

4. **Tenant evidence**: every deployment/smoke task must record target folder, package version, job/invocation ID, final state, logs, and queue/asset proof—or a structured blocker explaining why tenant evidence is unavailable.

5. **UAT/test evidence**: every production-bound user story must include automated test workflows (UiPath Testing Activities or pytest) or documented manual UAT, with test execution results and acceptance criteria mapping.

Use this reference when authoring and reviewing UiPlan bundles to ensure every claim is backed by verifiable, repeatable evidence.
