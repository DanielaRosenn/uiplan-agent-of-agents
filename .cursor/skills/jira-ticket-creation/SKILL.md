---
name: jira-ticket-creation
description: Use when drafting Jira Epics, Stories, Tasks, Bugs, or Sub-tasks from requirements, plans, code review findings, documentation gaps, or implementation work. DO NOT TRIGGER: live Jira writes or connector troubleshooting.
---

# Jira Ticket Creation

Draft clear, actionable Jira tickets before creating or updating live Jira issues.

## When to Use

- Convert requirements, specs, PDD/SDD sections, plan tasks, or review findings into Jira tickets.
- Draft bugs, stories, tasks, epics, or subtasks for user review.
- Improve an existing Jira ticket draft.
- Break implementation work into reviewable, testable tickets.

## Critical Rules

1. Draft first. Do not create or update live Jira issues unless the user explicitly asks.
2. One ticket should describe one deliverable or one decision-ready investigation.
3. Make acceptance criteria testable. Avoid vague criteria such as "works correctly".
4. Include context, scope, and verification. Do not bury key requirements in prose.
5. Capture documentation impact when the work changes user behavior, setup, operations, or support
   procedures.
6. Keep summaries short enough to scan in boards and reports.

## Issue Type Decision

| Type | Use When |
| --- | --- |
| Epic | Outcome spans multiple tickets or milestones. |
| Story | User-facing capability or business-value change. |
| Task | Technical, operational, documentation, or enablement work. |
| Bug | Existing behavior is broken, regressed, or contradicts requirements. |
| Sub-task | Concrete implementation step under an approved parent issue. |

## Ticket Template

```markdown
Type: <EPIC|STORY|TASK|BUG|SUB_TASK>
Summary: <ACTION_VERB> <OBJECT> <CONTEXT>
Priority: <CRITICAL|HIGH|MEDIUM|LOW>
Labels: <LABELS>
Components: <COMPONENTS>

## Overview
<One or two sentences describing what needs to change and why.>

## Background
<Relevant requirement, user need, defect context, plan link, PR link, or documentation link.>

## Requirements
- [ ] <Requirement 1>
- [ ] <Requirement 2>
- [ ] <Requirement 3>

## Acceptance Criteria
1. Given <precondition>, when <action>, then <expected result>.
2. Given <edge case>, when <action>, then <expected result>.

## Verification
- <Test, review, command, manual check, or evidence needed for Done.>

## Documentation Impact
- <None, or docs/pages/runbooks/release notes that must be created or updated.>

## Out of Scope
- <Explicit exclusions to prevent scope creep.>
```

## Bug Template Additions

For bugs, include these sections before `Requirements`:

```markdown
## Steps to Reproduce
1. <Step>
2. <Step>
3. <Step>

## Expected Behavior
<What should happen.>

## Actual Behavior
<What happens instead.>

## Environment
<Version, tenant, browser, project, data shape, or other relevant conditions.>
```

## Summary Rules

- Start with an action verb: `Add`, `Fix`, `Update`, `Implement`, `Document`, `Investigate`, or
  `Refactor`.
- Keep under 80 characters when practical.
- Include the affected area: feature, workflow, connector, page, report, or component.
- Avoid vague summaries such as `Fix Jira stuff` or `Improve docs`.

## Development Update Guidance

When drafting Jira updates during development, include only durable signal:

- Completed milestone and evidence.
- Blocker and requested owner/action.
- Scope or design decision.
- Verification result.
- Link to updated documentation, PR, plan, or report.

Do not draft comments for every local edit, temporary failure, or exploratory note.

## Anti-Patterns

- Mixing implementation, rollout, and documentation into one oversized ticket.
- Writing acceptance criteria that cannot be tested.
- Creating a ticket with no owner-action or next step.
- Omitting docs impact for changes that affect users or operators.
- Treating a ticket draft as permission to write to Jira.
