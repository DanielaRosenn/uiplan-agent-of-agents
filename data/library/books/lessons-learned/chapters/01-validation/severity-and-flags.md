# `get-errors` flags

| Flag                          | Effect                                             |
|-------------------------------|----------------------------------------------------|
| `--min-severity error`        | Only emits the `Errors (N):` block. Default in `run_uip_rpa_get_errors`. Removes the substring-based "is this a warning?" heuristic that was a source of false negatives. |
| `--use-studio`                | Drives the live Studio backend; required for full C# / activity validation. We default to True. |
| `--skip-validation`           | Returns the cached snapshot only. Useful for `studio_available()` probes; never use it for the verify-gate check. |
| `--file-path <relative>`      | Validate one file (relative to the project root). The pipeline iterates per-file so a failing file can be reported with its name. |
| `--project-dir <abs>`         | Required. Absolute path to the project root. |

## Parsing

`run_uip_rpa_get_errors` first tries `Data.Diagnostics` (structured).
When the CLI emits the textual `Errors (N):` / `Warnings (N):` blocks
(today's behavior), each `- ` bullet under each header is treated as a
diagnostic of that kind, regardless of whether the bullet text contains
the word "warning". The previous heuristic mis-classified compile errors
that mentioned "warning" anywhere in the message.
