---
name: uiplan-review
description: Wrapper for /uiplan-review feasibility checks and gating.
disable-model-invocation: true
---

# uiplan-review wrapper

Source contract: `.cursor/skills/uiplan/SKILL.md`

Primary tool: `uipath_plan_review` with `stage=all`.

Feasibility checklist:
- Validate implementation paradigm and project structure.
- Verify project discovery context exists and is current.
- Enforce personal workspace deploy default and Production safety language.
- Enforce .NET 8 modern requirement.
- Use `uipath_library_lookup`, `uipath_library_search`, `query_uipath_docs`,
  `uipath_doc_get_activity`, and `uipath_skill_match` for grounded checks.
