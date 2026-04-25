# Skill folders: what is duplicated and what is not

This repository exposes the same skill catalog to **Cursor** and to the **Python CLI / MCP server** using different mechanisms. Only one directory holds the official catalog; the rest are overlays or runtime code.

## Official catalog (git submodule)

- **`skills/`** — Root of the [UiPath/skills](https://github.com/UiPath/skills) submodule. Do not treat it as “our” Python package; it ships plugin metadata (`.claude-plugin/`), hooks, agents, and the nested catalog.
- **`skills/skills/<name>/`** — Actual `SKILL.md` trees for each UiPath skill. This is the **single copy** of upstream skills in the repo.

## Cursor discovery (not a second copy)

- **`.cursor/skills`** — On Windows this is typically a **junction** pointing at `skills/skills/`. Cursor indexes skills here; it does not duplicate disk usage beyond one directory tree.
- If `ops/scripts/setup-cursor.ps1` fell back to a **recursive copy** (junction creation failed), `.cursor/skills` is a **separate tree**. After every `git pull` or submodule advance, re-run **`ops/scripts/setup-cursor.ps1 -Force`** so Cursor sees new upstream `SKILL.md` files. Junction mode does not need this.

## Monitoring upstream (already wired)

- **Canonical content** lives only in the **`skills/` git submodule** (`skills/skills/<name>/`). Commit hash is pinned for reproducibility; see `.uipath/skills-approved.sha` and `python -m uipath_claude.skills.submodule_guard`.
- **SessionStart hook** (repo root `.cursor/hooks.json`) runs **`.cursor/hooks/check-skills-update.ps1`**: at most every few days it checks whether the submodule is behind `origin/main` and prints a **banner** suggesting `/update-skills` or `ops/scripts/update-skills.ps1`. It does not auto-pull (that would be unsafe without review).
- **Claude Code / `uip` session** uses the submodule’s **`skills/hooks/hooks.json`** (e.g. `ensure-uip.sh`) for npm-based tooling, not for copying skill markdown into `.cursor/`.

## Knowledge library (not under `.cursor/`)

- **`data/library/`** — Curated **content**: `catalog.yaml`, `books/<id>/…` markdown. MCP tools `uipath_library_*` read from here by default (`UIPATH_CLAUDE_LIBRARY` overrides the root). This is **not** the Cursor config folder; it is normal repo data.
- **`framework/uipath_claude/library/`** — **Python code** for that feature (`catalog.py`, `harvest.py`, `reader.py`, …). It lives under `framework/` with the rest of `uipath_claude` because the MCP server and CLI import it as `uipath_claude.library`. Same pattern as `framework/uipath_claude/skills/` (code) vs `skills/` (markdown submodule).

## Python skill engine (not skill content)

- **`framework/uipath_claude/skills/`** — Code: `registry.py`, `loader.py`, `sources.py`, `insights.py`, etc. This loads and merges skill roots; it is **not** a folder of `SKILL.md` files.

## `extensions/` at repo root (purpose and structure)

The **`extensions/`** directory groups **git-tracked, team-owned material** that is not the UiPath submodule and not Cursor-only config:

| Path | Role |
| --- | --- |
| **`extensions/skills/`** | Team skill overlays. Loaded by `build_skill_sources` **after** user/project paths and **before** `skills/skills/`, so same skill name can override upstream. See `extensions/skills/README.md`. |
| **`extensions/skill-insights/`** | Curated PR-reviewed insight JSON (vs raw captures under `.uipath-claude/skill-insights/`). See `extensions/skill-insights/README.md` and `framework/uipath_claude/skills/insights.py`. |
| **`extensions/uipath-rule-bundle/`** | A **portable drop-in kit** (CLAUDE.md, `.cursor/rules`, docs, hooks, optional zip) for other UiPath repos—not consumed as Python imports by this builder. Duplicate of patterns at repo root by design. |

**Should it merge into another folder?** Generally **no**. Moving overlays under `.cursor/` would mix **editor config** with **versioned team extensions**; moving them into `skills/` would violate the submodule boundary. The layout matches `sources.py` (`project_root / "extensions" / "skills"`) and migration notes that keep `skills/` + `extensions/` top-level to reduce risk (`docs/superpowers/specs/2026-04-23-framework-structure-migration-design.md`). Optional future cleanup: a short `extensions/README.md` index file if the tree grows.

## Team and local overlays

- **`extensions/skills/`** — Optional team-authored skills (may be empty; see `extensions/skills/README.md`).
- **`.uipath-claude/skills/`** — Optional per-checkout overrides (often gitignored; see `uipath_claude/skills/sources.py`).
- **`~/.cursor/skills/`** — User-wide overrides on the machine running the agent.

## Merge order (first wins on name collision)

Implemented in `uipath_claude.skills.sources.build_skill_sources`:

1. Paths from `.uipath-claude/config.yaml` `skills.sources` (if present), each as `project` origin  
2. `~/.cursor/skills` (`user`)  
3. `.uipath-claude/skills` (`project`)  
4. `extensions/skills` (`extensions`)  
5. `skills/skills` (`uipath-submodule`)  
6. Optional template paths when `UIPATH_INCLUDE_TEMPLATE_SKILLS=1`

## Skill insights (separate from skill markdown)

- **`.uipath-claude/skill-insights/`** — Auto-captured or machine-local insight JSON.
- **`extensions/skill-insights/`** — Curated team insights promoted via PR (see `extensions/skill-insights/README.md`).

## MCP vs LangGraph “tools”

- **`mcp_server/tools/`** — MCP tool handlers wired to `SkillRegistry` and related classes.
- **`uipath_claude/tools/`** — LangChain/LangGraph tool wrappers for the same product features.

Naming overlap (`skill_tools`, `doc_tools`) reflects two transport surfaces, not two copies of the skill files on disk.
