# BUILD_LOG.md and the lessons-learned workflow

Every UiPath project that the `uipath-builder-agent` (or a human
collaborator) touches gets an append-only `BUILD_LOG.md` in its project
root. This is the source of truth for **how the project was built**, and
the raw material for the cross-project
[`lessons-learned`](../../data/library/books/lessons-learned/) book.

## What is BUILD_LOG.md?

A Markdown file written by `uipath_claude/audit/build_log.py`. Each
event records:

| Field                | Meaning                                                                 |
|----------------------|-------------------------------------------------------------------------|
| `timestamp`          | UTC ISO-8601 of when the action started.                                |
| `actor`              | `agent` (skill tool), `cli` (uip wrapper), or `user` (manual entry).    |
| `action`             | `write_file`, `install_package`, `get_errors`, `run_file`, `start_debugging`, `build_and_verify`, `deploy_to_orchestrator`, … |
| `command`            | Full argv of the underlying CLI call. Secrets are masked by `uipath_claude/audit/redact.py`. |
| `exit_code`          | Numeric exit code, `timeout`, `missing-cli`, etc.                       |
| `stdout_excerpt` / `stderr_excerpt` | First and last 50 lines (with redaction).                                |
| `files_written`      | List of `{path, sha256, bytes}` for every file the action wrote.        |
| `validation_passes`  | Per-pass error / warning counts for `get-errors`.                       |
| `studio_attached`    | `True`, `False`, `skipped`, or `unknown`.                               |
| `outcome`            | `pass`, `needs_llm_fix`, `needs_human`, `error`.                        |

The file is **append-only**. Never edit historical entries; add new ones.

## Why it exists

1. **Audit.** A reviewer can answer "what exactly did the agent run on
   `examples/InvoiceQueueProcessor` last week?" without replaying the
   chat session.
2. **Debugging.** When a job fails in production, the BUILD_LOG.md for
   that project tells you which validation passes were attempted, which
   packages were installed, and which Studio debug attempts succeeded.
3. **Learning.** Patterns that repeat across projects graduate into the
   `lessons-learned` book.

## Verify-gate contract (summary)

The agent will not call a project verified unless the BUILD_LOG.md for
that project records, in order:

1. `get-errors --min-severity error` clean — pass 1.
2. `get-errors --min-severity error` clean — pass 2 (defeats the Studio
   IPC stale-cache failure mode).
3. `run-file --command StartExecution` exit 0 (headless).
4. When Studio is detected:
   `run-file --command StartDebugging --use-studio` exit 0.
   Otherwise the verify gate emits `verdict='needs_human'` with
   `next_action='start_studio_or_waive'`.

See
[`data/library/books/lessons-learned/chapters/01-validation/get-errors-stale-cache.md`](../../data/library/books/lessons-learned/chapters/01-validation/get-errors-stale-cache.md)
for the failure mode this contract is defending against.

## How an incident becomes a lesson

1. The agent (or a human reviewer) sees a `BUILD_LOG.md` event with
   `outcome=needs_llm_fix` (or worse, a false positive `outcome=pass`
   that turned out to be wrong).
2. After the fix lands, the project's BUILD_LOG.md gets a final
   `outcome=pass` entry.
3. The reviewer writes a short post-mortem at
   `data/library/books/lessons-learned/chapters/99-incidents/<date>-<slug>.md`
   that links back to the relevant BUILD_LOG.md entries and to the
   chapter that captures the rule going forward.
4. If the rule itself is new, add (or update) a section under the
   matching chapter (`01-validation`, `02-coded-workflows`,
   `03-orchestrator-queues`, `04-database`).

## Project index

Every example project that has produced a BUILD_LOG.md is listed here.
Update this table when a new project gains its first audit entry.

| Project                                | BUILD_LOG.md                                                                 | First incident note                                                                                              |
|----------------------------------------|------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| `examples/InvoiceQueueProcessor`       | [BUILD_LOG.md](../../examples/InvoiceQueueProcessor/BUILD_LOG.md)            | [2026-04-19 ErrorType + stale get-errors](../../data/library/books/lessons-learned/chapters/99-incidents/2026-04-19-invoice-queue-processor.md) |

## Secret hygiene

Connection strings, tokens, asset values, and credential names are
masked by `uipath_claude/audit/redact.py` before being written. If a new
secret-bearing flag is added to the CLI, extend `_SECRET_FLAGS` and
`_SECRET_REGEXES` in that module and add a unit test.
