# Manual testing after Phase 4 + UiPlan (repo layout)

Use this checklist after pulling `main` to confirm **framework-only runtime**, **UiPlan kit under `docs/uiplan/`**, **MCP path**, and **tooling** behave as expected. It complements automated tests (`pytest`) and does **not** replace Orchestrator deploy smoke (not in scope for this migration).

For a **deeper, Cursor-first pass** (natural-language prompts to test MCP intent routing, UiPlan doc/kit checks, per-tool NL examples, slash commands, and a copy-paste **results** block), use [MANUAL_REVIEW_CURSOR_FULL_PROJECT.md](MANUAL_REVIEW_CURSOR_FULL_PROJECT.md). **Minimal onboarding:** run `ops/scripts/cursor-quickstart.ps1` (Windows) or `bash ops/scripts/cursor-quickstart.sh` (Unix), then open the repo in Cursor. Scripted scenarios that overlap this checklist are detailed in [SMOKE_TESTS.md](SMOKE_TESTS.md).

## Preconditions

- Python 3.11+ and [uv](https://docs.astral.sh/uv/) (or your usual venv with the project installed editable).
- Repo root = workspace root when running commands below.
- Optional: Node.js + global `@uipath/cli` if you will run **uip** checks (see step 8).

## 1. Git and submodules

```powershell
cd <repo-root>
git checkout main
git pull
git submodule update --init --recursive
```

**Expect:** `skills/` present; no merge conflicts. If `skills` shows a detached SHA, that is normal when the parent pins a commit.

## 2. Submodule guard (hard gate)

```powershell
uv run python -m uipath_claude.skills.submodule_guard
```

**Expect:** `submodule-guard: OK`. If it fails, either revert `skills/` to a SHA listed in `.uipath/skills-approved.sha` or append a reviewed SHA per [CLAUDE.md](../CLAUDE.md).

## 3. Layout (Phase 4)

From repo root, confirm:

| Check | Expected |
| --- | --- |
| `framework/uipath_claude/` exists | Yes |
| `framework/mcp_server/` exists | Yes |
| `ops/scripts/` exists | Yes |
| `docs/uiplan/kit/_spec-template.md` exists | Yes |
| Root `uipath_claude/` (package tree) | **Absent** |
| Root `mcp_server/` | **Absent** |
| Root `scripts/` (legacy) | **Absent** |

PowerShell one-liner:

```powershell
@('uipath_claude','mcp_server','scripts') | % { if (Test-Path $_) { "FAIL: $_ exists" } }; Test-Path docs/uiplan/kit/_spec-template.md; Test-Path framework/mcp_server/server.py
```

**Expect:** no `FAIL` lines; last two lines `True`.

## 4. Automated tests (full suite)

```powershell
uv sync
uv run pytest -q
```

**Expect:** all tests pass (exit code 0). Optional faster slices from the parallel board:

```powershell
uv run pytest tools/uiplan/tests framework/tests/migration -q
uv run pytest framework/tests/mcp/test_tool_annotations.py framework/tests/mcp/test_tool_descriptions.py framework/tests/mcp/test_plan_tools.py -q
```

**Last recorded full run (CI-style):** `1406 passed, 8 skipped` (warnings only).

## 5. UiPlan CLI (`generate-docs`)

Pick a throwaway slug and output folder:

```powershell
$out = Join-Path $env:TEMP "uiplan-manual-test"
Remove-Item -Recurse -Force $out -ErrorAction SilentlyContinue
uv run python -m tools.uiplan generate-docs 2099-12-31-manual-test --out $out
Get-ChildItem $out
```

**Expect:** `Wrote UiPlan docs to ...`; folder contains `spec.md`, `plan.md`, `tasks.md`. Open the three files; each should contain at least the minimum Mermaid blocks (validator enforced unless you passed `--no-strict`).

Strict vs loose:

```powershell
uv run python -m tools.uiplan generate-docs 2099-12-31-strict-test --out $out --strict
```

## 6. MCP server import smoke (no Cursor required)

```powershell
$env:PYTHONPATH = "$PWD\framework"
uv run python -c "import mcp_server.server; print('ok')"
```

**Expect:** `ok`. This confirms `mcp_server` resolves from `framework/` on `PYTHONPATH`.

## 7. Cursor MCP config

Per-repo `.cursor/mcp.json` is **gitignored** (local IDE file). Use the **tracked** template at [.cursor/mcp.json.example](../.cursor/mcp.json.example):

```powershell
Copy-Item .cursor/mcp.json.example .cursor/mcp.json
```

That file matches the tested layout (`uv` + `PYTHONPATH` `${workspaceFolder}/framework`). If you do not use `uv`, edit `.cursor/mcp.json` to use `"command": "python"` and `"args": ["-m", "mcp_server.server"]` with the same `PYTHONPATH` (interpreter must have this repo and MCP deps installed). See [CURSOR_USER_GUIDE.md](CURSOR_USER_GUIDE.md).

**Manual in Cursor:** Settings → MCP → confirm `uipath-builder-agent` connects; invoke a read-only tool (e.g. `uipath_plan_list` with safe scope) once.

## 8. Node: `@uipath/cli` (`uip`)

This is **separate** from the `skills/` submodule (markdown skills vs Node CLI).

```powershell
uip --version
npm list -g @uipath/cli
```

**Expect:** `uip` on PATH; version reported. Upgrade only per team policy: `npm install -g @uipath/cli@latest` (may require corporate proxy/CA configuration).

## 9. Optional: LangGraph / CLI entry

```powershell
uv run python -c "from uipath_claude.graph import graph; print('graph:', type(graph))"
```

**Expect:** import succeeds (uses editable install + `pythonpath` from [pyproject.toml](../pyproject.toml)).

## 10. What this checklist does **not** cover

- **No** `uipcli package deploy` / **no** Production Orchestrator deploy from this doc.
- **No** guarantee that Studio Desktop or `uip rpa` validators are installed; see [INSTALL.md](INSTALL.md).

## Reference docs

- [docs/uiplan/README.md](uiplan/README.md) — UiPlan overview.
- [docs/uiplan/HOW_TO_USE.md](uiplan/HOW_TO_USE.md) — MCP vs CLI vs skill.
- [docs/plans/2026-04-21-uiplan-framework.md](plans/2026-04-21-uiplan-framework.md) — MCP tool matrix.
- [docs/superpowers/plans/2026-04-23-parallel-execution-board.md](superpowers/plans/2026-04-23-parallel-execution-board.md) — regression slices.

## Recorded run (agent verification, 2026-04-23)

These numbers are from one clean checkout run after the Phase 4 + UiPlan merge; re-run locally to refresh.

| Step | Result |
| --- | --- |
| `git submodule update --init --recursive` | OK (nested scaffold templates updated) |
| `uv run python -m uipath_claude.skills.submodule_guard` | OK (`skills` HEAD `11f3ec40…`) |
| Layout (root `uipath_claude` / `mcp_server` / `scripts`) | absent |
| `uv run pytest -q` (full) | `1406 passed`, `8 skipped` |
| `uip --version` | `0.1.21` (machine-dependent) |
| `uv run python -m tools.uiplan generate-docs … --out %TEMP%\…` | wrote `spec.md` / `plan.md` / `tasks.md` |
| `PYTHONPATH=framework` + `import mcp_server.server` | OK |
