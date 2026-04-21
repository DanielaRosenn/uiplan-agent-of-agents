---
slug: template-example
title: Example Implementation Plan
date: YYYY-MM-DD
status: draft            # draft | refining | accepted | rejected | in-progress | done | superseded
owner: your-github-handle
project_type: mixed
linked_pdd: ""
supersedes: null
accepted_at: null        # ISO 8601 timestamp, stamped by uipath_plan_accept
accepted_by: null        # actor label, stamped by uipath_plan_accept
rejection_reason: null   # non-empty when status is rejected
published_at: null       # set by uipath_plan_publish when promoting to docs/plans/
---

# Example Implementation Plan

> For agentic workers: implement task-by-task; use checkboxes below.

**Goal:** One sentence describing the outcome.

**Architecture:** Two or three sentences on approach and boundaries.

## Architecture diagram

```mermaid
flowchart TD
  Start([Start]):::start --> Step[Implement]:::process
  Step --> EndOk(((Done))):::endOk

  classDef start   fill:#ECFDF5,stroke:#10B981,color:#065F46,stroke-width:2px
  classDef process fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:1.25px
  classDef endOk   fill:#ECFDF5,stroke:#10B981,color:#065F46,stroke-width:2px

  linkStyle default stroke:#94A3B8,stroke-width:1.5px
```

## File plan

| Path | Responsibility |
|------|------------------|
| `path/to/file.py` | ... |

## Bite-sized tasks

- [ ] Write or adjust failing test
- [ ] Run test, confirm red
- [ ] Minimal implementation
- [ ] Run `pytest` (or project test command)
- [ ] Update docs if behavior changed
- [ ] Commit with clear message

## Verification

```bash
pytest tests/ -q
```

## Rollback

Revert the commit / delete the branch; note any data migrations separately.
