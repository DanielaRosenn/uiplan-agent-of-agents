# UiPath Planner Local Overlay

This directory documents local behavior patches for `uipath-planner` that extend the upstream skill in `skills/skills/uipath-planner/`.

## Local Changes vs Upstream

Base upstream commit: `0c126220a754da81b9b84e56036182c37f67eeb4` ("Improve testng step in planner (#279)")

### Patch 1: Batched AskUserQuestion

**Step 1**: Batch Q1-Q4 into one `AskUserQuestion` call instead of asking one-at-a-time.

This reduces user interaction overhead and improves chat flow.

### Patch 2: Consolidated Residue Card

**Step 1.5 (new)**: Consolidated residue card for project-shape decisions the planner cannot default or resolve via library/filesystem.

This gathers all unresolved project configuration questions into a single interaction.

### Patch 3: Anti-pattern 18

**Anti-pattern 18 (new)**: Do not ask a question the planner/library/filesystem can answer.

Before any `AskUserQuestion` call, check:
- (a) Is there a safe default?
- (b) Can `uipath_library_search` / `lookup_uipath_knowledge` answer it?
- (c) Does the filesystem probe already tell you?

Only the residue that survives all three gates goes in the batched card.

## Reconciliation on Upstream Bumps

When the submodule is updated:

1. Diff `.cursor/skills/uipath-planner/SKILL.md` (if it still exists) against `skills/skills/uipath-planner/SKILL.md`
2. Merge upstream changes while preserving the three patches above
3. Update this OVERLAY.md with any new deltas
