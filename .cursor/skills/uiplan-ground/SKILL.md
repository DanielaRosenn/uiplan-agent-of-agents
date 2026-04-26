---
name: uiplan-ground
description: Build a read-only UiPlan grounding pack for a topic.
disable-model-invocation: true
---

# UiPlan Ground

Use `.cursor/skills/uiplan/SKILL.md` as the canonical contract.

Treat the user's text after `/uiplan-ground` as the topic. Run
`uipath_plan_ground` to collect project context, matched skills, library hits,
PDD candidates, and constitution gates.

This is read-only. Do not create plan files or implementation changes from this
command.
