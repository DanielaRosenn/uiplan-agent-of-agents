# Hermes-Inspired Core Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Hermes-inspired operational controls to UiPath Claude Code: tool profiles, CLI approval policy, and session recall.

**Architecture:** Keep the current Python/LangGraph structure, and add thin modules in `tools/`, `commands/`, and `query/`. Do not rewrite the conversation engine. Extend existing command registration and state flow with small, testable seams.

**Tech Stack:** Python 3.11, Typer CLI, LangChain/LangGraph, pytest.

---

## File Structure (planned changes)

- `uipath_claude/tools/profiles.py` (new): Defines tool profiles (`safe`, `uipath-dev`, `all`) and resolver.
- `uipath_claude/tools/uipath/approval.py` (new): Env-driven approval guard for CLI-impacting actions.
- `uipath_claude/query/session_search.py` (new): Lightweight session search over in-memory chat history.
- `uipath_claude/commands/recall.py` (new): `/recall` command to search current-session conversation turns.
- `uipath_claude/cli/app.py` (modify): Wire profile selection and recall command registration.
- `uipath_claude/tools/uipath/analyzer.py` (modify): Enforce approval policy before analyze execution.
- `uipath_claude/commands/validate.py` (modify): Enforce approval policy before analyze/pack execution.
- `uipath_claude/commands/status.py` (modify): Include active tool profile and approval mode in output.
- `tests/unit/tools/test_profiles.py` (new): Unit tests for profile resolver behavior.
- `tests/unit/tools/uipath/test_approval.py` (new): Unit tests for approval policy logic.
- `tests/unit/query/test_session_search.py` (new): Unit tests for recall search ranking/filtering.
- `tests/unit/commands/test_recall_command.py` (new): Unit tests for `/recall` command output.
- `tests/unit/commands/test_validate_command.py` (new): Approval-gate tests for `/validate`.
- `docs/ARCHITECTURE.md` (modify): Document new control plane modules and command.
- `README.md` (modify): Add usage for `UIPATH_CLAUDE_TOOL_PROFILE`, `UIPATH_CLAUDE_REQUIRE_APPROVAL`, `/recall`.

---

### Task 1: Add Tool Profiles

**Files:**
- Create: `uipath_claude/tools/profiles.py`
- Modify: `uipath_claude/cli/app.py`
- Modify: `uipath_claude/commands/status.py`
- Test: `tests/unit/tools/test_profiles.py`

- [ ] **Step 1: Write the failing tests for profile resolution**

```python
from uipath_claude.tools.profiles import resolve_tool_profile, supported_profiles


def test_supported_profiles_contains_expected_profiles():
    profiles = supported_profiles()
    assert profiles == ["all", "safe", "uipath-dev"]


def test_resolve_tool_profile_uses_default_safe_for_unknown():
    profile = resolve_tool_profile("unknown-profile")
    assert profile.name == "safe"
    assert "workflow_analyzer_tool" in profile.tool_names


def test_resolve_tool_profile_includes_validate_for_uipath_dev():
    profile = resolve_tool_profile("uipath-dev")
    assert profile.name == "uipath-dev"
    assert "validate_command" in profile.command_allowlist
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/tools/test_profiles.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'uipath_claude.tools.profiles'`

- [ ] **Step 3: Write minimal profile implementation**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolProfile:
    name: str
    tool_names: list[str]
    command_allowlist: list[str]


_PROFILES = {
    "safe": ToolProfile(
        name="safe",
        tool_names=["skill_tool"],
        command_allowlist=["help", "status", "skills", "recall"],
    ),
    "uipath-dev": ToolProfile(
        name="uipath-dev",
        tool_names=["skill_tool", "workflow_analyzer_tool"],
        command_allowlist=["help", "status", "skills", "analyze", "validate", "bootstrap", "recall"],
    ),
    "all": ToolProfile(
        name="all",
        tool_names=["skill_tool", "workflow_analyzer_tool"],
        command_allowlist=["*"],
    ),
}


def supported_profiles() -> list[str]:
    return sorted(_PROFILES.keys())


def resolve_tool_profile(raw_name: str | None) -> ToolProfile:
    key = (raw_name or "safe").strip().lower()
    return _PROFILES.get(key, _PROFILES["safe"])
```

- [ ] **Step 4: Wire profile into CLI status payload**

```python
# in uipath_claude/cli/app.py
profile_name = os.getenv("UIPATH_CLAUDE_TOOL_PROFILE", "safe")
resolved_profile = resolve_tool_profile(profile_name)

def _status() -> dict[str, str | int | bool]:
    return {
        "model": model_name,
        "region": region,
        "project_detected": bool(project_context),
        "project_name": project_context["project_name"] if project_context else "n/a",
        "memory_loaded": bool(memory),
        "skill_count": len(skills),
        "tool_profile": resolved_profile.name,
    }
```

- [ ] **Step 5: Run tests to verify pass**

Run: `pytest tests/unit/tools/test_profiles.py tests/unit/commands/test_status_command.py -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add uipath_claude/tools/profiles.py uipath_claude/cli/app.py uipath_claude/commands/status.py tests/unit/tools/test_profiles.py
git commit -m "feat: add tool profile controls for chat sessions"
```

---

### Task 2: Add Approval Guard for UiPath CLI Actions

**Files:**
- Create: `uipath_claude/tools/uipath/approval.py`
- Modify: `uipath_claude/tools/uipath/analyzer.py`
- Modify: `uipath_claude/commands/validate.py`
- Test: `tests/unit/tools/uipath/test_approval.py`
- Test: `tests/unit/tools/uipath/test_analyzer.py`
- Test: `tests/unit/commands/test_validate_command.py`

- [ ] **Step 1: Write failing approval tests**

```python
from uipath_claude.tools.uipath.approval import check_cli_approval


def test_check_cli_approval_allows_when_flag_false():
    ok, reason = check_cli_approval({"UIPATH_CLAUDE_REQUIRE_APPROVAL": "false"})
    assert ok is True
    assert reason == ""


def test_check_cli_approval_blocks_without_explicit_yes():
    ok, reason = check_cli_approval({"UIPATH_CLAUDE_REQUIRE_APPROVAL": "true"})
    assert ok is False
    assert "blocked" in reason.lower()


def test_check_cli_approval_allows_with_explicit_yes():
    ok, reason = check_cli_approval(
        {"UIPATH_CLAUDE_REQUIRE_APPROVAL": "true", "UIPATH_CLAUDE_APPROVE": "yes"}
    )
    assert ok is True
    assert reason == ""
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/unit/tools/uipath/test_approval.py -v`  
Expected: FAIL with missing module error

- [ ] **Step 3: Implement approval policy**

```python
def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def check_cli_approval(env: dict[str, str] | None = None) -> tuple[bool, str]:
    env_map = env or {}
    require = _truthy(env_map.get("UIPATH_CLAUDE_REQUIRE_APPROVAL", "false"))
    approved = _truthy(env_map.get("UIPATH_CLAUDE_APPROVE", "false"))
    if require and not approved:
        return (
            False,
            "CLI execution blocked: set UIPATH_CLAUDE_APPROVE=yes for this session.",
        )
    return True, ""
```

- [ ] **Step 4: Gate analyzer and validate flows**

```python
# in analyzer.py
allowed, reason = check_cli_approval(dict(os.environ))
if not allowed:
    return reason

# in validate.py
allowed, reason = check_cli_approval(dict(os.environ))
if not allowed:
    return reason
```

- [ ] **Step 5: Add/adjust tests for analyzer and validate behavior**

```python
def test_workflow_analyzer_returns_block_message_when_approval_missing(monkeypatch):
    monkeypatch.setenv("UIPATH_CLAUDE_REQUIRE_APPROVAL", "true")
    monkeypatch.delenv("UIPATH_CLAUDE_APPROVE", raising=False)
    result = workflow_analyzer_tool.invoke({"project_path": "/test/project"})
    assert "blocked" in result.lower()
```

- [ ] **Step 6: Run tests to verify pass**

Run: `pytest tests/unit/tools/uipath/test_approval.py tests/unit/tools/uipath/test_analyzer.py tests/unit/commands/test_validate_command.py -v`  
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add uipath_claude/tools/uipath/approval.py uipath_claude/tools/uipath/analyzer.py uipath_claude/commands/validate.py tests/unit/tools/uipath/test_approval.py tests/unit/tools/uipath/test_analyzer.py tests/unit/commands/test_validate_command.py
git commit -m "feat: add approval gate for uipath cli operations"
```

---

### Task 3: Add Session Recall Command

**Files:**
- Create: `uipath_claude/query/session_search.py`
- Create: `uipath_claude/commands/recall.py`
- Modify: `uipath_claude/cli/app.py`
- Test: `tests/unit/query/test_session_search.py`
- Test: `tests/unit/commands/test_recall_command.py`

- [ ] **Step 1: Write failing session-search tests**

```python
from uipath_claude.query.session_search import search_session_history


def test_search_session_history_returns_recent_matches_first():
    history = [
        {"role": "user", "content": "create queue"},
        {"role": "assistant", "content": "use Orchestrator queue create"},
        {"role": "user", "content": "queue retry policy"},
    ]
    hits = search_session_history(history, "queue", limit=2)
    assert len(hits) == 2
    assert "retry" in hits[0]["content"]


def test_search_session_history_empty_query_returns_empty():
    assert search_session_history([], "", limit=5) == []
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/unit/query/test_session_search.py -v`  
Expected: FAIL with missing module error

- [ ] **Step 3: Implement search and command module**

```python
# session_search.py
def search_session_history(
    history: list[dict[str, str]], query: str, limit: int = 5
) -> list[dict[str, str]]:
    q = (query or "").strip().lower()
    if not q:
        return []
    matches = []
    for item in reversed(history):
        content = item.get("content", "")
        if q in content.lower():
            matches.append(item)
        if len(matches) >= limit:
            break
    return matches
```

```python
# recall.py
def register_recall_command(registry: CommandRegistry, get_history: Callable[[], list[dict[str, str]]]) -> None:
    @register_command(registry, name="recall", description="Search current session messages")
    def recall_command(*query_parts: str) -> str:
        query = " ".join(query_parts).strip()
        if not query:
            return 'Usage: /recall "<keyword>"'
        hits = search_session_history(get_history(), query, limit=5)
        if not hits:
            return f'No session matches for "{query}".'
        lines = [f'Session matches for "{query}":']
        for idx, hit in enumerate(hits, start=1):
            lines.append(f'{idx}. [{hit.get("role", "unknown")}] {hit.get("content", "")}')
        return "\n".join(lines)
```

- [ ] **Step 4: Wire `/recall` in app command registry**

```python
history: list[dict[str, str]] = []

def _get_history() -> list[dict[str, str]]:
    return history

register_recall_command(registry, get_history=_get_history)
```

- [ ] **Step 5: Run tests to verify pass**

Run: `pytest tests/unit/query/test_session_search.py tests/unit/commands/test_recall_command.py -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add uipath_claude/query/session_search.py uipath_claude/commands/recall.py uipath_claude/cli/app.py tests/unit/query/test_session_search.py tests/unit/commands/test_recall_command.py
git commit -m "feat: add /recall command for session search"
```

---

### Task 4: Documentation and End-to-End Regression Check

**Files:**
- Modify: `README.md`
- Modify: `docs/ARCHITECTURE.md`
- Test: `tests/unit/test_package_structure.py`

- [ ] **Step 1: Write failing doc assertion test for new command/module listing**

```python
from pathlib import Path


def test_architecture_mentions_recall_and_profiles():
    content = Path("docs/ARCHITECTURE.md").read_text()
    assert "recall" in content.lower()
    assert "tool profile" in content.lower()
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/unit/test_package_structure.py -v`  
Expected: FAIL until architecture text is updated

- [ ] **Step 3: Update docs with exact runtime controls**

```markdown
- Tool profiles: `UIPATH_CLAUDE_TOOL_PROFILE=safe|uipath-dev|all`
- Approval gate: `UIPATH_CLAUDE_REQUIRE_APPROVAL=true` and one-shot `UIPATH_CLAUDE_APPROVE=yes`
- Session recall: `/recall "<term>"`
```

- [ ] **Step 4: Run full unit suite for touched areas**

Run: `pytest tests/unit/tools/ tests/unit/commands/ tests/unit/query/ -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add README.md docs/ARCHITECTURE.md tests/unit/test_package_structure.py
git commit -m "docs: document hermes-inspired controls and recall workflow"
```

---

## Validation Checklist (self-review)

- Spec coverage: this plan only covers the Hermes-inspired parts that fit now (profiles, approval, recall), not Hermes full messaging/voice/RL stack.
- Placeholder scan: no TODO/TBD placeholders remain.
- Type consistency: all planned APIs use existing project conventions (`dict[str, str]`, `CommandRegistry`, small module helpers).

