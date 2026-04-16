# Library learning loop

The documentation library lives under `data/library/` in the repository (override with `UIPATH_CLAUDE_LIBRARY`). Sessions must not edit books directly; durable additions go through a **proposal, review, approve** flow.

## Lifecycle

1. The agent calls the `propose_library_update` tool with book/chapter/section metadata and markdown body.
2. Proposals are stored under `~/.uipath-claude/library-proposals/` (one JSON file per book). Override the root with `UIPATH_CLAUDE_LIBRARY_PROPOSALS`. The evaluation runner sets this to a temp directory for `Library` category tests.
3. An operator lists and reviews proposals, then approves or rejects.
4. **Approve** applies the markdown into `data/library/` via `LibraryWriter` and removes the proposal from the queue. **Reject** drops the proposal only.

## CLI

```text
uipath-claude library-proposals list
uipath-claude library-proposals show <proposal_id>
uipath-claude library-proposals approve <proposal_id>
uipath-claude library-proposals reject <proposal_id>
```

Approve and reject append JSON lines to the structured event log (default `~/.uipath-claude/logs/events.log`, override `UIPATH_EVENT_LOG`) with `event` equal to `library_proposal_approved` or `library_proposal_rejected`.

## Agent tool

- `propose_library_update(book_id, chapter_id, section_id, section_title, content, keywords, rationale)` — returns JSON with `proposal_id` and `status: pending`.

## Evaluations

Library behavior is covered by CLI evaluations in `docs/evaluations/test_cases.json` (`LIB-001` … `LIB-006`, category `Library`). Run:

```powershell
python docs/evaluations/run_evaluations.py --category Library
```

See [HOW_TO_RUN_TESTS.md](evaluations/HOW_TO_RUN_TESTS.md) for prerequisites (`UIPATH_SKIP_AUTH_CHECK`, `PYTHONIOENCODING`, project directory).
