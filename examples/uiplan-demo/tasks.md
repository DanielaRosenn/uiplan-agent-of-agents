---
name: Example UiPlan Project
overview: "Task tracking for the demonstration UiPlan bundle."
---

# Example UiPlan Project Tasks

## Phase 0: Setup

Goal: Establish the bundle structure and validate discoverability.

- [x] Create `examples/uiplan-demo/` directory
- [x] Write `spec.md` with front matter and requirements
- [x] Write `plan.md` with decisions and architecture
- [x] Write `tasks.md` with phase structure
- [ ] Verify bundle appears in UiPlan Studio Explorer
- [ ] Confirm task checkboxes render correctly

## Phase 1: Documentation

Goal: Provide reference documentation for users creating their own bundles.

- [ ] Add comments explaining each section in spec.md
- [ ] Document front-matter schema and required keys
- [ ] Create a `README.md` in examples/ pointing to this bundle
- [ ] Add inline examples of common patterns (Mermaid diagrams, code blocks)

## Phase 2: Validation

Goal: Ensure the bundle works as intended in the product.

- [ ] Load the bundle in UiPlan Studio
- [ ] Verify phase-based visualization in PHASE FLOW view
- [ ] Verify task list in KANBAN view
- [ ] Test task completion state updates
- [ ] Validate metadata extraction (name, overview, progress)

## Phase 3: Cleanup

Goal: Remove obsolete examples and consolidate documentation.

- [ ] Archive old `.cursor/plans/` examples not used by the product
- [ ] Remove stale fixtures from `studio/web/src/__fixtures__/`
- [ ] Update `docs/uiplan/STUDIO.md` to reference this example
- [ ] Document the "one example" decision in the productization plan
