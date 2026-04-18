# Smoke Tests

Two focused smoke tests that exercise the full surface: knowledge pipeline,
unified Ask AI, library proposals + chapters, book manifests, skills
auto-refresh, upstream scan, harvest, and MCP parity.

## CLI test (PowerShell)

Run from the repo root (`uipath-builder-agent`).

```powershell
# 0. Env: force a fresh session so the new per-session refresh actually triggers
$env:UIPATH_CHAT_SESSION_ID = "smoke-" + (Get-Date -Format "yyyyMMddHHmmss")
$env:UIPATH_SKILLS_AUTO_REFRESH = "1"
# Optional: enable web-search leg of the knowledge pipeline
# $env:UIPATH_WEB_SEARCH_ENABLED = "1"
# $env:TAVILY_API_KEY = "..."   # or SERPAPI_API_KEY

# 1. Launch chat; watch startup banner for "Skills cache: updated ..." or "skipped: ..."
python -m uipath_claude.cli.app chat
```

> Note: `python -m uipath_claude.cli.app` on its own prints "Missing command".
> The app is a Typer multi-command CLI. Use `chat`, `start-project`, or
> `library-proposals`.

Inside the chat REPL, run these slash-commands one by one:

```
/books                     # lists library books + manifest fields (audience, curator, license)
/books --info              # shows MANIFEST.yaml metadata per book
/scan-upstream-skills      # diff of new/removed skills in the skills/ submodule
/library-harvest           # enqueues NEW_SECTION proposals from every upstream SKILL.md
/library-proposals list    # shows queued proposals (from harvest + any chapter proposals)
```

Ask the agent a UiPath question to exercise the knowledge pipeline
(library → Ask AI → optional web search). Expect citations in the answer:

```
How do I schedule a job in UiPath Orchestrator? Cite sources.
```

Approve one harvested proposal end-to-end:

```
/library-proposals list
/library-proposals approve <paste-a-proposal-id>
```

Re-run scan; diff should show no *new* changes this session:

```
/scan-upstream-skills
```

Exit, then re-enter with the SAME session id to prove per-session skip:

```powershell
exit
python -m uipath_claude.cli.app chat
# Banner should show: "Skills cache: skipped: same session"
```

New session id => refresh runs again (force-reset, backup branch on drift):

```powershell
$env:UIPATH_CHAT_SESSION_ID = "smoke-" + (Get-Date -Format "yyyyMMddHHmmss")
python -m uipath_claude.cli.app chat
```

## Full chat test drive: build a real UiPath project

This exercises BA → SA → planner → Dev → QA, the knowledge pipeline, Ask AI,
skills, and Studio integration end-to-end.

1. Sanity checks inside the chat REPL:

   ```
   /books --info
   /scan-upstream-skills
   ```

2. Kick off a project via free-text chat:

   ```
   Build a UiPath attended automation called "InvoiceTriage" that:
    - watches a SharePoint folder for new PDF invoices,
    - extracts vendor, invoice number, total, and due date using Document Understanding,
    - writes the results to a SQL Server table dbo.Invoices,
    - sends a Teams notification on failure.
   Use our library as the primary source and cite sources.
   ```

   Expected flow:
   - BA produces requirements.
   - SA produces a design with citations like `[uipath-docs/...]`.
   - Planner emits a plan; approve it when prompted.
   - Dev writes the project (XAML + `project.json`).
   - QA adds and runs tests.

3. Verify artifacts (in a second PowerShell, same cwd):

   ```powershell
   Get-ChildItem .\InvoiceTriage
   Get-Content .\InvoiceTriage\project.json -TotalCount 40
   ```

4. Non-interactive bootstrap path (second confirmation):

   ```powershell
   python -m uipath_claude.cli.app start-project InvoiceTriage2
   ```

5. Follow-ups inside chat to hit more tools:

   ```
   Ask UiPath AI: difference between attended and unattended robots.
   Look up "retry scope best practices" in the library and cite.
   /library-proposals list
   /library-proposals approve <id>
   ```

### What to verify

- Citations on any knowledge lookup answer.
- `InvoiceTriage/` contains a valid `project.json`, `Main.xaml`, and tests.
- No errors referencing `install_git_hooks`.
- Second chat launch with the same `UIPATH_CHAT_SESSION_ID` prints
  `Skills cache: skipped: same session`.

### What to verify

- Banner prints `Skills cache: updated ...` on first run, `skipped: same session` on the second.
- `/books --info` shows `audience: agent`, `curator: uipath-builder-agent`, etc. for `uipath-docs`.
- `/library-harvest` returns "N proposals enqueued" and `/library-proposals list` shows them.
- The UiPath question answer contains bracketed citations like `[uipath-docs/<chapter>/<section>]` or an Ask-AI source.
- After approve, the target section exists under `data/library/books/uipath-docs/<chapter>/<section>.md`.
- No `post-merge` / `post-checkout` / `post-rewrite` files in `.git/hooks/` (removed).

## Cursor test (MCP tools)

Point Cursor's MCP config at this repo's server (already wired via
`mcp_server/server.py`). In a Cursor chat, run these prompts in order — each
one forces a specific `uipath_library_*` tool and exercises the same surface
without the CLI.

1. **List books**
   > "List all UiPath library books with their manifests."
   Calls `uipath_library_list`; shows audience/curator/license.

2. **TOC**
   > "Show the table of contents for the uipath-docs book."
   Calls `uipath_library_toc`.

3. **Search**
   > "Search the library for 'orchestrator schedule' and show the top 3 sections."
   Calls `uipath_library_search`.

4. **Read section**
   > "Read section <paste id from step 3>."
   Calls `uipath_library_read_section`.

5. **Full knowledge lookup**
   > "Look up 'how to create an attended robot' using the full knowledge pipeline. Cite sources."
   Calls `uipath_library_lookup` (library → Ask AI → web if enabled).
   The answer **must** include citations.

6. **Propose a chapter**
   > "Propose a new chapter 'Patterns' in uipath-docs with an initial section called 'Retry loops'."
   Calls `uipath_library_propose_*` then `uipath_library_list_proposals`.
   Verify the proposal shows `kind = new_chapter`.

7. **Approve**
   > "Approve proposal <id from step 6>."
   Calls `uipath_library_approve_proposal`. Check that
   `data/library/books/uipath-docs/patterns/` now exists with `chapter.yaml`.

8. **Reject**
   > "Reject proposal <another id>."
   Calls `uipath_library_reject_proposal`; it should disappear from the list.

9. **Unified Ask AI**
   > "Ask UiPath AI: what's the difference between attended and unattended?"
   Invokes `query_uipath_docs` (SDK-first, HTTP fallback).

### What to verify in Cursor

- Every step invokes a distinct `uipath_library_*` / `query_uipath_docs` /
  `lookup_uipath_knowledge` tool (visible in the tool-call trace).
- Proposals round-trip: create → list → approve writes files; reject removes them.
- Citations appear on any knowledge lookup answer.
- No errors about git hooks or missing `install_git_hooks` (proves the removal is clean).

If any step fails, grab the tool-call payload from Cursor's trace and the
corresponding log line — that's enough to pinpoint whether the failure is in
the library layer, Ask AI, or the updater.
