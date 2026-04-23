# Track A Framework Structure Migration Implementation Plan

> **Plan record:** **Merged to `main` 2026-04-23** via `feat/parallel-a-b-impl` (fast-forward). Original task checkboxes below remain the historical script; see [§ Plan closure](#plan-closure-2026-04-23) for verification and resume notes.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize repository topology into `framework/`, `scaffold/`, and `ops/` with zero behavior regression.

**Architecture:** Implement a four-phase migration with dual-path compatibility in phases 2-3 and strict test gates between phases. Keep command contracts stable while references transition to new canonical paths. Remove legacy path support only after no-legacy regression checks pass.

**Tech Stack:** Python 3.11, pytest, MCP server, Cursor config, PowerShell/bash scripts

---

### Task 1: Add migration contract tests and smoke harness (Phase 1 baseline)

**Files:**
- Create: `tests/migration/test_structure_contract.py`
- Create: `tests/migration/test_path_resolution.py`
- Modify: `pyproject.toml`
- Test: `tests/migration/test_structure_contract.py`

- [ ] **Step 1: Write the failing structure contract test**

```python
# tests/migration/test_structure_contract.py
from pathlib import Path


def test_current_expected_roots_exist():
    root = Path(__file__).resolve().parents[2]
    expected = ["uipath_claude", "mcp_server", "scripts", "docs", "skills", "extensions"]
    missing = [name for name in expected if not (root / name).exists()]
    assert not missing, f"Missing roots: {missing}"
```

- [ ] **Step 2: Run the test to verify baseline**

Run: `uv run pytest tests/migration/test_structure_contract.py -q`  
Expected: PASS (or fail with explicit missing roots list if repo drifted).

- [ ] **Step 3: Add path-resolution test scaffold**

```python
# tests/migration/test_path_resolution.py
from pathlib import Path


def resolve_runtime_root(root: Path) -> Path:
    if (root / "framework" / "uipath_claude").exists():
        return root / "framework"
    return root


def test_resolve_runtime_root_prefers_legacy_before_phase2():
    root = Path(__file__).resolve().parents[2]
    runtime = resolve_runtime_root(root)
    assert (runtime / "uipath_claude").exists() or (runtime / "framework" / "uipath_claude").exists()
```

- [ ] **Step 4: Run migration baseline subset**

Run: `uv run pytest tests/migration -q`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/migration/test_structure_contract.py tests/migration/test_path_resolution.py pyproject.toml
git commit -m "test(migration): add structure baseline and path-resolution contracts"
```

### Task 2: Introduce new folders and dual-path compatibility (Phase 2)

**Files:**
- Create: `framework/.gitkeep`
- Create: `scaffold/template/.gitkeep`
- Create: `ops/scripts/.gitkeep`
- Create: `uipath_claude/context/path_contract.py`
- Modify: `mcp_server/server.py`
- Test: `tests/migration/test_path_resolution.py`

- [ ] **Step 1: Create target folders (non-destructive)**

Run:
```bash
mkdir -p framework scaffold/template ops/scripts
```
Expected: directories created with no existing file moves.

- [ ] **Step 2: Implement dual-path resolver helper**

```python
# uipath_claude/context/path_contract.py
from pathlib import Path


def runtime_root(repo_root: Path) -> Path:
    new_root = repo_root / "framework"
    if (new_root / "uipath_claude").exists() and (new_root / "mcp_server").exists():
        return new_root
    return repo_root


def scripts_root(repo_root: Path) -> Path:
    new_scripts = repo_root / "ops" / "scripts"
    if new_scripts.exists():
        return new_scripts
    return repo_root / "scripts"
```

- [ ] **Step 3: Wire one runtime call site to resolver (first migration seam)**

```python
# mcp_server/server.py (pattern)
from pathlib import Path
from uipath_claude.context.path_contract import runtime_root

repo_root = Path(__file__).resolve().parents[1]
active_root = runtime_root(repo_root)
```

- [ ] **Step 4: Run dual-path tests**

Run: `uv run pytest tests/migration/test_path_resolution.py -q`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add framework/.gitkeep scaffold/template/.gitkeep ops/scripts/.gitkeep uipath_claude/context/path_contract.py mcp_server/server.py tests/migration/test_path_resolution.py
git commit -m "feat(migration): add target roots and dual-path resolver seams"
```

### Task 3: Switch references, then remove legacy fallback (Phases 3 and 4)

**Files:**
- Modify: `langgraph.json`
- Modify: `.cursor/mcp.json`
- Modify: `README.md`
- Modify: `tests/migration/test_path_resolution.py`
- Test: `tests/migration/test_path_resolution.py`

- [ ] **Step 1: Add preferred-path assertions for phase 3**

```python
def test_new_path_preferred_when_framework_exists(tmp_path):
    (tmp_path / "framework" / "uipath_claude").mkdir(parents=True)
    (tmp_path / "framework" / "mcp_server").mkdir(parents=True)
    runtime = resolve_runtime_root(tmp_path)
    assert runtime == tmp_path / "framework"
```

- [ ] **Step 2: Update config/docs to canonical new paths**

```json
// langgraph.json (example intent)
{
  "graphs": {
    "builder": "framework/uipath_claude/graph:graph"
  }
}
```

- [ ] **Step 3: Add no-legacy assertion for phase 4 completion**

```python
def test_no_legacy_uipath_claude_path_after_phase4(root_path):
    assert not (root_path / "uipath_claude").exists()
```

- [ ] **Step 4: Run full migration + smoke subset**

Run:
```bash
uv run pytest tests/migration -q
uv run pytest tests/mcp/test_tool_annotations.py -q
uv run pytest tests/mcp/test_tool_descriptions.py -q
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add langgraph.json .cursor/mcp.json README.md tests/migration/test_path_resolution.py
git commit -m "refactor(migration): switch to new paths and add no-legacy gates"
```

## Verification

Run:

```bash
uv run pytest tests/migration -q
uv run pytest tests/mcp/test_tool_annotations.py tests/mcp/test_tool_descriptions.py -q
uv run pytest tests/mcp/test_plan_tools.py -q
```

Expected:
- all migration tests pass,
- no MCP regression on tool inventory and descriptions,
- plan tools remain functional.

## Rollback

- Reset to last checkpoint tag (`phase-1-pass`, `phase-2-pass`, `phase-3-pass`) if any phase fails repeatedly.
- Re-enable legacy path resolver branch before removing fallback code.
- Keep compatibility window open until shared smoke suite is green.

---

## Plan closure (2026-04-23)

**Disposition:** **Implemented on `main`** — `framework/uipath_claude`, `framework/mcp_server`, `framework/tests`, `ops/scripts`, `scaffold/template/`, dual-path resolver (`framework/uipath_claude/context/path_contract.py`), and migration tests under `framework/tests/migration/` are present after fast-forward merge from **`feat/parallel-a-b-impl`**.

**Design:** `docs/superpowers/specs/2026-04-23-framework-structure-migration-design.md` (finalized baseline).

**Post-merge verification (2026-04-23):** `uv run pytest framework/tests/migration tools/uiplan/tests -q` (8 passed); full suite `uv run pytest -q` (**1396 passed**, 9 skipped); `python -m uipath_claude.skills.submodule_guard` **OK** with `skills` HEAD recorded in `.uipath/skills-approved.sha`.

**Also on `main`:** Agentic executor only nudges build/verify when those tools exist; **`uip rpa close-project`** hygiene in `CLAUDE.md`, `docs/uipath-workflows.md`, `.cursor/skills/uipath-rpa/references/environment-setup.md`, `docs/Testing_Guide.md`, and executor system prompt.

**Phase 4 (not done yet — required for “clean” architecture):** Repo root still contains **legacy duplicates** alongside `framework/`: `uipath_claude/`, `mcp_server/`, and `scripts/` (verify with `Test-Path`). The design’s **Phase 4** is to remove old trees and resolver fallbacks after **S2** proves Track B has no stale path deps, then enforce **no-legacy** contract tests. Until Phase 4 lands, two copies can **drift** — prefer editing **`framework/`** only.

**Other steps often still outstanding after a merge like this:**

| Step | Why |
|------|-----|
| Re-run board **S2/S3** commands verbatim (paths: `framework/tests/...`) | Board paths were pre-move; confirms MCP + migration lanes after any change. |
| **`langgraph.json` / packaging entrypoints** | Still use import path `uipath_claude.graph:graph` (works with `pythonpath`); optional explicit `framework.uipath_claude.graph:graph` for clarity once Phase 4 removes root package. |
| **Git checkpoint tags** | Plan mentions `phase-1-pass` … `phase-4-final` — create if you rely on tagged rollback. |
| **Docs & links** | `README.md` still links `uipath_claude/tools/` as a repo path; should point at `framework/uipath_claude/tools/` after Phase 4 (or note “import path” vs path). |
| **Worktree / branch hygiene** | `feat/parallel-a-b-impl` may still sit at pre-merge SHA in a worktree — align or remove to avoid editing the wrong tree. |
| **CI / release** | If external pipelines invoked old `pytest tests/` paths, update them to `framework/tests/` (or rely on default `testpaths` in `pyproject.toml`). |
| **Push `main`** | Local branch ahead of `origin` until published. |

**Subagent-driven-development** remains the recommended shape for Phase 4 and doc/CI follow-ups (fresh implementer per task, spec then quality review, worktrees for risky refactors).
