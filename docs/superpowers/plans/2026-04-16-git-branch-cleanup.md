# Git Branch Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate the repository to a single `main` branch by safely removing merged feature branches and pushing all local work to remote.

**Architecture:** Sequential git operations: commit uncommitted work, push main to origin, delete merged local branches, delete merged remote branch.

**Tech Stack:** Git CLI

---

## Repository policy (test projects)

- Do **not** commit or push full UiPath test or solution trees (for example `.xaml`, `.uiproj`, `Main.xaml`, `Workflows/`, or other project folders under `tests/fixtures/sample_project/`).
- The repo keeps only the minimal tracked fixture `tests/fixtures/sample_project/project.json` for automated tests.
- Any extra files created by opening the sample in Studio or by local runs are **local-only**: delete them from disk when cleaning up, and rely on `.gitignore` so they never enter git history.

---

## Pre-Flight Summary

| Branch | Commit | Merge Status |
|--------|--------|--------------|
| `main` | `440ad21` | Current HEAD, 43 commits ahead of origin |
| `feature/adaptive-validation-sync` | `51e3a8c` | Fully merged into main |
| `feature/hermes-core-controls` | `08db6b6` | Fully merged into main |
| `sprint-1-foundation` | `43dddc5` | Fully merged into main |
| `origin/feature/adaptive-validation-sync` | remote | Fully merged into main |

**Uncommitted changes:** 33 modified files, 67+ untracked files/directories

---

### Task 1: Stage and Commit All Uncommitted Work

**Files:**
- Modify: Working directory (staging all changes)

- [ ] **Step 1: Review what will be committed**

Run: `git status --short`

Expected output: List of M (modified), D (deleted), and ?? (untracked) files

- [ ] **Step 2: Stage all tracked file changes**

```powershell
git add -u
```

This stages all modifications and deletions to tracked files.

- [ ] **Step 3: Verify staged changes**

Run: `git status --short`

Expected: Modified/deleted files now show as staged (first column has letter)

- [ ] **Step 4: Commit tracked file changes**

```powershell
git commit -m "chore: batch commit of evaluation, test, and documentation updates"
```

Expected: Commit created successfully

- [ ] **Step 5: Verify commit**

Run: `git log -1 --oneline`

Expected: New commit hash with message "chore: batch commit..."

---

### Task 2: Stage and Commit Untracked Files (Selective)

**Files:**
- Create: Various new files being tracked

**Do not add:** Anything under `tests/fixtures/sample_project/` except the already-tracked `project.json` (see **Repository policy**). Never stage full UiPath test projects.

- [ ] **Step 1: Review untracked files**

Run: `git status --short | Select-String "^\?\?"`

Expected: List of untracked files/directories

- [ ] **Step 2: Add documentation and source files**

```powershell
git add docs/CURSOR_USER_GUIDE.md
git add docs/DEPLOYMENT_INTEGRATION.md
git add docs/MANUAL_EVAL_AND_QA.md
git add docs/Testing_Guide.md
git add docs/evaluations/README.md
git add docs/superpowers/plans/
git add README_DEPLOYMENT.md
git add scripts/setup-cursor.ps1
git add scripts/setup-cursor.sh
```

- [ ] **Step 3: Add new source code files**

```powershell
git add uipath_claude/evaluation/eval_skill_prompt.py
git add uipath_claude/tools/deploy_tool.py
git add uipath_claude/utils/
git add tests/unit/query/test_intent_classifier.py
git add tests/unit/query/test_tool_return_inference.py
git add tests/unit/rendering/test_agentic_progress.py
git add tests/unit/utils/
```

- [ ] **Step 4: Commit new files**

```powershell
git commit -m "feat: add deployment tooling, cursor setup scripts, and new test coverage"
```

Expected: Commit created successfully

- [ ] **Step 5: Verify commit**

Run: `git log -1 --oneline`

Expected: New commit with message "feat: add deployment tooling..."

---

### Task 3: Handle Generated/Local-Only Content

**Files:**
- Modify: `.gitignore`
- Delete: Everything under `tests/fixtures/sample_project/` except `tests/fixtures/sample_project/project.json`

- [ ] **Step 1: Verify these paths should NOT be committed**

The following are generated/local-only and should remain untracked (or deleted locally):
- `.cursor/` - IDE settings
- `.uipath-claude/` - Local runtime data
- `.uipath/` - Local UiPath data
- `HelloWorld/` - Generated project
- `docs/evaluations/results/` - Test run outputs
- `evaluation_results.json` / `evaluation_results_smoke.json` - Test run outputs
- `docs/~$Chat_UX_Test_Cases.xlsx` - Excel temp file
- Full UiPath trees under `tests/fixtures/sample_project/` (see **Repository policy** above); only `project.json` is tracked

- [ ] **Step 2: Delete local test project files under the sample fixture**

Keep the single tracked file `tests/fixtures/sample_project/project.json`. Remove all other files and directories next to it (safe to delete; they must not be pushed).

```powershell
Get-ChildItem -LiteralPath "tests/fixtures/sample_project" -Force |
  Where-Object { $_.Name -ne "project.json" } |
  ForEach-Object { Remove-Item -LiteralPath $_.FullName -Recurse -Force }
```

Run: `dir tests\fixtures\sample_project`

Expected: Only `project.json` is listed.

- [ ] **Step 3: Ensure `.gitignore` blocks future test projects**

Confirm `.gitignore` contains exactly these lines (add or adjust if missing):

```
# Sample UiPath test project: keep only tracked project.json; never commit full projects
tests/fixtures/sample_project/*
!tests/fixtures/sample_project/project.json
```

- [ ] **Step 4: Confirm gitignore covers local-only paths**

Run:

```powershell
git check-ignore -v .cursor .uipath-claude .uipath HelloWorld evaluation_results.json
git check-ignore -v tests/fixtures/sample_project/Main.xaml
git check-ignore -v tests/fixtures/sample_project/project.json; if ($LASTEXITCODE -eq 0) { Write-Error "project.json must NOT be ignored" }
```

Expected: The first two commands list ignore rules for each path. `Main.xaml` is ignored. `git check-ignore` for `project.json` exits non-zero (file is not ignored).

- [ ] **Step 5: Commit gitignore updates if changed**

```powershell
git add .gitignore
git diff --cached --quiet .gitignore; if ($LASTEXITCODE -ne 0) { git commit -m "chore: ignore sample UiPath test projects; keep project.json only" }
```

Expected: Commit created if `.gitignore` changed, otherwise no action

---

### Task 4: Push Main Branch to Origin

**Files:**
- None (remote operation)

- [ ] **Step 1: Verify main is ahead of origin**

Run: `git status`

Expected: "Your branch is ahead of 'origin/main' by N commits"

- [ ] **Step 2: Push main to origin**

```powershell
git push origin main
```

Expected: Push succeeds, showing commits transferred

- [ ] **Step 3: Verify push succeeded**

Run: `git status`

Expected: "Your branch is up to date with 'origin/main'"

---

### Task 5: Delete Merged Local Branches

**Files:**
- None (branch references only)

- [ ] **Step 1: Verify branches are fully merged**

```powershell
git branch --merged main
```

Expected output includes:
- `feature/adaptive-validation-sync`
- `feature/hermes-core-controls`
- `sprint-1-foundation`

- [ ] **Step 2: Delete feature/adaptive-validation-sync**

```powershell
git branch -d feature/adaptive-validation-sync
```

Expected: "Deleted branch feature/adaptive-validation-sync (was 51e3a8c)"

- [ ] **Step 3: Delete feature/hermes-core-controls**

```powershell
git branch -d feature/hermes-core-controls
```

Expected: "Deleted branch feature/hermes-core-controls (was 08db6b6)"

- [ ] **Step 4: Delete sprint-1-foundation**

```powershell
git branch -d sprint-1-foundation
```

Expected: "Deleted branch sprint-1-foundation (was 43dddc5)"

- [ ] **Step 5: Verify only main remains**

Run: `git branch`

Expected output:
```
* main
```

---

### Task 6: Delete Merged Remote Branches

**Files:**
- None (remote branch references)

- [ ] **Step 1: Check remote branches**

Run: `git branch -r`

Expected output includes:
- `origin/HEAD -> origin/main`
- `origin/feature/adaptive-validation-sync`
- `origin/main`

- [ ] **Step 2: Delete remote feature/adaptive-validation-sync**

```powershell
git push origin --delete feature/adaptive-validation-sync
```

Expected: "- [deleted] feature/adaptive-validation-sync"

- [ ] **Step 3: Prune stale remote-tracking references**

```powershell
git fetch --prune
```

Expected: Any stale references removed

- [ ] **Step 4: Verify remote branches**

Run: `git branch -r`

Expected output:
```
origin/HEAD -> origin/main
origin/main
```

---

### Task 7: Final Verification

**Files:**
- None (verification only)

- [ ] **Step 1: Verify all branches**

Run: `git branch -a`

Expected output:
```
* main
  remotes/origin/HEAD -> origin/main
  remotes/origin/main
```

- [ ] **Step 2: Verify no worktrees**

Run: `git worktree list`

Expected output (single worktree):
```
C:/Users/DanielaRosenstein/projects/uipath-builder-agent <hash> [main]
```

- [ ] **Step 3: Verify clean working directory (except intentionally untracked)**

Run: `git status`

Expected: Either "working tree clean" or only shows intentionally untracked local files

- [ ] **Step 4: Final commit log review**

Run: `git log --oneline -5`

Expected: Recent commits visible, main branch up to date

---

## Rollback Procedures

If anything goes wrong:

**Restore deleted local branch:**
```powershell
git branch <branch-name> <commit-hash>
# Example: git branch feature/adaptive-validation-sync 51e3a8c
```

**Restore deleted remote branch (if you have the commit locally):**
```powershell
git push origin <commit-hash>:refs/heads/<branch-name>
# Example: git push origin 51e3a8c:refs/heads/feature/adaptive-validation-sync
```

**Undo last commit (keep changes staged):**
```powershell
git reset --soft HEAD~1
```

---

## Summary

After completing all tasks:
- Single `main` branch locally and on origin
- All uncommitted work preserved in commits
- All merged feature branch content preserved in main's history
- Local-only/generated files properly gitignored
- Clean repository state
