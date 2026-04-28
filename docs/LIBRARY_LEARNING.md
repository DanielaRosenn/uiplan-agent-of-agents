# Library learning loop

The documentation library lives under `data/library/` in the repository (override with `UIPATH_CLAUDE_LIBRARY`). Sessions must not edit books directly; durable additions go through a **proposal, review, approve** flow.

## Lifecycle

1. The agent calls the `propose_library_update` tool with book/chapter/section metadata and markdown body.
2. Proposals are stored under `~/.uipath-claude/library-proposals/` (one JSON file per book). Override the root with `UIPATH_CLAUDE_LIBRARY_PROPOSALS`. The evaluation runner sets this to a temp directory for `Library` category tests.
3. An operator lists and reviews proposals, then approves or rejects.
4. **Approve** applies the markdown into `data/library/` via `LibraryWriter` and removes the proposal from the queue. **Reject** drops the proposal only.

```mermaid
flowchart LR
    Discovery[Agent discovers useful fact] --> Proposal[Stage proposal JSON]
    Proposal --> Queue[Proposal queue]
    Queue --> Doctor[uipath-claude doctor]
    Queue --> Review[Operator review]
    Review -->|approve| Library[data/library section]
    Review -->|reject| Drop[Drop proposal]
    Library --> Search[Future library search / lookup]
    Search --> Answer[Grounded answer with citation]
    Review --> Audit[Event log]
    Drop --> Audit
```

## CLI

```text
uipath-claude library-proposals list
uipath-claude library-proposals show <proposal_id>
uipath-claude library-proposals approve <proposal_id>
uipath-claude library-proposals reject <proposal_id>
```

Approve and reject append JSON lines to the structured event log (default `~/.uipath-claude/logs/events.log`, override `UIPATH_EVENT_LOG`) with `event` equal to `library_proposal_approved` or `library_proposal_rejected`.

## Operator workflow

Use this loop when reviewing captured lessons:

1. Run `uipath-claude doctor` to see pending proposal count, stale proposals, duplicate targets, and catalog readability.
2. Run `uipath-claude library-proposals list` to identify pending proposals.
3. Inspect each proposal with `uipath-claude library-proposals show <proposal_id>`.
4. Approve durable, generally useful lessons with `uipath-claude library-proposals approve <proposal_id>`.
5. Reject one-off, duplicate, or low-confidence lessons with `uipath-claude library-proposals reject <proposal_id>`.
6. Check the structured event log when you need an audit trail of approval/rejection decisions.

Doctor is read-only. It reports library health but never applies, rejects, or
rewrites proposals.

## Retrospective sources (transcripts and postmortems)

Agent transcripts and project postmortems are valid proposal sources when they
surface repeated delivery gaps (for example recurring HITL routing ambiguity,
placeholder completion, or missing runtime evidence contracts).

When proposing retrospective lessons:

1. Cite the parent conversation/transcript clearly (not only local notes).
2. Separate one-off project remediation from reusable builder-agent guidance.
3. Convert observations into durable rules ("always/never/required"), not raw
   logs or chat dumps.
4. Include confidence and scope boundaries when evidence is partial.
5. Reject proposals that cannot be verified beyond a single session.

### Review decision map

```mermaid
flowchart TD
    Proposal[Pending proposal] --> Durable{Reusable beyond one chat?}
    Durable -->|no| Reject[Reject]
    Durable -->|yes| Cited{Has source / citation metadata?}
    Cited -->|no| FixOrReject[Ask for citation or reject]
    Cited -->|yes| Duplicate{Duplicate target or existing section?}
    Duplicate -->|yes| Merge[Merge manually or reject duplicate]
    Duplicate -->|no| Safe{Safe, accurate, non-secret?}
    Safe -->|no| Reject
    Safe -->|yes| Approve[Approve]
    Approve --> Audit[Audit event]
    Reject --> Audit
    Merge --> Audit
    FixOrReject --> Audit
```

| Approve when... | Reject when... |
| --- | --- |
| The lesson is durable, cited, and useful for future UiPath work. | It is one-off, speculative, duplicated, secret-bearing, or missing source context. |
| The target book/chapter/section is clear. | The proposed section overlaps an existing approved section without adding value. |
| The content explains the why, not only the command. | The proposal is just raw chat transcript or temporary debugging noise. |

## Agent tool (LangChain)

- `propose_library_update(book_id, chapter_id, section_id, section_title, content, keywords, rationale)` — returns JSON with `proposal_id` and `status: pending`.

## MCP tool mapping

When driving the agent from Cursor or any other MCP client, use the `uipath_library_*` tools (see [CURSOR_USER_GUIDE.md](CURSOR_USER_GUIDE.md#library-tools-uipath_library_)):

| Action | MCP tool |
|--------|----------|
| Browse books / TOC / sections | `uipath_library_list`, `uipath_library_toc`, `uipath_library_read_section` |
| Search / question lookup | `uipath_library_search`, `uipath_library_lookup` |
| Stage a section proposal | `uipath_library_propose_section` |
| Stage a chapter proposal | `uipath_library_propose_chapter` |
| Review queue | `uipath_library_list_proposals` |
| Apply / drop proposal | `uipath_library_approve_proposal` / `uipath_library_reject_proposal` |

## Evaluations

Library behavior is covered by CLI evaluations in `docs/evaluations/test_cases.json` (`LIB-001` … `LIB-006`, category `Library`). Run:

```powershell
python docs/evaluations/run_evaluations.py --category Library
```

See [HOW_TO_RUN_TESTS.md](evaluations/HOW_TO_RUN_TESTS.md) for prerequisites (`UIPATH_SKIP_AUTH_CHECK`, `PYTHONIOENCODING`, project directory).
