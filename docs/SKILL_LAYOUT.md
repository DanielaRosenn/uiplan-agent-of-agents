# Skill folders: what is duplicated and what is not

This repository exposes the same skill catalog to **Cursor** and to the **Python CLI / MCP server** using different mechanisms. Only one directory holds the official catalog; the rest are overlays or runtime code.

## Official catalog (git submodule)

- **`skills/`** — Root of the [UiPath/skills](https://github.com/UiPath/skills) submodule. Do not treat it as “our” Python package; it ships plugin metadata (`.claude-plugin/`), hooks, agents, and the nested catalog.
- **`skills/skills/<name>/`** — Actual `SKILL.md` trees for each UiPath skill. This is the **single copy** of upstream skills in the repo.

## Cursor discovery (not a second copy)

- **`.cursor/skills`** — On Windows this is typically a **junction** pointing at `skills/skills/`. Cursor indexes skills here; it does not duplicate disk usage beyond one directory tree.

## Python skill engine (not skill content)

- **`uipath_claude/skills/`** — Code: `registry.py`, `loader.py`, `sources.py`, `insights.py`, etc. This loads and merges skill roots; it is **not** a folder of `SKILL.md` files.

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
