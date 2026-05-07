# Legacy docs

These docs are kept for reference but are scheduled for consolidation.
Each one overlaps with at least one other doc here or with a primary
guide under `docs/`.

| File | Status | Consolidation target |
|---|---|---|
| `CLAUDE_USER_GUIDE.md` | Overlaps with `../USER_GUIDE.md` (terminal-Claude specifics) | merge into `../USER_GUIDE.md` |
| `PURE_CLAUDE_CODE.md` | Overlaps with `../USER_GUIDE.md` (Anthropic `claude` CLI variant) | merge into `../USER_GUIDE.md` |
| `MANUAL_EVAL_AND_QA.md` | Canonical manual-QA checklist; overlaps with the two below | becomes the canonical `../MANUAL_QA.md` once merged |
| `MANUAL_REVIEW_CURSOR_FULL_PROJECT.md` | Phase-specific manual review matrix | merge salvageable parts into `../MANUAL_QA.md` |
| `MANUAL_TESTING_POST_PHASE4.md` | Phase-4 post-release checklist | merge salvageable parts into `../MANUAL_QA.md` |
| `PRODUCTIZATION_STATUS.md` | Point-in-time productization snapshot (now stale) | replace with a `../PRODUCT_STATUS.md` if still needed |
| `LEARNING_LOOP.md` | Earlier framing of the learning loop | merge into `../LIBRARY_AUTHORING.md` |
| `DEMO_RUNBOOK.md` | Manual demo script (large, mostly stale) | trim to a short demo card or delete |

When consolidating, copy salvageable content into the target file under
clearly-named sections, then `git rm` the file from this folder.

Nothing here was content-changed during the 2026-05 cleanup; only moved.
