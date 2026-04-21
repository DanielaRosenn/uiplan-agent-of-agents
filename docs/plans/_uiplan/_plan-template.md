# Implementation Plan: {{TITLE}}

> **Grounding:** {{GROUNDING_CITATIONS}}
> **Spec:** `./spec.md`

**Date**: {{DATE}}
**Spec**: ./spec.md

## Summary

{{SUMMARY}}

## Technical Context

**Language/Version**: {{LANG_VERSION}}
**Primary Dependencies**: {{DEPS}}
**Storage**: {{STORAGE}}
**Testing**: {{TESTING}}
**Target Platform**: {{TARGET_PLATFORM}}
**Project Type**: {{PROJECT_TYPE}}
**Performance Goals**: {{PERF}}
**Constraints**: {{CONSTRAINTS}}
**Scale/Scope**: {{SCALE}}

## Constitution Check

Gates re-checked after Phase 1 design:

{{CONSTITUTION_CHECKLIST}}

## Project Structure

### Documentation (this feature)

```text
.cursor/plans/{{FOLDER_NAME}}/
  spec.md
  plan.md
  tasks.md
  .meta.yaml
```

### Source Code (repository root)

```text
{{SOURCE_TREE}}
```

**Structure Decision**: {{STRUCTURE_DECISION}}

## Activity references (optional)

`uipath_plan_tasks_new` resolves activity documentation for explicit tags in **plan.md** or **spec.md** (up to 8 unique pairs). Use the package id and activity name as in Studio:

`[activity:UiPath.System.Activities:LogMessage]`

`[activity:UiPath.Mail.Activities:SendMail]`

## Complexity Tracking

{{COMPLEXITY_TABLE}}
