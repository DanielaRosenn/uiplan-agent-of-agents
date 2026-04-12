# Mandatory Chat File Creation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When users ask the chat agent to create UiPath workflows, XAML, or documentation, the CLI must **write files under the working directory** (not only print WPF-style prose or generic how-to steps).

**Architecture:** Keep Bedrock as the generator, but (1) replace the generic chat system prompt with a **UiPath-first contract** that forbids off-domain UI stacks unless asked, (2) require the model to emit **parseable file blocks**, and (3) add a **deterministic materialization pass** after each assistant turn that extracts paths and contents and writes them to `generated/chat/` (gitignored) or an explicit `UIPATH_CHAT_OUTPUT_DIR`, then prints absolute paths to the user.

**Tech Stack:** Python 3.11+, Typer, existing `ConversationEngine`, new small module under `uipath_claude/artifacts/`, pytest.

---

## File map

| File | Responsibility |
|------|----------------|
| [uipath_claude/cli/app.py](c:/Users/DanielaRosenstein/projects/uipath-builder-agent/uipath_claude/cli/app.py) | Chat loop: stronger system prompt; call materializer after LLM reply; optional env flag to disable writes |
| [uipath_claude/artifacts/materialize.py](c:/Users/DanielaRosenstein/projects/uipath-builder-agent/uipath_claude/artifacts/materialize.py) (create) | Parse assistant text for `UIPATH_FILE:` blocks or fenced ``` blocks with filename; validate paths; write bytes |
| [uipath_claude/artifacts/__init__.py](c:/Users/DanielaRosenstein/projects/uipath-builder-agent/uipath_claude/artifacts/__init__.py) | Export public helpers if needed |
| [.gitignore](c:/Users/DanielaRosenstein/projects/uipath-builder-agent/.gitignore) | Ensure `generated/chat/` ignored (reuse `generated/` rule if already covers subtree) |
| [tests/unit/artifacts/test_materialize.py](c:/Users/DanielaRosenstein/projects/uipath-builder-agent/tests/unit/artifacts/test_materialize.py) (create) | Unit tests for extraction and path safety |
| [tests/integration/test_chat_materialize.py](c:/Users/DanielaRosenstein/projects/uipath-builder-agent/tests/integration/test_chat_materialize.py) (create) | Patch Bedrock; assert printed paths and files exist |
| [README.md](c:/Users/DanielaRosenstein/projects/uipath-builder-agent/README.md) or [QUICKSTART.md](c:/Users/DanielaRosenstein/projects/uipath-builder-agent/QUICKSTART.md) | Document `UIPATH_CHAT_OUTPUT_DIR`, block format, and that `/bootstrap` already writes docs |

---

### Task 1: Path-safe writer and fenced-block parser

**Files:**
- Create: `c:/Users/DanielaRosenstein/projects/uipath-builder-agent/uipath_claude/artifacts/materialize.py`
- Test: `c:/Users/DanielaRosenstein/projects/uipath-builder-agent/tests/unit/artifacts/test_materialize.py`

**Format (machine contract):** The model must be instructed to wrap each file as:

```
<<<UIPATH_FILE path="generated/chat/20260412-Example/Main.xaml">>>
...raw file body...
<<<END_UIPATH_FILE>>>
```

Alternate supported: first line inside a fence `path: relative/path.ext` then body (document in prompt). Parser must:

- Resolve only under `output_root / "generated" / "chat" / <session_stamp>/` OR under `UIPATH_CHAT_OUTPUT_DIR` if set (must still resolve to stay under that directory after `resolve()` — reject `..` components).
- Refuse absolute paths on Windows/Linux that escape the root.
- Return `list[tuple[Path, str]]` of written paths.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/artifacts/test_materialize.py
from pathlib import Path

from uipath_claude.artifacts.materialize import materialize_from_assistant_text


def test_materialize_writes_single_file(tmp_path: Path) -> None:
    root = tmp_path / "out"
    text = '''
Some intro.
<<<UIPATH_FILE path="Main.xaml">>>
<Activity x:Class="Main" xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
 xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence DisplayName="Root"><WriteLine Text="Hi" /></Sequence>
</Activity>
<<<END_UIPATH_FILE>>>
'''
    written = materialize_from_assistant_text(text, output_root=root)
    assert len(written) == 1
    assert written[0].exists()
    assert "WriteLine" in written[0].read_text(encoding="utf-8")


def test_materialize_rejects_parent_traversal(tmp_path: Path) -> None:
    from uipath_claude.artifacts.materialize import materialize_from_assistant_text

    root = tmp_path / "out"
    text = '<<<UIPATH_FILE path="../../../evil.txt">>>x<<<END_UIPATH_FILE>>>'
    written = materialize_from_assistant_text(text, output_root=root)
    assert written == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest c:/Users/DanielaRosenstein/projects/uipath-builder-agent/tests/unit/artifacts/test_materialize.py -v`

Expected: FAIL (import or function missing)

- [ ] **Step 3: Implement `materialize.py`**

```python
# uipath_claude/artifacts/materialize.py
from __future__ import annotations

import re
from pathlib import Path

_BLOCK = re.compile(
    r"<<<UIPATH_FILE path=(?P<q>[\"'])(?P<rel>.+?)(?P=q)>>>(?P<body>.*?)<<<END_UIPATH_FILE>>>",
    re.DOTALL,
)


def _safe_join(root: Path, rel: str) -> Path | None:
    rel = rel.strip().replace("\\", "/")
    if not rel or rel.startswith("/") or ".." in Path(rel).parts:
        return None
    dest = (root / rel).resolve()
    try:
        dest.relative_to(root.resolve())
    except ValueError:
        return None
    return dest


def materialize_from_assistant_text(text: str, output_root: Path) -> list[Path]:
    root = output_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for m in _BLOCK.finditer(text):
        rel = m.group("rel")
        body = m.group("body").strip("\n")
        dest = _safe_join(root, rel)
        if dest is None:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body, encoding="utf-8")
        written.append(dest)
    return written
```

- [ ] **Step 4: Run tests**

Run: `pytest c:/Users/DanielaRosenstein/projects/uipath-builder-agent/tests/unit/artifacts/test_materialize.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd c:/Users/DanielaRosenstein/projects/uipath-builder-agent
git add uipath_claude/artifacts/materialize.py tests/unit/artifacts/test_materialize.py
git commit -m "feat(artifacts): materialize UIPATH_FILE blocks from assistant text"
```

---

### Task 2: Wire chat loop to materialize after every assistant reply

**Files:**
- Modify: `c:/Users/DanielaRosenstein/projects/uipath-builder-agent/uipath_claude/cli/app.py` (function `_get_model_response` and chat loop after `response = ...`)

- [ ] **Step 1: Write failing integration test**

```python
# tests/integration/test_chat_materialize.py
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from uipath_claude.cli.app import app

runner = CliRunner()


def test_chat_writes_file_when_assistant_emits_block(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake_reply = '''Here is your workflow.
<<<UIPATH_FILE path="Main.xaml">>>
<Activity x:Class="Main" xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
 xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"><Sequence><WriteLine Text="Ok"/></Sequence></Activity>
<<<END_UIPATH_FILE>>>
'''
    with patch("uipath_claude.cli.app._create_engine") as eng:
        eng.return_value = object()
        with patch("uipath_claude.cli.app._get_model_response", new_callable=AsyncMock) as gmr:
            gmr.return_value = fake_reply
            result = runner.invoke(
                app,
                ["chat", "--no-banner"],
                input="create Main.xaml\nexit\n",
            )
    assert result.exit_code == 0
    hits = list(tmp_path.rglob("Main.xaml"))
    assert hits, "expected Main.xaml materialized under cwd"
```

Run: `pytest c:/Users/DanielaRosenstein/projects/uipath-builder-agent/tests/integration/test_chat_materialize.py -v`

Expected: FAIL until app wired.

- [ ] **Step 2: Add system prompt constant and post-process in `app.py`**

Add near top of `app.py` (after imports):

```python
_UIPATH_CHAT_SYSTEM = """You are UiPath Claude Code. You help build UiPath Studio automations (XAML workflows, project.json), not WPF unless the user explicitly asks for WPF.

When the user asks you to CREATE or WRITE files, you MUST output one or more file blocks using EXACTLY this format (no extra text inside the markers):

<<<UIPATH_FILE path="generated/chat/<shortname>/Main.xaml">>>
...valid workflow XAML body...
<<<END_UIPATH_FILE>>>

Use relative paths only; use forward slashes. Prefer under generated/chat/<folder>/.
After blocks, you may add one short sentence listing what you wrote.
"""
```

Change `_get_model_response` to pass `_UIPATH_CHAT_SYSTEM` as the system prompt content in the first message (keep memory injection pattern).

After `response = await ...` in chat loop, before print:

```python
from pathlib import Path
import os
from uipath_claude.artifacts.materialize import materialize_from_assistant_text

out = Path(os.environ.get("UIPATH_CHAT_OUTPUT_DIR", Path.cwd()))
written = materialize_from_assistant_text(str(response), output_root=out)
if written:
    print("Wrote:")
    for p in written:
        print(f"  {p}")
```

- [ ] **Step 3: Re-run integration test**

Run: `pytest c:/Users/DanielaRosenstein/projects/uipath-builder-agent/tests/integration/test_chat_materialize.py -v`

Expected: PASS

- [ ] **Step 4: Run full suite**

Run: `pytest c:/Users/DanielaRosenstein/projects/uipath-builder-agent/tests/ -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add uipath_claude/cli/app.py tests/integration/test_chat_materialize.py
git commit -m "feat(chat): materialize UIPATH_FILE blocks after each reply"
```

---

### Task 3: Document behavior and env flags

**Files:**
- Modify: `c:/Users/DanielaRosenstein/projects/uipath-builder-agent/QUICKSTART.md`

- [ ] **Step 1: Add section "Chat file output"**

Document:

- `UIPATH_CHAT_OUTPUT_DIR` — optional absolute or relative root for materialized files (default `.`).
- Block format `<<<UIPATH_FILE path="...">>>`.
- Remind that `/bootstrap "<request>"` already writes `docs/pdd`, `docs/sdd`, `docs/qa`, and `generated/automation/...` without needing fenced blocks.

- [ ] **Step 2: Fix stale `cd uipath-builder-agent-sprint-1` line** if still present — replace with `cd uipath-builder-agent`.

- [ ] **Step 3: Commit**

```bash
git add QUICKSTART.md
git commit -m "docs: chat file materialization and output dir"
```

---

## Spec coverage (self-review)

| Requirement | Task |
|-------------|------|
| Agent creates files, not only explains | Task 2 (post-process every reply) + Task 1 (parser) |
| UiPath XAML / docs, not generic WPF | Task 2 system prompt |
| Safety (no path escape) | Task 1 tests + `_safe_join` |
| User discoverability | Task 3 |
| Existing bootstrap pipeline unchanged | No edits to `run_bootstrap_flow` required; docs cross-link |

## Placeholder scan

No TBD/TODO left in tasks above.

---

**Plan complete and saved to** `docs/superpowers/plans/2026-04-12-mandatory-chat-file-creation.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration. **REQUIRED SUB-SKILL:** superpowers:subagent-driven-development.

2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints. **REQUIRED SUB-SKILL:** superpowers:executing-plans.

**Which approach?**
