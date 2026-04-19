# `uip rpa get-errors` returns stale results — always run twice

## Symptom

Right after `write_file` modifies a `.cs` or `.xaml`, the very next
`uip rpa get-errors --project-dir <dir> --output json` call can return:

```json
{ "Result": "Success", "Code": "ToolResult",
  "Data": { "message": "No diagnostics found." } }
```

…even though a follow-up call (run a few seconds later, or after any other
Studio interaction) reports the real C# compile errors.

## Root cause

The Studio IPC backing `get-errors` is stateful. The first call after a
file change can race the in-process file watcher and respond from a stale
diagnostics snapshot.

## Rule

`uipath_claude/tools/uipath/cli_runner.run_uip_rpa_get_errors` defaults to
`passes=2` and **unions** the errors. Callers (the validation pipeline,
`validate_file`, `build_and_verify_workflow`) must use that default. A
single clean pass is **not** sufficient evidence to call a project verified.

## Verify-gate contract

For a project mutation to graduate to `verdict='pass'`:

1. `uip rpa get-errors --min-severity error` returns clean — pass 1.
2. `uip rpa get-errors --min-severity error` returns clean — pass 2.
3. `uip rpa run-file --command StartExecution` exits 0 (headless).
4. When Studio is detected:
   `uip rpa run-file --command StartDebugging --use-studio` exits 0.
   Otherwise return `verdict='needs_human'` with
   `next_action='start_studio_or_waive'`.

## See also

- `chapters/99-incidents/2026-04-19-invoice-queue-processor.md`
- `docs/build-logs/README.md`
