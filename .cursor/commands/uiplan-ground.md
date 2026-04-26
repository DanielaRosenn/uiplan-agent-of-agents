---
name: uiplan-ground
description: Build a read-only UiPlan grounding pack for a topic.
---

# UiPlan Ground

Use `.cursor/skills/uiplan/SKILL.md` and `@docs/uiplan/` as the operating
contract.

Treat the user's text after `/uiplan-ground` as the topic. Run
`uipath_plan_ground` to gather project context, matched skills, library hits,
PDD candidates, and constitution gates.

If the topic is missing, ask one concise clarifying question. This command is
read-only and must not create or edit plan files.
