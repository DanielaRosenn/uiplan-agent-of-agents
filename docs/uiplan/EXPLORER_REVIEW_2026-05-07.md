## Review scope

Subsystem: **UiPlan Studio Explorer + Builder** (`apps/uiplan-studio/` + `services/uiplan-studio-api/` + `framework/uipath_claude/cli/explore.py`) considered through two lenses:

1. Senior software engineer — code health, dead code, tests, security, dependency hygiene.
2. Senior UiPath solution architect — paradigm coverage, skill/library MCP rule compliance, modern-experience compliance, "is this a clean reusable template?".

This is a **review only**. No source code was modified.

---

## 1. Executive summary

1. **P0 secret exposure.** `.env` (committed-status: gitignored, but on disk and 3.7 KB) contains a real `UIPATH_ACCESS_TOKEN` JWT, tenant id, organization id, and an Atlassian connection id. Even though `.env` is in `.gitignore`, the token is sitting on the developer machine in a file the prompt asked us to confirm was non-secret — it is not. Rotate the token immediately, replace `.env` with a copy of `.env.example`, and add a pre-commit guard against `UIPATH_ACCESS_TOKEN=eyJ` patterns.
2. **Iteration A backend is dead.** `app/graph_workspace.py`, `app/graph_indexer.py`, `app/copilot_graph_actions.py`, plus the `/graph/index`, `/graph/context/resolve`, `/graph/actions/execute` and `/agent/chat` routes in `app/main.py` have **zero callers** from the live frontend (`apps/uiplan-studio/src/projectGraph/api.ts`). The only remaining consumer is their own tests. Delete in PR 1.
3. **Iteration A tests should follow the code.** `services/uiplan-studio-api/tests/test_graph_workspace.py` and `tests/test_graph_indexer.py` exist solely to test now-dead modules. The `App.test.tsx` file currently in tree is **not** the broken iteration-A test referenced in the brief — it is an explorer-era test. The "24 failed" tests in the transcript no longer exist on disk.
4. **Repo-root pollution is widespread.** 11 of the 12 named junk files at root (`at.txt`, `full2.txt`, `full_final2.txt`, `_pt_out.txt`, `_pytest_last.txt`, `unit_result.txt`, `verify_unit.txt`, `pytest_run.log`, `debug-7bfa30.log`, `.assistant-choice`) are already gitignored and exist only on this machine; **`input.txt` is the only one actually tracked in git** and must be `git rm`'d. They should still all be deleted from the working tree before this is used as a template.
5. **Frontend e2e is a phantom.** `apps/uiplan-studio/playwright.config.ts` is committed and points at `./e2e`, but no `e2e/` directory exists. Either restore `e2e/project-explorer.spec.ts` from the plan or remove the playwright config + `@playwright/test` devDep.
6. **`apps/uiplan-studio/package.json` lacks `lint`, `typecheck`, and `e2e` scripts**, has no ESLint config, and pins `version: "0.0.0"` (vs `0.1.0` for the API). For a template this needs `lint`, `typecheck`, `test`, `e2e`, `build`, `preview`, plus a coherent version.
7. **`lucide-react@^1.14.0` is correct.** The prompt's hypothesis that this is stale was wrong: `lucide-react` shipped a new major versioning scheme (`1.x` is current as of Apr 2026, latest is 1.14.0 published Apr 29, 2026). Keep as-is, but add a comment in `CHANGELOG.md` so future maintainers don't repeat the assumption.
8. **`Inspector.tsx` at 42 KB / 906 lines is a refactor target.** It mixes 4 tab implementations, citation expansion state, skill-detail loading, and inline styled JSX. Split into `inspector/` subfolder with one file per tab.
9. **UiPath paradigm coverage is partial.** `_detect_project_type()` in `app/explorer.py:200` covers RPA, LangGraph, generic coded agent, LlamaIndex, Solution. Missing: Maestro `*.bpmn`, Coded App `app.config.json`, Case `caseplan.json`, API Workflow `api-workflow.json`, agent.json (low-code agent). For a "full UiPath" template this is a documented gap.
10. **As a template, the repo has too many top-level concerns.** `apps/`, `services/`, `framework/`, `extensions/`, `skills/`, `scaffold/`, `templates/`, `examples/`, `projects/`, `generated/`, `tools/`, `ops/`, `config/`, `data/`, `test-fixtures/`, `.uipath-claude/`, `.uipath/`, `.superpowers/`, `.worktrees/`. A consumer cloning this can't tell what's product vs scaffolding. Recommend a `STRUCTURE.md` and consolidating `projects/` + `generated/` + `examples/` under one `examples/` root.

---

## 2. DELETE

### 2.1 Dead iteration-A backend (consumed only by dead routes)

| Path | Reason |
|---|---|
| `services/uiplan-studio-api/app/graph_workspace.py` | Defines `GraphWorkspaceV2`. Only consumer is `graph_indexer.py` (also dead) and `tests/test_graph_workspace.py`. |
| `services/uiplan-studio-api/app/graph_indexer.py` | Powers `/graph/index`. Frontend never calls `/graph/index` — it calls `/explorer/graph`. |
| `services/uiplan-studio-api/app/copilot_graph_actions.py` | Powers `/graph/actions/execute`. No frontend caller; tests absent. |
| `services/uiplan-studio-api/app/context_resolver.py` | Powers `/graph/context/resolve`. No frontend caller. Verify no MCP tool consumes it; if not, delete. |
| `services/uiplan-studio-api/tests/test_graph_workspace.py` | Tests deleted module. |
| `services/uiplan-studio-api/tests/test_graph_indexer.py` | Tests deleted module. |
| `services/uiplan-studio-api/tests/test_context_resolver.py` | Tests deleted module (only if §2.1 row above is removed). |

After deletion, remove the corresponding imports and routes from `app/main.py`:

- Imports: lines 11 (`context_resolver`), 13 (`copilot_graph_actions`), 39 (`graph_indexer`).
- Route handlers: `graph_index` (`main.py:324-353`), `graph_context_resolve` (`main.py:356-362`), `graph_actions_execute` (`main.py:365-371`).
- Health route entries: `main.py:122-124` (`/graph/index`, `/graph/context/resolve`, `/graph/actions/execute`).
- Schemas: `GraphIndexEdge`, `GraphIndexNode`, `GraphIndexResponse`, `GraphContextResolveRequest`, `GraphActionExecuteRequest` in `main.py:200-209` and `app/schemas.py`.

### 2.2 `/agent/chat` is hardcoded keyword junk

`app/main.py:759-819` `agent_chat()` is a string-match toy that returns one of three hardcoded `DiagramNode` objects depending on whether the user said "skill", "library", or "hitl". The current explorer UI does not call `/agent/chat`. Delete the route, the `AssistantChatRequest`/`AssistantChatResponse` schemas, and any associated tests (search `agent/chat` in `tests/test_main.py`). Replace later with the copilot runtime when the chat surface returns.

### 2.3 Repo-root junk files

All paths relative to repo root:

| File | Status | Action |
|---|---|---|
| `at.txt` | untracked, gitignored | `del` from working tree |
| `full2.txt` | untracked, gitignored | `del` |
| `full_final2.txt` | untracked, gitignored | `del` |
| `_pt_out.txt` | untracked, gitignored | `del` |
| `_pytest_last.txt` | untracked, gitignored | `del` |
| `unit_result.txt` | untracked, gitignored | `del` |
| `verify_unit.txt` | untracked, gitignored | `del` |
| `pytest_run.log` | untracked, gitignored | `del` |
| `debug-7bfa30.log` | untracked, gitignored (`debug-*.log`) | `del` |
| `.assistant-choice` | untracked, gitignored | `del` |
| **`input.txt`** | **TRACKED** | `git rm input.txt` — content is `create an outlook email workflow\nexit`, clearly a chat scratch. |

### 2.4 Frontend e2e remnants (decision required)

- `apps/uiplan-studio/playwright.config.ts` references a non-existent `./e2e` directory.
- `@playwright/test` is in `devDependencies`.
- No `npm run e2e` script.

Pick one of:

- **Restore**: write the `e2e/project-explorer.spec.ts` described in the plan (smoke test: load demo fixture, switch to solution fixture, drill into a node, assert breadcrumb).
- **Remove** (recommended for PR 1, restore later): delete `playwright.config.ts`, drop `@playwright/test` from `devDependencies`.

### 2.5 Sample fixtures: move, do not delete

`apps/uiplan-studio/src/projectGraph/sample.ts` (36 KB, 650+ lines) and `sampleSolution.ts` (13 KB) are demo content shipped inside the production bundle. They should:

- Move to `apps/uiplan-studio/src/__fixtures__/` (still bundled but signposted), OR
- Move to `apps/uiplan-studio/test-fixtures/` and dynamic-import only when `worktreeId in {"demo","solution","empty"}`. Saves ~50 KB from production bundle.

Do not actually delete — `App.test.tsx` and the offline fallback path in `api.ts:46-65` rely on them.

---

## 3. CHANGE

### 3.1 `app/main.py` — slim post-deletion

After §2.1/§2.2 deletions, `main.py` drops from 876 lines to ~600. Further: extract route groups into routers:

```
app/
  routers/
    bundle.py          # /bundle/load, /bundle/save
    diagram.py         # /diagram/load, /diagram/save
    generation.py      # /generate/*, /generation/*
    review.py          # /review/run, /lifecycle/readiness
    context.py         # /context/sources, /agent/library-context, /agent/context-sources
    copilotkit.py      # /copilotkit*
  main.py              # 50-line composition root
```

The `explorer` router is already correctly factored (`app/explorer.py:264`). Mirror that pattern.

### 3.2 `app/explorer.py:272-298` — path traversal hardening

```py
@router.get("/graph", response_model=ExplorerGraphResponse)
def get_project_graph(worktree: str = Query("repo-root")) -> ExplorerGraphResponse:
    ...
    else:
        candidate = Path(worktree)
        if not candidate.is_absolute():
            candidate = (_repo_root() / candidate).resolve()
        if not candidate.is_dir():
            raise HTTPException(status_code=404, detail=f"unknown worktree: {worktree}")
        project_path = candidate
```

Issues:

- The `worktree` query parameter accepts an **absolute path** to any directory on the host, with no allow-list.
- The CLI sets `?worktree=<absolute-project-path>` (`framework/uipath_claude/cli/explore.py:193`), so unrestricted absolute paths are by design — but the API listens on `127.0.0.1` only by default and the CORS origin is locked to `localhost`, so the blast radius is local-only. Still:
- Add an explicit allow-list: union of `{repo_root}` ∪ `{git_worktree.path for ...}` ∪ env-var `UIPATH_EXPLORER_ROOTS` (colon-separated). Reject anything outside.
- Forbid `..` segments, symlink escape (`candidate.resolve()` already collapses, but verify the resolved path is under one of the allowed roots before indexing).

Suggested before/after:

Before (`explorer.py:290-298`):

```py
candidate = Path(worktree)
if not candidate.is_absolute():
    candidate = (_repo_root() / candidate).resolve()
if not candidate.is_dir():
    raise HTTPException(status_code=404, detail=f"unknown worktree: {worktree}")
```

After:

```py
candidate = Path(worktree)
if not candidate.is_absolute():
    candidate = (_repo_root() / candidate).resolve()
else:
    candidate = candidate.resolve()
if not candidate.is_dir():
    raise HTTPException(status_code=404, detail=f"unknown worktree: {worktree}")
allowed = _allowed_roots()                    # repo + git worktrees + UIPATH_EXPLORER_ROOTS
if not any(_is_within(candidate, root) for root in allowed):
    raise HTTPException(status_code=403, detail="worktree path is not in the allow-list")
```

### 3.3 `app/main.py:79` — `PLANS_ROOT` resolution is fragile

```py
PLANS_ROOT = (Path(__file__).resolve().parents[3] / ".cursor" / "plans").resolve()
```

`parents[3]` assumes layout `services/uiplan-studio-api/app/main.py`. When this template is forked into a project that nests the studio differently, the path silently points at a non-existent dir and every `bundle_load` returns 403. Make this configurable via env var with the current value as default, e.g. `UIPLAN_PLANS_ROOT`.

### 3.4 `apps/uiplan-studio/src/App.tsx` — break up the god component

528 lines, all inline styles, 14 `useState` calls, 3 `useEffect`s, 7 `useCallback`s. Refactor:

| Extract to | What |
|---|---|
| `hooks/useProjectGraph.ts` | worktree state, graph load, `loadGraph`, error/loading state. |
| `hooks/useExplorerKeymap.ts` | the keyboard handler at `App.tsx:154-208`. |
| `hooks/useDrilldown.ts` | trail / drillInto / popOne / navigateTo. |
| `components/TopBar.tsx` | the header at `App.tsx:255-353`. |
| `components/StatusBar.tsx` | the footer at `App.tsx:428-451`. |
| `components/EmptyState.tsx`, `LoadingOverlay.tsx` | already inline at `App.tsx:460-512`; promote to files. |
| `theme.ts` styled object literals | Move all 30+ inline `style={{...}}` objects out of JSX into named consts at the bottom of each component or into `theme.ts`. |

Target App.tsx ≤ 150 lines after refactor.

### 3.5 `apps/uiplan-studio/src/components/Inspector.tsx` — split by tab

42 KB / 906 lines. Tabs (`overview`, `code`, `knowledge`, `links`) each have ~150-200 lines of unique logic. Split:

```
components/inspector/
  Inspector.tsx                # tab chrome, shared header, ~120 lines
  OverviewTab.tsx
  CodeTab.tsx
  KnowledgeTab.tsx             # contains CitationItem, SkillItem
  LinksTab.tsx
  CitationItem.tsx
  SkillItem.tsx
```

### 3.6 `apps/uiplan-studio/package.json` — add missing scripts

Before:

```json
"scripts": {
  "dev": "vite",
  "build": "vite build",
  "test": "vitest run"
}
```

After (recommended for a template):

```json
"scripts": {
  "dev": "vite",
  "build": "tsc -b && vite build",
  "preview": "vite preview --host 127.0.0.1 --port 4173",
  "test": "vitest run",
  "test:watch": "vitest",
  "typecheck": "tsc -b --noEmit",
  "lint": "eslint 'src/**/*.{ts,tsx}'",
  "e2e": "playwright test"
}
```

Add `eslint`, `@typescript-eslint/parser`, `@typescript-eslint/eslint-plugin`, `eslint-plugin-react-hooks` to devDeps. Add an `.eslintrc.cjs` and a `tsconfig.json` with `"strict": true` (verify currently set).

### 3.7 `apps/uiplan-studio/src/components/Inspector.tsx:30-35` — fetch error UX

`loadNodeKnowledge`, `loadLibrarySection`, `loadSkillDetail` all swallow errors and return empty arrays. Inspector silently shows "no citations" whether the backend is down or the section genuinely has none. Surface a visible "indexer offline" banner — the same one App.tsx already uses at `App.tsx:400-412`.

### 3.8 `services/uiplan-studio-api/pyproject.toml` — version bump + tighter deps

```toml
[project]
name = "uiplan-studio-api"
version = "0.1.0"           # bump to 0.2.0 after iteration-A removal
dependencies = [
    "fastapi[standard]",     # pin to a major: "fastapi[standard]>=0.115,<1"
    "uvicorn",               # pin to >=0.30,<1
    "pyyaml",                # pin >=6,<7
    "copilotkit>=0.1.88",
]
```

If `copilotkit` is only used by the (also vestigial) `/copilotkit*` routes and the runtime is not yet wired into the explorer UI, consider gating the import behind a feature flag and dropping the dep until the chat surface comes back.

### 3.9 `framework/uipath_claude/cli/explore.py` — process management

Issues found:

- `explore.py:189-191` runs `npm run dev` with `shell=True` on Windows. `npm run dev -- --port` arg-passing through cmd.exe shell is fragile. Switch to launching `node node_modules/vite/bin/vite.js` directly (or use `npm.cmd` explicitly with `shell=False`).
- `explore.py:215-227` cleanup loop on Ctrl-C: `signal.CTRL_BREAK_EVENT` only works on processes started with `creationflags=subprocess.CREATE_NEW_PROCESS_GROUP`. The current `Popen` calls do **not** set that flag, so on Windows the CTRL_BREAK signal is broadcast to the parent process group and may kill the calling shell. Add `creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0`.
- `explore.py:181-184` exits if backend doesn't bind in 20s but doesn't read backend stdout/stderr — debugging a slow boot requires a `--verbose` flag and forwarding child output.
- `explore.py:67-74` mutates `sys.path` with `sys.path.insert(0, …)` and the `try/finally` does nothing. Drop the no-op finally.

### 3.10 `apps/uiplan-studio/src/projectGraph/api.ts:5-6` — boot-time API URL

```ts
const API_BASE = (import.meta.env?.VITE_UIPLAN_API_URL as string | undefined)?.replace(/\/$/, "")
  ?? "http://localhost:8000";
```

Two issues:

1. `localhost` vs `127.0.0.1`: the CLI passes `http://127.0.0.1:<port>` (`explore.py:166`) but the default falls back to `http://localhost:8000`. CORS in `main.py:69-75` allows both, so it works, but the hard-coded `8000` is a mismatch when the CLI auto-picks a free port. The studio served from `npm run dev` (no CLI) will hit a stale 8000. Document this.
2. The CLI route uses `?worktree=<absolute-path>`. `App.tsx:24-32` reads it from `window.location.search`, which is right, but `loadProjectGraph()` then URL-encodes it again — double-encoding for paths with spaces. Verify with a path containing a space: `C:\Users\Daniela Rosenstein\proj` round-trips correctly.

---

## 4. ADJUST (template hardening)

### 4.1 Repo root cleanup

After §2.3 deletions, root should contain:

```
.gitattributes  .gitignore  .gitmodules
.cursor/  .github/  .githooks/  .vscode/
apps/  services/  framework/  extensions/  skills/
config/  data/  docs/  examples/  ops/  test-fixtures/  tools/
templates/  scaffold/                     # see §4.2
.env.example  CHANGELOG.md  CLAUDE.md  CONTRIBUTING.md  README.md  QUICKSTART.md
langgraph.json  pyproject.toml  uv.lock  run_evals.py
```

Hide `.skills_refresh_at`, `.skills_session_refresh`, `.assistant-choice` behind `.uipath-claude/` (they are internal markers, not template content).

### 4.2 Top-level dir consolidation

| Current | Proposed |
|---|---|
| `apps/` | keep (consumer-facing surfaces) |
| `services/` | keep |
| `framework/` | keep (Python core) |
| `extensions/` | keep (skill overrides) |
| `skills/` | keep (submodule) |
| `scaffold/` | merge into `templates/scaffold/` |
| `templates/` | keep (project starter templates) |
| `examples/` | keep — move `projects/`, `generated/` content into `examples/` |
| `projects/` | **delete** (already gitignored at root) |
| `generated/` | **delete** (already gitignored at root) |
| `tools/` | keep (build/CI helpers) |
| `ops/` | merge into `tools/ops/` |
| `config/` | review — likely reusable |
| `data/` | keep (library content) |
| `test-fixtures/` | keep |

Add a top-level `STRUCTURE.md` (≤ 80 lines) that describes the role of each dir for someone forking the template.

### 4.3 `CLAUDE.md` is 26 KB — split

Currently `CLAUDE.md` is the AI-assistant rule. It is referenced from `.cursor/rules/uipath.mdc` and several skills. Length is acceptable for a rules doc, but for a **template** consumer it is intimidating. Recommend:

- Keep `CLAUDE.md` as-is (it is the entry point for AI assistants, must be readable in one shot).
- Add a 3-4 KB `README.md` template section "What is this template?" pointing at `CLAUDE.md` for AI-assistant rules and `QUICKSTART.md` for humans.
- Move the §14 "Verification trail" out of `CLAUDE.md` into `docs/uipath-stack-verification.md`. It's audit metadata, not rules.

### 4.4 `.env` handling

- Replace the on-disk `.env` with `cp .env.example .env`, then **rotate the JWT** in `UIPATH_ACCESS_TOKEN` and the connection id. Treat anything in the current `.env` as compromised.
- Add a pre-commit hook entry in `.githooks/` that rejects `git add` on any path matching `\.env$` (without `.example` suffix).
- Add a CI job (`.github/workflows/secret-scan.yml`) running `gitleaks` against pushes.

### 4.5 Versioning

| Component | Current | Proposed |
|---|---|---|
| `apps/uiplan-studio/package.json` | `0.0.0` | `0.2.0` |
| `services/uiplan-studio-api/pyproject.toml` | `0.1.0` | `0.2.0` |
| Repo root | (no shared version) | publish a `VERSION` file at root and reference both |

### 4.6 `.uiplan/explorer.yaml` starter wiring

`app/explorer.py:402-428` writes a starter `explorer.yaml` + `annotations.yaml`. For a template, a **commented sample `explorer.yaml`** should ship at `templates/uiplan/explorer.yaml.example` so a forking project can `cp` it without booting the studio. Document in `docs/uiplan/EXPLORER.md` §"Wiring into a new project".

---

## 5. UiPath-architect findings

### 5.1 Paradigm coverage

`app/explorer.py:200-214` `_detect_project_type()` covers:

- LangGraph (`langgraph.json`)
- Generic coded agent (`agent_framework.json`)
- LlamaIndex (`llama_index.json`)
- Solution (`solution.uipx`)
- RPA (`*.uiproj` or `project.json`)

**Missing markers** (per `CLAUDE.md` §1):

| Project type | Marker | Add to `_detect_project_type` |
|---|---|---|
| Maestro process | `*.bpmn` files | `if any(path.glob("**/*.bpmn")): return "maestro"` |
| Coded App | `app.config.json` + `action-schema.json` | check both |
| Coded Action App | `action-schema.json` alone | |
| API Workflow | `api-workflow.json` or `ApiWorkflow` in `project.json:projectType` | |
| Case Management | `caseplan.json` | |
| Low-code agent | `agent.json` from Agent Builder | |

Also: the explorer graph layer set `SUPPORTED_LAYERS = ("ui","api","agent","rpa","maestro","app","orchestrator","test","external")` (`explorer_indexer.py:29`) is fine but the indexer itself does not produce `maestro`/`app`/`orchestrator` nodes from project content — the only `.bpmn`/`app.config.json` content path is the sample fixture. File: `explorer_indexer.py` needs handlers for those file types.

### 5.2 Modern-experience compliance

Searched fixtures (`apps/uiplan-studio/src/projectGraph/sample.ts`, `sampleSolution.ts`) for `Classic`, `VB.Net`, `Windows-Legacy`, `targetFramework` — **clean, no matches**. Sample data is modern-experience consistent.

### 5.3 Skill / library MCP rule compliance

Per `.cursor/rules/library-tools.mdc`: never read `data/library/`, `skills/skills/`, or `skills/references/activity-docs/` directly to answer a user question — go through `uipath_library_*` / `uipath_skill_*` tools.

Findings:

- `app/library_service.py:50-63` reads through `uipath_claude.library.catalog.LibraryCatalog` and `LibraryReader`. **Compliant** — that is the same plumbing the MCP tool uses; raw `data/library/` reads are absent (grep returned no matches).
- `app/explorer_skills.py:36-48` reads through `uipath_claude.skills.registry.SkillRegistry`. **Compliant** for skill listing.
- `app/explorer_skills.py:51-72` `read_skill_detail` reads `SKILL.md` body via `path.read_text(...)` after the registry resolves the path. This is acceptable because the registry already enforces the submodule guard, but recommend wrapping in a helper that asserts the path is under the approved skills tree before reading.
- `app/explorer.py:244-256` `_read_library_section` re-uses the framework `LibraryReader`. Compliant.

**Submodule guard:** `CLAUDE.md` §0a requires the `python -m uipath_claude.skills.submodule_guard` check. The explorer does not invoke this on every request. Acceptable for a per-request hot path, but `explore.py` should call the guard once at boot before importing skill modules.

### 5.4 Security posture

| Risk | Where | Severity |
|---|---|---|
| Live JWT in `.env` | `.env:1` | **P0** — rotate now |
| Unbounded `?worktree=<path>` | `app/explorer.py:290-298` | P2 (localhost-bound, no auth, but can index any dir) |
| `subprocess.check_output(["git", ...], cwd=..., timeout=3)` | `app/explorer.py:156-163`, `188-194` | P3 — safe; `cwd` is a `Path`, no user input on argv |
| `_PENDING_GENERATION_PREVIEWS` in-process dict | `app/main.py:82` | P3 — already documented (`/health` `metadata.preview_store`); fine for single-worker dev, must be Redis/SQLite for prod |
| CORS wide-open on localhost | `app/main.py:69-75` | P3 — accepts any port on `localhost`/`127.0.0.1`; acceptable for dev; tighten to `VITE_UIPLAN_API_URL` origin in prod |
| No auth on any explorer route | all `/explorer/*` | P3 — by design (local), but document in EXPLORER.md |

### 5.5 Misc UiPath-architect notes

- `app/explorer_skills.py` aggregates skill coverage at the **project graph** level. Worth surfacing in `docs/uiplan/EXPLORER.md` as the answer to "what skill explains this project?" — current docs don't sell this feature.
- `code_extractor.py:1-end` (11 KB) handles Python/TS/TSX/XAML and emits "concept" explanations. For UiPath, XAML is the most important — verify the parser handles `Sequence`, `If`, `WhileDo`, `InvokeWorkflowFile`, `Switch`. (Did not deep-read; 11 KB is reasonable for a heuristic.)

---

## 6. Risks & open questions

1. **Did the iteration-A `App.test.tsx` ever actually exist?** The current `App.test.tsx` (4 KB, 113 lines) is the explorer-era test, all green against current code. The transcript's "24 failed in App.test.tsx" appears to refer to a transient state already resolved. Confirm by running `npm test` before deletion of any "broken" test.
2. **Is `/copilotkit*` actually wired anywhere from the current explorer UI?** I did not find a frontend caller. If unused, all of `app/copilot_runtime.py` (22 KB!) is dead code. Verify before deleting — chat surface may return.
3. **`framework/uipath_claude/library/catalog.py` and `reader.py`** — not reviewed in depth. Compliance with MCP rule depends on these implementations. Worth a separate review.
4. **`config/`, `ops/`, `data/` contents** — not enumerated; presumed reusable. Review separately.
5. **`extensions/skills/`** — referenced by `CLAUDE.md` §0a but not exercised in this review.
6. **Lucide-react `^1.14.0`** — verified as the current latest (Apr 2026). The brief's claim that this is stale was **incorrect**; document this in `CHANGELOG.md` to prevent re-investigation.
7. **The plan references `e2e/project-explorer.spec.ts`** — file does not exist on disk, only `playwright.config.ts` does. Cannot review what isn't there.

---

## 7. Suggested 3-PR sequence

### PR 1 — Dead-code removal (safe, additive ↓)

- Delete `app/graph_workspace.py`, `app/graph_indexer.py`, `app/copilot_graph_actions.py`, `app/context_resolver.py` and their tests.
- Remove `/graph/index`, `/graph/context/resolve`, `/graph/actions/execute`, `/agent/chat` routes from `app/main.py` (and their request schemas).
- Delete `playwright.config.ts` and drop `@playwright/test` dep (or restore the e2e spec — pick one).
- Remove `tests/test_main.py` cases that hit deleted endpoints.
- `git rm input.txt`. Delete the 10 untracked junk files at repo root.
- Acceptance: `pytest` in `services/uiplan-studio-api/` is green; `npm test` in `apps/uiplan-studio/` is green; `uipath-claude explore --check` still works.

### PR 2 — Template hygiene + security

- Rotate the JWT in `.env`. Replace `.env` with `cp .env.example .env` (assumes that is gitignored — verified).
- Add `gitleaks` CI workflow + pre-commit hook for `.env` and JWT patterns.
- Bump `apps/uiplan-studio/package.json` to `0.2.0`; sync `pyproject.toml` to `0.2.0`.
- Add `lint`, `typecheck`, `e2e`, `preview` scripts; add `.eslintrc.cjs`; add ESLint devDeps.
- Add `STRUCTURE.md`. Move `_pt_out`, `_pytest_last`, `unit_result`, `verify_unit`, etc. patterns into a single `local-scratch/` block in `.gitignore`.
- Move `apps/uiplan-studio/src/projectGraph/sample{,Solution}.ts` to `src/__fixtures__/` and dynamic-import.
- Acceptance: every script in `package.json` runs successfully; secret-scan CI passes; no JWT in any working-tree file.

### PR 3 — Refactors + paradigm coverage

- Split `app/main.py` into routers (`bundle.py`, `diagram.py`, `generation.py`, `review.py`, `context.py`, `copilotkit.py`).
- Split `Inspector.tsx` into `components/inspector/` per-tab files.
- Extract `App.tsx` hooks (`useProjectGraph`, `useExplorerKeymap`, `useDrilldown`).
- Extend `_detect_project_type()` to cover Maestro `.bpmn`, Coded App `app.config.json`, Case `caseplan.json`, API Workflow, low-code `agent.json`.
- Add `explorer_indexer.py` handlers for `.bpmn` and `app.config.json`.
- Harden `app/explorer.py:290-298` worktree allow-list.
- Make `PLANS_ROOT` configurable via `UIPLAN_PLANS_ROOT`.
- Fix `explore.py` Windows process-group flag and `npm` shell quoting.
- Acceptance: all existing tests green; new tests for paradigm detection; manual smoke test with a Solution + a Maestro BPMN fixture.
