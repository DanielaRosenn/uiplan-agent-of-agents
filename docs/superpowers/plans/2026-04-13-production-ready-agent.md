# UiPath Builder Agent - Production Ready Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the UiPath Builder Agent production-ready with comprehensive skill picking, proper test coverage, and reliable workflow generation.

**Architecture:** LangGraph-based conversational agent with skill-guided workflow generation, multi-source skill loading, and automatic validation via UiPath CLI.

**Tech Stack:** Python 3.11+, LangGraph, AWS Bedrock (Claude), UiPath CLI (`uip`), pytest, coder-eval

---

## Current State Analysis

### What Works
- Chat mode with skill-guided workflow generation
- File materialization from LLM responses
- Auto-validation with `uip rpa get-errors`
- Auto-fix loop for validation errors
- Multi-source skill loading (official, custom, project-local)
- Slash commands (`/help`, `/status`, `/skills`, `/validate`, etc.)
- Bootstrap flow (BA/SA/Dev/QA)

### Known Gaps
1. **Skill Picking Accuracy** - Needs more triggers and better scoring for edge cases
2. **Integration Service Activities** - XAML IS activities need better documentation
3. **Test Coverage** - Missing coder-eval tests for `uipath-rpa` skill
4. **UI Automation** - Target configuration workflow not fully tested
5. **Excel Activities** - Limited test coverage for Excel workflows

---

## Task 1: Skill Picking Improvements

**Files:**
- Modify: `uipath_claude/cli/app.py:60-200`
- Test: `tests/unit/cli/test_skill_picking_matrix.py`

- [ ] **Step 1: Add Integration Service triggers to skill scoring**

Add IS-related tokens to the scoring logic:

```python
_IS_HINT_TOKENS = {
    "connector", "jira", "salesforce", "servicenow", "slack",
    "integration", "service", "api", "webhook",
}
```

- [ ] **Step 2: Run skill picking tests to verify**

Run: `pytest tests/unit/cli/test_skill_picking_matrix.py -v`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add uipath_claude/cli/app.py tests/unit/cli/test_skill_picking_matrix.py
git commit -m "feat: improve skill picking with IS triggers and comprehensive tests"
```

---

## Task 2: Integration Service XAML Documentation

**Files:**
- Create: `skills/skills/uipath-rpa/references/xaml/integration-service-xaml.md`
- Modify: `skills/skills/uipath-rpa/SKILL.md`

- [ ] **Step 1: Create IS XAML reference document**

Document the correct namespace and activity patterns for IS activities in XAML:

```markdown
# Integration Service Activities in XAML

## Required Namespace

xmlns:uip="clr-namespace:UiPath.IntegrationService.Activities;assembly=UiPath.IntegrationService.Activities"

## Required Package

"UiPath.IntegrationService.Activities": "[1.25.0]"

## When to Use IS Activities vs Mail Activities

- **Mail Activities** (GetOutlookMailMessages, SendOutlookMail): Use for Outlook/Exchange operations
  - Package: UiPath.Mail.Activities
  - Type: System.Net.Mail.MailMessage
  - NO Integration Service namespace needed

- **IS Connector Activities**: Use for third-party connectors (Jira, Salesforce, Slack)
  - Package: UiPath.IntegrationService.Activities
  - Requires connection configuration in Orchestrator
```

- [ ] **Step 2: Update SKILL.md to reference the new document**

Add to Task Navigation table.

- [ ] **Step 3: Commit**

```bash
git add skills/skills/uipath-rpa/references/xaml/integration-service-xaml.md
git add skills/skills/uipath-rpa/SKILL.md
git commit -m "docs: add Integration Service XAML reference"
```

---

## Task 3: Coder-Eval Test Suite for uipath-rpa

**Files:**
- Create: `skills/tests/tasks/uipath-rpa/` (directory with YAML tests)

- [ ] **Step 1: Verify test files exist**

Check that these files were created:
- `outlook_email_workflow.yaml`
- `excel_read_write.yaml`
- `ui_automation_click_type.yaml`
- `logical_if_foreach.yaml`
- `integration_service_connector.yaml`

Run: `ls skills/tests/tasks/uipath-rpa/`
Expected: 5 YAML files

- [ ] **Step 2: Run smoke tests for uipath-rpa**

Run: `cd skills/tests && make test-uipath-rpa`
Expected: Tests execute (may fail initially - that's expected for new tests)

- [ ] **Step 3: Document test results and adjust if needed**

Review output and adjust test criteria if too strict/lenient.

- [ ] **Step 4: Commit**

```bash
git add skills/tests/tasks/uipath-rpa/
git commit -m "test: add coder-eval tests for uipath-rpa skill"
```

---

## Task 4: Pytest Integration Test Suite

**Files:**
- Create: `tests/integration/test_integration_service_workflows.py`
- Modify: `tests/integration/test_chat_skill_picking_outputs.py`

- [ ] **Step 1: Verify IS workflow tests exist**

Run: `pytest tests/integration/test_integration_service_workflows.py -v --collect-only`
Expected: 4 tests collected

- [ ] **Step 2: Run all integration tests**

Run: `pytest tests/integration/ -v -m integration`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/integration/
git commit -m "test: add Integration Service workflow tests"
```

---

## Task 5: Benchmark Documentation

**Files:**
- Modify: `docs/workflow-benchmarks.md`

- [ ] **Step 1: Verify benchmark documentation is complete**

Read: `docs/workflow-benchmarks.md`
Expected: Contains test architecture table, running instructions, debugging checklist

- [ ] **Step 2: Run benchmark tests**

Run: `$env:UIPATH_RUN_BENCHMARKS="1"; pytest tests/integration/test_workflow_benchmarks.py -v`
Expected: All benchmarks pass (requires `uip` CLI)

- [ ] **Step 3: Commit if changes needed**

```bash
git add docs/workflow-benchmarks.md
git commit -m "docs: update benchmark documentation"
```

---

## Task 6: Folder Cleanup

**Files:**
- Move: `docs/reports/*.json` → `archive/reports/`
- Move: `docs/reports/*.md` → `archive/reports/`

- [ ] **Step 1: Verify reports moved to archive**

Run: `ls docs/reports/`
Expected: Empty or only current reports

Run: `ls archive/reports/2026-04-12/`
Expected: Historical reports present

- [ ] **Step 2: Update .gitignore if needed**

Ensure `generated/` and test artifacts are ignored.

- [ ] **Step 3: Commit**

```bash
git add archive/ docs/reports/
git commit -m "chore: archive historical test reports"
```

---

## Task 7: Production Readiness Checklist

- [ ] **Step 1: Verify all unit tests pass**

Run: `pytest tests/unit/ -v`
Expected: All tests pass

- [ ] **Step 2: Verify all integration tests pass**

Run: `pytest tests/integration/ -v -m integration`
Expected: All tests pass

- [ ] **Step 3: Verify skill loading works**

Run: `python -c "from uipath_claude.skills.registry import SkillRegistry; r = SkillRegistry(); print(len(r.load_skills()), 'skills loaded')"`
Expected: 5+ skills loaded

- [ ] **Step 4: Verify chat mode starts**

Run: `uipath-claude chat --no-banner` (then type `exit`)
Expected: Chat session starts without errors

- [ ] **Step 5: Create release tag**

```bash
git tag -a v1.0.0-rc1 -m "Release candidate 1: Production-ready agent"
```

---

## Success Criteria

| Criterion | Target |
|-----------|--------|
| Unit test coverage | >80% |
| Integration tests passing | 100% |
| Skill picking accuracy | >90% for common intents |
| Benchmark validation | All templates pass `uip rpa get-errors` |
| Coder-eval smoke tests | All pass for uipath-rpa |

---

## Next Steps After This Plan

1. **Performance Optimization** - Profile and optimize skill loading
2. **Error Recovery** - Improve auto-fix loop with better error categorization
3. **Multi-Model Support** - Add support for other LLM providers
4. **CI/CD Pipeline** - Set up automated testing on PR
5. **Documentation** - Create user guide and API documentation
