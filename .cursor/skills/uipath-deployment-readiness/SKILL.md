---
name: uipath-deployment-readiness
description: UiPath deployment readiness and controlled non-Production deployment flow. Use when asked to deploy, publish, activate, smoke test, or hand off Solution/RPA/agent/Flow deployments.
---

# UiPath Deployment Readiness

Use this skill to prevent "local pack passed, deploy unknown" gaps.

## When to use

Trigger on requests like:

- deploy to Orchestrator
- publish package / solution
- solution upload-package / deploy / deploy-activate
- run smoke job / verify in Dev folder
- handoff for release / activation / bindings

## Hard gates

- Never deploy to Production from an assistant session.
- Require explicit user approval before any tenant mutation.
- Run local build gates first: restore -> analyze -> test (when available) -> pack.
- Stop if analyze has errors.
- If credentials/tenant target are missing, produce a blocker handoff with exact missing inputs.

## Deployment modes

1. **Read-only research**
   - Use `--help`, `--version`, runbook/docs, and library lookups.
   - No tenant calls.

2. **Local-only readiness**
   - Restore, analyze, test, pack.
   - Gather package output and evidence logs.
   - No upload/deploy/job.

3. **Approved non-Production deploy**
   - Requires explicit target folder and credentials.
   - Run upload/deploy/deploy-activate flow.
   - Run safe smoke.
   - Capture deployment and job evidence.

## Required preflight checklist

- Project type: RPA, Solution, coded agent, Flow/Maestro.
- CLI versions captured (`uipcli`, `uip`, `uipath` where relevant).
- On Windows, set UTF-8 console mode before Python `uipath` auth/run commands:
  `$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; chcp 65001 | Out-Null`.
- Target: Automation Cloud URL, tenant, folder (personal workspace or Dev only).
- Auth method confirmed (external app preferred).
- Binding source confirmed (`bindings/dev.json` or `download-config` output).
- Evidence output folder prepared under `out/`.

### Tenant runtime prerequisite (coded agents only)

Coded agents need a Cloud-Serverless runtime template on the target folder.

- Personal Workspace folders inherit a default Cloud-Serverless template; Shared folders DO NOT, and require a one-time tenant-admin configuration step.
- Pre-flight: confirm the target Shared folder has a Cloud-Serverless template configured (Orchestrator UI -> Folder -> Templates) before running `uipath publish` against it. If the operator cannot confirm this, fall back to publishing in the Personal Workspace and route the Shared-folder activation to a tenant admin.
- Cross-link: see [`docs/uipath-workflows.md#cloud-serverless-shared-folder-prereq`](../../../docs/uipath-workflows.md#cloud-serverless-shared-folder-prereq) for the operator UI steps and the Personal Workspace fall-back.

## Authentication preflight

Python `uipath auth` can crash on Windows with `UnicodeEncodeError` from the
Rich spinner when the terminal uses `cp1252`. Always run auth through a UTF-8
shell prelude:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
chcp 65001 | Out-Null
uipath auth --tenant <tenant>
```

Record the command, exit code, and whether authentication succeeded.

Node `uip` authentication is separate from Python `uipath auth`. For `uip`
commands, use:

```powershell
uip login -t <tenant>
uip login status --output json
```

If Node fails with `self-signed certificate in certificate chain`, prefer a real
corporate CA file:

```powershell
$env:NODE_EXTRA_CA_CERTS='C:\path\to\corporate-root-ca.pem'
uip login -t <tenant>
```

Only as a temporary lab fallback, scope `NODE_TLS_REJECT_UNAUTHORIZED=0` to a
single command. It disables TLS verification. Never persist or commit
`uip login --output json` output because it includes access and refresh tokens.

## Command skeletons (authoritative order)

### Solution

```powershell
uipcli solution restore <solution_path>
uipcli solution analyze <workspace_or_solution_path> --resultPath <out/analyze.json>
uipcli solution pack <solution_path> --version <version> -o <out/solution-pack>
uipcli solution upload-package <solution_package_zip> -U <url> -T <tenant> -A <org> -I <appId> -S <secret>
uipcli solution deploy-activate <deployment_name> -v <version> -U <url> -T <tenant> -A <org> -I <appId> -S <secret> -o <folder>
```

Interactive `uip` alternative:

```powershell
uip login -t <tenant>
uip solution publish <out/solution-pack/solution_version.zip> --tenant <tenant> --output json
uip solution deploy run --tenant <tenant> --name <deployment_name> --package-name <package_name> --package-version <version> --folder-name <folder_name> --folder-path <parent_folder> --timeout 360 --output json
uip solution deploy status <pipeline_deployment_id> --tenant <tenant> --output json
uip or processes list --tenant <tenant> --folder-path <parent_folder>/<folder_name> --output json
uip or jobs start <process_guid> --tenant <tenant> --folder-path <parent_folder>/<folder_name> --wait-for-completion --timeout 180 --output json
uip or jobs logs <job_guid> --tenant <tenant> --level Error --output json
```

When deploy reports setup gaps:

```powershell
uipcli solution download-config <deployment_or_package_name> -v <version> -U <url> -T <tenant> -A <org> -I <appId> -S <secret> -d <output-folder>
```

### RPA package

```powershell
uipcli package restore project.json
uipcli package analyze project.json --resultPath <out/analyze.json>
uipcli package pack project.json -o <out> --autoVersion
uipcli package deploy <out/*.nupkg> <url> <tenant> -A <org> -I <appId> -S <secret> --orchestratorFolder <folder> --createProcess
```

### Coded agent

```powershell
uv run pytest
uv run uipath pack --nolock
uv run uipath publish -w
uipath invoke <entrypoint> -f <safe-input.json>
```

After invoking a published agent, read the tenant job state and logs:

```powershell
uip or jobs get <job_guid> --tenant <tenant> --output json
uip or jobs logs <job_guid> --tenant <tenant> --output json
```

## Flow / Maestro rule

If Solution pack logs `No tool results` for Flow/Maestro projects:

- Do not claim deployability from local pack alone.
- Mark deployment as partial.
- Route to Studio Web / Automation Cloud solution publish path and document required human verification.
- For `uip flow pack`, ensure the `.flow` filename matches the project name
  convention expected by the packer, for example project `ZipEmail.HumanReview`
  expects `ZipEmail_HumanReview.flow`.

## Runtime resource smoke rule

Deployment success is not the same as runtime readiness. After deployment:

- list processes in the deployed folder;
- provision required non-secret assets and queues with `uip resource`, scoped to
  the same folder path used by the deployed processes;
- leave credential/secret assets as explicit `[HANDOFF:Secrets]` items unless
  the user provides values through an approved secret channel;
- start a safe smoke job;
- fetch job logs, not only the final job state;
- for coded agents, verify the deployed package version and dependency install
  lines in the logs where available;
- if the job faults on missing assets, queues, or connections, classify the
  blocker as `runtime_resource_missing`.

Use this default resource provisioning path:

```powershell
uip resource assets list --tenant <tenant> --folder-path <folder> --output json
uip resource assets create "<asset_name>" "<value>" --tenant <tenant> --folder-path <folder> --type Text --description "<description>" --output json
uip resource queues list --tenant <tenant> --folder-path <folder> --output json
uip resource queues create "<queue_name>" --tenant <tenant> --folder-path <folder> --max-retries 3 --auto-retry --output json
uip resource queue-items list --tenant <tenant> --folder-path <folder> --queue-definition-key <queue_key> --output json
```

Do not rely on `uipcli asset deploy` as the primary path for assistant-driven
runtime resource setup. If it authenticates but fails with a tool error, record
the exact CLI error as `asset_cli_failure`, switch to `uip resource`, and keep
smoke open until a job proves the assets/queues are usable.

## Evidence ledger (required)

For every gate and deploy step, record:

- exact command
- working directory
- exit code
- target tenant/folder (if tenant mutation)
- package/deployment identifier
- output log/result path
- observed outcome
- blocker class (if incomplete)

Use this format in runbooks and handoffs. Do not mark deployment complete without tenant-side evidence.

## References

- [solution-deployment-checklist.md](solution-deployment-checklist.md)
- [docs/ORCHESTRATOR_DEPLOYMENT.md](../../../docs/ORCHESTRATOR_DEPLOYMENT.md)
- [docs/uipath-cli.md](../../../docs/uipath-cli.md)
