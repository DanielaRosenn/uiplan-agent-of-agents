# Orchestrator Deployment Runbook

Use this runbook when packaging, publishing, or deploying UiPath projects to
Orchestrator. It is the canonical repo guidance for assistant-driven deploy
instructions.

## Hard Safety Rules

- Do not deploy to Production from an AI-assistant session.
- Do not publish or deploy until a human explicitly confirms the target; record
  that explicit human confirmation in the handoff.
- Prefer a personal workspace for assistant-driven review. Use a named Dev
  folder only when the user explicitly asks for it.
- Always run the local gate before publish/deploy: restore, analyze, test when
  available, pack, then deploy.
- Never continue to pack or deploy when `analyze` reports errors.
- Treat warnings as a human decision: summarize them and ask before deploy.
- Do not run deploy, publish, invoke, or Orchestrator job commands while editing
  docs or tests for this repo.

## Production Handoff Evidence

Before any production push or deployment request, capture this evidence in the
handoff:

- Current branch and commit SHA.
- `git status --short` output showing a clean working tree.
- `python tools/check-versions.py` result.
- `python -m uipath_claude.skills.submodule_guard --strict` result.
- `python -m pytest -q` result for the root test suite.
- Studio API test result from `studio/api`: `uv run pytest tests -q`.
- Frontend gate result from `studio/web`: `npm run lint`, `npm test`, and
  `npm run build`.
- `gitleaks detect --config .gitleaks.toml` result.
- CLI versions: `uipcli --version`, `uip --version`, and `uipath --version`.
- Artifact-specific restore, analyze, test, and pack output for the production target.
- Human confirmation of the target tenant, folder, feed, and package version.

If any item is missing, the release is not ready for production promotion.

## Compatibility Preflight

Run this before creating a project, choosing packages, validating, packing, or
deploying. The goal is to choose the latest compatible versions, not the newest
versions blindly.

| Check | Required evidence | Blocking rule |
| --- | --- | --- |
| Project type | RPA/Coded Automation, coded agent, Solution, Maestro, Coded App, or legacy | Stop if the type is ambiguous. |
| Studio | Studio version and target framework | Modern projects use Windows/.NET 8; legacy requires explicit handling. |
| CLI | `uipcli`, `uip`, and/or `uipath` version, depending on project type | CLI major/minor must match the Studio/Orchestrator support envelope. |
| Packages | Activity/NuGet/Python package versions selected | Prefer latest compatible with Studio/project target; stop before behavior-changing upgrades. |
| Orchestrator | Tenant/folder/feed and Automation Cloud capability where relevant | Never use Production; Solutions require Automation Cloud support. |
| Maestro/Solutions | Solution feature, bindings, and activation requirements | Treat Maestro/Coded Apps as Solution deploys, not standalone RPA deploys. |

Read-only probes that are safe in a local preflight include version/help
commands such as `uipcli --version`, `uip --version`, `uipath --version`, and
`--help` for the specific command family. In Cursor, use
`uipath_workflow_environment_probe` before choosing activity packages or
creating/editing `project.json`.

If there is no live API or local metadata source for a package decision, record
the decision rule and ask the user to confirm the version.

## Project-Type Decision

| Project | Primary deploy path | Notes |
| --- | --- | --- |
| RPA / Coded Automation | `uipcli package ...` | Use for `project.json` with XAML/C# workflows. |
| Coded Agent | `uipath pack` then `uipath publish -w` | Use personal workspace by default. |
| Solution | `uipcli solution ...` | Automation Cloud only; explicit version required. |
| Maestro / Coded App | Solution deploy | Publish/activate through Solution flow and bindings. |
| Legacy RPA | Legacy CLI / human approval | Do not convert silently to Modern. |

## RPA / Coded Automation

```powershell
uipcli package restore project.json
uipcli package analyze project.json --resultPath analyze.json
# Inspect analyze.json. If severity == Error, stop.
uipcli test run Tests\project.json <orch-url> <tenant> `
  -A <org> -I <app-id> -S <secret> `
  --testset "Smoke" --result_path test-results.xml
uipcli package pack project.json -o output --autoVersion
```

Deploy only after explicit approval:

```powershell
uipcli package deploy output\*.nupkg <orch-url> <tenant> `
  -A <org> -I <app-id> -S <secret> `
  --orchestratorFolder "<personal-or-dev-folder>" `
  --createProcess
```

Use a personal workspace or named Dev folder. Do not use Production.

## Coded Agents

```powershell
uv run pytest
uv run uipath run agent '{"input":"sample"}'
uv run uipath pack --nolock
```

Publish only after explicit approval:

```powershell
uv run uipath publish -w
```

The returned process configuration link is part of the handoff evidence. Configure
runtime environment variables in Orchestrator; do not assume local `.env` values
were packed.

Smoke test only with safe test input:

```powershell
uv run uipath invoke agent '{"input":"smoke"}'
```

## Solutions, Maestro, And Coded Apps

Solutions are Automation Cloud only through CLI. Maestro and Coded Apps deploy as
part of a Solution-style lifecycle.

```powershell
uipcli solution restore <solution-path>
uipcli solution analyze <solution-path> --resultPath analyze.json
# Inspect analyze.json. If severity == Error, stop.
uipcli solution pack <solution-path> -v <version> -o output
uipcli solution upload-package output\*.uipx <orch-url> `
  -A <org> -I <app-id> -S <secret>
```

If deployment needs setup, download and fill bindings before activation:

```powershell
uipcli solution download-config <solution-name> <version> <orch-url> `
  -A <org> -I <app-id> -S <secret> `
  -o bindings
```

Activate only after explicit approval:

```powershell
uipcli solution deploy-activate <solution-name> <version> <orch-url> `
  -A <org> -I <app-id> -S <secret> `
  --targetFolder "<personal-or-dev-folder>" `
  --bindings bindings/dev.json
```

## Smoke Test And Handoff Evidence

Report these items after any approved deploy:

- Project type and package/process/solution name.
- Version string and package path.
- Target tenant and folder.
- Analyzer result summary and warnings.
- Test/eval result summary.
- Process configuration link, deployment ID, or package upload ID.
- Smoke job/run ID and final state, when a smoke run was approved.
- Any unresolved bindings, missing runtime/machine setup, or follow-up actions.

## Troubleshooting

| Symptom | Likely cause | Action |
| --- | --- | --- |
| `401` / unauthorized | External App credentials or scopes missing | Re-check app ID/secret and CLI scope defaults. |
| Folder not found | Wrong folder path or modern folder mismatch | List folders and ask the user to confirm the target. |
| Package already exists | Version already uploaded | Bump version; do not delete packages from shared feeds. |
| No suitable runtime | Machine template/runtime not assigned | Ask the user to configure runtimes in the target folder. |
| `Needs setup to activate` | Solution bindings unresolved | Download config, fill bindings, redeploy/activate. |
| App activation failed | Coded App activation step incomplete | Open activation link and complete app setup. |
| Agent env vars missing | Runtime env not configured in Orchestrator | Use the process configuration link returned by publish. |

## References

- [UiPath CLI reference](uipath-cli.md)
- [UiPath workflows](uipath-workflows.md)
- [PDD lifecycle](PDD_LIFECYCLE.md)
- [Cursor guide](CURSOR_USER_GUIDE.md)
- [Smoke tests](SMOKE_TESTS.md)
