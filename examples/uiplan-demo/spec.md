---
name: Example UiPlan Project
overview: "A demonstration of the three-file UiPlan planning contract: spec, plan, and tasks. This example shows how to structure planning documents for UiPath automation projects."
---

# Example UiPlan Project Specification

## Context

This is a demonstration UiPlan bundle that illustrates the structure and conventions for planning UiPath automation work. It serves as a template and reference for new projects using the UiPlan Studio.

## Problem Statement

Organizations need a consistent, machine-readable way to plan automation projects that can be visualized, tracked, and validated throughout the development lifecycle.

## Scope

This example demonstrates:

- **Specification (spec.md)**: Requirements, context, and problem definition
- **Plan (plan.md)**: High-level architecture, decisions, and implementation approach
- **Tasks (tasks.md)**: Concrete, trackable work items with checkboxes and phases

## Requirements

### Functional

- Must provide a clear template structure for all three UiPlan documents
- Must demonstrate proper front-matter formatting with YAML metadata
- Must show the relationship between specification, planning, and task tracking

### Non-Functional

- Documents must be human-readable Markdown
- Must be scannable by the UiPlan Studio Explorer
- Must support progressive disclosure (spec → plan → tasks)

## Constraints

- Files must be named exactly `spec.md`, `plan.md`, and `tasks.md`
- Front matter is required for metadata extraction
- Checkboxes in tasks.md must follow standard Markdown format `[ ]` or `[x]`

## Success Criteria

- All three files are present and valid
- Front matter parses correctly
- Tasks display with correct completion state
- Bundle is discoverable in UiPlan Studio Explorer

## References

- [UiPlan Documentation](../../docs/uiplan/README.md)
- [Planning Framework](../../docs/PLANNING_FRAMEWORK.md)
- [UiPlan Studio Guide](../../docs/uiplan/STUDIO.md)
