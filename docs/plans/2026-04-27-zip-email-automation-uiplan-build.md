---
slug: 2026-04-27-zip-email-automation-uiplan-build
title: Zip Email Automation Smart Invoice Routing
date: 2026-04-27
status: accepted
owner: DanielaRosenstein
project_type: solution
---

# Zip Email Automation Smart Invoice Routing

Authoritative execution bundle:
`.cursor/plans/2026-04-27-zip-email-automation-uiplan-build/`
(`spec.md`, `plan.md`, `tasks.md`).

## 360 bundle navigation

| Need | Navigate to |
| --- | --- |
| Scope, FR/SC, 360 artifact/dependency/logging contract | `.cursor/plans/2026-04-27-zip-email-automation-uiplan-build/spec.md` |
| Solution architecture, workflow catalog, connectors/resources, CLI matrix, skill/subagent map | `.cursor/plans/2026-04-27-zip-email-automation-uiplan-build/plan.md` |
| Execution task cards, FR traceability, clarification ledger, log assertion checklist, evidence outputs | `.cursor/plans/2026-04-27-zip-email-automation-uiplan-build/tasks.md` |

## Linked design docs

- PDD: `C:/Users/DanielaRosenstein/cursor_projects/AgenticAI_FIN02_ZipMailboxAutomation/docs/design/pdd.md`
- SDD: `C:/Users/DanielaRosenstein/cursor_projects/AgenticAI_FIN02_ZipMailboxAutomation/docs/design/sdd.md`
- ADD: `C:/Users/DanielaRosenstein/cursor_projects/AgenticAI_FIN02_ZipMailboxAutomation/docs/design/add.md`

## Runtime focus

- Dispatcher + analyzer runner are modern XAML surfaces.
- Analyzer is LangGraph Python surface.
- HITL is Flow-owned for this bundle.
- Verification is command/evidence-driven (analyze/test/pack/smoke + log assertions).
