---
name: uipath-interact
description: "[PREVIEW] Inspect and interact with live desktop/browser apps using the UiPath UIA CLI. Use for screenshots, click/type actions, reading UI state, and post-build verification. Do not use for workflow authoring."
allowed-tools: Bash(uip:*), Read, Grep
---

# UI Interaction

Use this skill for live desktop/browser inspection and interaction only:
screenshots, snapshots, reading UI state, click/type actions, and post-build
verification.

For creating or editing workflows, configuring Object Repository targets, or
fixing selectors, use `uipath-rpa`.

## Entry Procedure

Read and follow the official skill from the UiPath skills submodule:

`skills/skills/uipath-interact/SKILL.md`

That skill delegates UIA-version-specific details to the installed package docs
under `.local/docs/packages/UiPath.UIAutomation.Activities/`.
