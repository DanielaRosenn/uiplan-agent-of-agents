# Chat Runtime + Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `uipath-claude chat` fully functional with real Bedrock responses, test the CLI behavior thoroughly, and clean up root-folder clutter.

**Architecture:** Keep chat in `uipath_claude/cli/app.py` as the user-facing REPL, route slash commands through `CommandRegistry`, and call Bedrock via `ConversationEngine`. Use clear runtime errors instead of silent fallback. Reorganize non-product artifacts into archive folders.

**Tech Stack:** Python 3.11+, Typer, LangChain AWS (`ChatBedrockConverse`), pytest

---

### Task 1: Real Bedrock Chat Runtime

**Files:**
- Modify: `uipath_claude/cli/app.py`
- Modify: `uipath_claude/query/conversation.py`

- [x] Add engine bootstrap via `_create_engine()` with env-driven model/region.
- [x] Keep chat in REPL loop (`You:` prompt) with `exit`/`quit`.
- [x] Add `/chat` in-session behavior (`already in chat mode`).
- [x] Remove fake fallback chat as default behavior.
- [x] Add actionable Bedrock runtime error text for model/permission/region issues.
- [x] Keep message history and send it to `ConversationEngine`.
- [x] Ensure `ConversationEngine.run()` handles no-tools calls safely.

---

### Task 2: CLI Test Expansion

**Files:**
- Modify: `tests/unit/cli/test_app.py`
- Modify: `tests/integration/test_chat_flow.py`
- Modify: `pyproject.toml`

- [x] Unit test: chat starts and exits.
- [x] Unit test: `/chat` inside session is handled gracefully.
- [x] Unit test: Bedrock failure path prints actionable message.
- [x] Integration test: mocked model returns assistant text in chat.
- [x] Integration test: project auto-detection appears in output.
- [x] Register `integration` marker in pytest config.

---

### Task 3: Runtime Verification

**Verification Commands:**
- [x] `pytest tests/unit/cli/test_app.py tests/unit/cli/test_utils.py -v`
- [x] `python -c "<spawn uipath-claude chat, run /help + exit>"`
- [x] `python -c "<spawn uipath-claude chat, run hello + exit>"` (real Bedrock turn)

**Acceptance:**
- [x] CLI returns assistant response from Bedrock (not placeholder text)
- [x] Slash commands operate in REPL
- [x] Failures are explicit and actionable

---

### Task 4: Folder Cleanup (Full)

**Files/Folders:**
- Modify: `.gitignore`
- Add directories: `archive/reports/2026-04-09/`, `archive/docs/legacy/`, `scripts/maintenance/`
- Move files from root/docs into archive or scripts folders
- Remove runtime caches (`.coverage`, `coverage.json`, `htmlcov`, caches)

- [x] Add `.venv/` and `coverage.json` to `.gitignore`.
- [x] Move report artifacts from repo root to `archive/reports/2026-04-09/`.
- [x] Move one-off utility scripts to `scripts/maintenance/`.
- [x] Move legacy docs (`docs/API_DOCUMENTATION.md`, `docs/REFACTORING_PLAN.md`) to archive docs.
- [x] Delete local cache/coverage noise.

---

### Task 5: Quickstart/Usage Docs Refresh

**Files:**
- Modify: `README.md`
- Modify: `QUICKSTART.md`

- [x] Document correct chat command (`uipath-claude chat`).
- [x] Add Bedrock credential verification (`aws sts get-caller-identity`).
- [x] Add env overrides for model and region.
- [x] Update slash-command list with `/chat`.

---

## Final Validation Checklist

- [ ] Run full suite: `pytest tests/ -v`
- [ ] Run CLI help: `uipath-claude --help`
- [ ] Run chat smoke: `uipath-claude chat` then `/help`, `hello`, `exit`
- [ ] Verify root folder is materially cleaner than before
