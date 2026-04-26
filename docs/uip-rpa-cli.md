# UiPath `uip rpa` CLI Reference

This page tracks the Studio IPC CLI surface used by the `uipath-rpa` skill.

Source of truth: `skills/uipath-rpa/references/cli-reference.md` at approved
skills commit `bae274e488043d4df505ffe6ac4d344748ee9114`.

`uip rpa` communicates with UiPath Studio over named pipes. It is for local
Studio-backed project creation, validation, package/activity discovery,
debugging, and workflow execution. Use `uipcli` for CI/CD packaging and
Orchestrator deployment.

> Installation is automatic through the session hook. Do not manually install
> `uip` inside normal assistant flows.

## Discovery

The CLI is self-documenting:

```bash
uip --help
uip rpa --help
uip rpa get-errors --help
```

When invoking commands programmatically, always pass `--output json`.

## Global Options

| Option | Purpose | Default |
| --- | --- | --- |
| `--project-dir <path>` | Project directory containing `project.json` | Current working directory |
| `--studio-dir <path>` | Studio install directory | Auto-detected |
| `--timeout <seconds>` | Studio resolution timeout | `300` |
| `--verbose` | Debug logging | Off |
| `--output <format>` | `json`, `table`, `yaml`, or `plain` | `table` |

Studio auto-detection checks `UIPATH_STUDIO_DIR`, standard install paths such
as `C:\Program Files\UiPath\Studio`, then local Studio dev build outputs.

If a command reports that Studio does not have interop support or requires
Studio 26.2+, stop and ask the user to update Studio.

## Studio Management

| Command | Purpose |
| --- | --- |
| `uip rpa list-instances --output json` | List running Studio instances and IPC status. |
| `uip rpa start-studio --project-dir "<PROJECT_DIR>" --output json` | Ensure a Studio instance is available. |
| `uip rpa open-project --project-dir "<PROJECT_DIR>" --output json` | Open a project in Studio. |
| `uip rpa close-project --project-dir "<PROJECT_DIR>" --output json` | Close the current project in Studio. |

`start-studio` first tries to reuse a matching Studio instance, then an idle
instance, then starts a new one.

## Project Lifecycle

Create a project from a Studio template:

```bash
uip rpa create-project --name "<NAME>" --location "<PARENT_DIR>" --output json
```

Common options:

| Option | Purpose |
| --- | --- |
| `--template-id <id>` | Built-in template such as `BlankTemplate`, `LibraryProcessTemplate`, or `TestAutomationProjectTemplate`. |
| `--description <text>` | Project description. |
| `--expression-language <lang>` | `CSharp` or `VisualBasic`. Prefer `CSharp`. |
| `--target-framework <framework>` | `Windows`, `Portable`, or `Legacy`. Prefer modern `Windows`. |

The upstream reference also documents template search:

```bash
uip rpa search-templates --query "<SEARCH_TERM>" --output json
uip rpa search-templates --limit 10 --include-prerelease --output json
```

Use returned `packageId` and `version` values with template-backed project
creation.

## Validation And Execution

| Command | Purpose |
| --- | --- |
| `uip rpa run-file --file-path "<FILE>" --project-dir "<PROJECT_DIR>" --output json` | Run a workflow file. |
| `uip rpa run-file --file-path "<FILE>" --project-dir "<PROJECT_DIR>" --command StartDebugging --output json` | Debug a workflow and preserve UI state on error. |
| `uip rpa get-errors --project-dir "<PROJECT_DIR>" --output json` | Validate the whole project. |
| `uip rpa get-errors --file-path "<FILE>" --project-dir "<PROJECT_DIR>" --output json` | Validate a specific file. |
| `uip rpa build "<PROJECT_DIR>" --log-level Warn --output json` | Compile the project and catch expression/JIT failures. |

`run-file` returns `Data.runResult` as a JSON string. Parse that string to
inspect `Output` and `HasErrors`.

Use `StartDebugging` for UI automation workflows so the target app remains
available for selector repair after a failure.

`get-errors` has `--skip-validation` for cached results. Use it only when stale
validation is acceptable.

`build` is the required compilability check when no smoke test is safe to run.
It catches failures that static validation may miss.

## Package And Activity Discovery

Install or update NuGet packages:

```bash
uip rpa install-or-update-packages --packages '[{"id":"UiPath.Excel.Activities"}]' --project-dir "<PROJECT_DIR>" --output json
```

Omit package versions unless there is a known compatibility constraint.

Query available versions:

```bash
uip rpa get-versions --package-id UiPath.Excel.Activities --output json
uip rpa get-versions --package-id UiPath.Excel.Activities --include-prerelease --output json
```

Search activities and retrieve activity XAML:

```bash
uip rpa find-activities --query "<KEYWORD>" --output json
uip rpa find-activities --query "<KEYWORD>" --tags "<TAGS>" --limit 20 --output json
uip rpa get-default-activity-xaml --activity-class-name "<FULLY_QUALIFIED_CLASS>" --output json
uip rpa get-default-activity-xaml --activity-type-id "<TYPE_ID>" --connection-id "<CONNECTION_ID>" --output json
```

Installed package docs are generated under
`{projectRoot}/.local/docs/packages/{PackageId}/`:

| File | Use |
| --- | --- |
| `activities/{ActivityName}.md` | Activity-level docs when package and activity are known. |
| `coded/coded-api.md` | Coded workflow service API signatures and examples. |
| `overview.md` | Package overview. |

## Data Fabric Entities

List available and installed entities:

```bash
uip rpa list-data-fabric-entities --project-dir "<PROJECT_DIR>" --output json
uip rpa list-data-fabric-entities --service-document "<PATH>" --project-dir "<PROJECT_DIR>" --output json
```

Install, update, or remove entity bindings:

```bash
uip rpa install-data-fabric-entities --add "Invoice" --add "Customer" --project-dir "<PROJECT_DIR>" --output json
uip rpa install-data-fabric-entities --remove "LegacyOrder" --project-dir "<PROJECT_DIR>" --output json
uip rpa install-data-fabric-entities --add "Invoice" --remove "LegacyOrder" --namespace "My.App.Entities" --project-dir "<PROJECT_DIR>" --output json
```

Installation writes entity manifests and generated assemblies that workflows,
coded service calls, and test-data bindings compile against.

## Test Manager

| Command | Purpose |
| --- | --- |
| `uip rpa get-manual-test-cases --project-dir "<PROJECT_DIR>" --output json` | List unautomated manual test cases. |
| `uip rpa get-manual-test-steps --test-case-ids "id1,id2" --project-dir "<PROJECT_DIR>" --output json` | Retrieve manual test steps. |

## Integration Service

The linked upstream reference also covers `uip is` commands used with RPA
connector workflows:

| Command | Purpose |
| --- | --- |
| `uip is connectors list --output json` | List connectors, optionally filtered by name/key. |
| `uip is connectors get <CONNECTOR_KEY> --output json` | Get connector details. |
| `uip is connections list --output json` | List Integration Service connections. |
| `uip is connections create <CONNECTOR_KEY>` | Start OAuth connection creation. |
| `uip is connections ping <CONNECTION_ID>` | Verify a connection. |
| `uip is connections edit <CONNECTION_ID>` | Re-authenticate or edit a connection. |
| `uip is activities list <CONNECTOR_KEY> --output json` | List connector activities. |
| `uip is resources list <CONNECTOR_KEY> --output json` | List resource operations. |
| `uip is resources describe <CONNECTOR_KEY> <OBJECT_NAME> --output json` | Inspect a resource schema. |
| `uip is resources execute <OPERATION> <CONNECTOR_KEY> <OBJECT_NAME> --output json` | Execute a CRUD operation. |

## Workflow Examples And Studio Focus

| Command | Purpose |
| --- | --- |
| `uip rpa list-workflow-examples --tags "service1,service2" --output json` | Search example workflows by service tags. |
| `uip rpa get-workflow-example --key "<BLOB_PATH>" --output json` | Retrieve full XAML for an example workflow. |
| `uip rpa focus-activity --activity-id "<IDREF>" --output json` | Focus a specific activity in Studio. |
| `uip rpa focus-activity --output json` | Focus all activities sequentially. |

## Coded Workflow Helpers

Inspect a package API surface for coded workflow development:

```bash
uip rpa inspect-package --help
```

See the upstream `coded/inspect-package-guide.md` from the `uipath-rpa` skill
for command-specific details.

## Error Recovery

| Error Pattern | Likely Cause | Recovery |
| --- | --- | --- |
| `connection refused`, `EPIPE`, `pipe not found` | Studio IPC unavailable | Run `uip rpa start-studio`, then `uip rpa open-project`. |
| `timeout`, `ETIMEDOUT` | Studio operation took too long | Increase `--timeout` or use `--skip-validation` when appropriate. |
| `not authenticated`, `401`, `403` | Cloud auth required | Run `uip login`. |
| `package not found`, `version not available` | Wrong package ID/version | Verify with `find-activities` or omit version. |
| `project not found`, `no project open` | Wrong project directory or unopened project | Verify `--project-dir`, then `open-project`. |
| `file not found` in `get-errors` | File path is not project-relative | Pass a path relative to the project root. |
| `Studio is busy` | Studio is processing another operation | Wait briefly, then retry once. |

Do not retry the same failing command in a loop. Diagnose the cause, apply the
recovery step, then retry once.
