# Library authoring guide

The documentation library is the agent's **first** source of truth. It is
designed for agents to browse deterministically (TOC → chapter → section), not
for humans to read front-to-back.

## Structure

```
data/library/
  catalog.yaml                       # list of books
  books/<book-id>/
    MANIFEST.yaml                    # metadata (audience, curator, license, ...)
    book.yaml                        # chapters (id, title, path, order)
    chapters/<NN-chapter-id>/
      chapter.yaml                   # sections (id, title, file, keywords[])
      <section-id>.md                # the actual content
```

### `MANIFEST.yaml` fields

| Field           | Notes                                                                |
| --------------- | -------------------------------------------------------------------- |
| `audience`      | `agent` (first-class) or `human` (reference only)                    |
| `curator`       | Who is responsible for this book                                     |
| `last_reviewed` | ISO-8601 date (`2026-04-18`)                                         |
| `homepage`      | Upstream URL for the source material (if any)                        |
| `license`       | SPDX id (e.g. `MIT`, `CC-BY-4.0`)                                    |

Books without a `MANIFEST.yaml` load fine — the fields default to empty.

## Writing rules (agent-first)

- **One idea per section.** Split long topics into multiple small sections.
- **Terse, imperative.** Skip narrative; write like a checklist.
- **Code before prose.** Put the snippet first, a brief explanation after.
- **Every section is addressable.** Keep section `id` stable — other tools cite
  it as `book/chapter/section`.
- **Budget: < ~400 words per section.** If you cross that, split.
- **Link internally by id** (e.g. `See orchestrator/releases`) — avoid URLs
  unless the source actually requires external context.

## Adding a new book

1. Create `data/library/books/<book-id>/` with `book.yaml`, optional
   `MANIFEST.yaml`, and one or more chapters.
2. Append `{id, path, title}` to `data/library/catalog.yaml`.
3. Run the unit test suite.

## Proposing via the agent

Agents never write to the library directly. They enqueue proposals:

- `propose_library_update(...)` — new/updated section.
- `propose_library_chapter(...)` — new chapter plus optional starter sections.

Review & apply with:

```bash
uipath-claude library-proposals list
uipath-claude library-proposals show <id>
uipath-claude library-proposals approve <id>
uipath-claude library-proposals reject <id>
```

Over MCP, the same surface is available as `uipath_library_list_proposals`,
`uipath_library_approve_proposal`, `uipath_library_reject_proposal`.

## Harvesting from upstream skills

`uipath-claude /library-harvest` walks the `skills/skills/*/SKILL.md` files in
the `UiPath/skills` submodule and enqueues a proposal per skill into the
`uipath-docs` book's `best-practices` chapter. Nothing is applied until a human
approves each proposal.

## Related

- [`docs/TOOLS.md`](TOOLS.md) — full tool surface.
- [`uipath_claude/library/catalog.py`](../uipath_claude/library/catalog.py) — loader.
- [`uipath_claude/library/writer.py`](../uipath_claude/library/writer.py) — create/update.
