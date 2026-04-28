---
slug: 2026-04-28-it-support-flow-dmn-hitl-demo
title: IT Support Flow DMN HITL Demo
date: 2026-04-28
status: accepted
owner: DanielaRosenstein
project_type: solution
---

# IT Support Agent: Flow + DMN + HITL Demo

> Superseded for implementation by the UiPlan folder bundle at
> `.cursor/plans/2026-04-28-it-support-flow-dmn-hitl-demo/`
> (`spec.md`, `plan.md`, `tasks.md`), which contains the 360 visibility contract
> and executable task-level detail.

## 360 bundle navigation

| Need | Navigate to |
| --- | --- |
| Business scope and outcomes | `.cursor/plans/2026-04-28-it-support-flow-dmn-hitl-demo/spec.md` |
| Architecture, dependencies, skill/tool/subagent routing | `.cursor/plans/2026-04-28-it-support-flow-dmn-hitl-demo/plan.md` |
| Step-by-step execution, task IDs, verify commands, evidence paths | `.cursor/plans/2026-04-28-it-support-flow-dmn-hitl-demo/tasks.md` |

Source use-case reference:
- [IT Support Agent - Coded agents challenge](https://forum.uipath.com/t/it-support-agent-coded-agents-challenge/5671451)
- [Forum reply](https://forum.uipath.com/t/it-support-agent-coded-agents-challenge/5671451/2)

Execution-grade demo plan: Flow owns orchestration and HITL, LangGraph owns
semantic reasoning, DMN owns deterministic policy, and Modern RPA workflows own
deterministic IT actions.

## Scope

- Build a ticket-triage demo for Information Technology and Services.
- Resolve self-serviceable tickets automatically where policy allows.
- Trigger deterministic UiPath actions for standard IT requests.
- Escalate to human review when policy or confidence requires it.

## Solution topology

```mermaid
flowchart TD
  Ticket[Incoming_ticket] --> Flow[ITSupport_flow]
  Flow --> Normalize[Normalize_ticket]
  Normalize --> Agent[LangGraph_support_agent]
  Agent --> DMN[Support_routing_policy_dmn]
  DMN --> Route{Route_decision}
  Route --> SelfServe[Self_service_response]
  Route --> Action[Deterministic_IT_workflow]
  Route --> Review[HITL_review]
  SelfServe --> Close[Ticket_close_and_audit]
  Action --> Close
  Review --> Close
```

## Plan phases

| Phase | Goal | Deliverable |
| --- | --- | --- |
| Phase 1 | Readiness and access gates | `out/tool-readiness.txt` |
| Phase 2 | Flow + agent + DMN test baseline | validation + JUnit evidence |
| Phase 3 | Implement graph/action/flow branches | updated `graph.py`, `Main.xaml`, `it-support.flow` |
| Phase 4 | HITL closure and route finalization | Flow HITL paths validated |
| Phase 5 | Build, verify, diagnose/rerun | `out/verification-summary.md`, `out/diagnose-rerun.md` |

## Task dependency map

```mermaid
flowchart TD
  T001[T001_readiness]
  T010[T010_flow_contract]
  T020[T020_agent_schema_tests]
  T030[T030_dmn_policy_tests]
  T040[T040_agent_implementation]
  T050[T050_action_workflows]
  T060[T060_hitl_closure]
  T070[T070_build_verify_handoff]

  T001 --> T010
  T001 --> T020
  T010 --> T030
  T020 --> T040
  T030 --> T040
  T040 --> T050
  T050 --> T060
  T060 --> T070
```

## Workflow-level build visuals

### `it-support.flow`

```mermaid
flowchart LR
  Trigger[Trigger] --> Normalize[Normalize ticket]
  Normalize --> Agent[Invoke graph.py]
  Agent --> DMN[Evaluate support-routing.dmn]
  DMN --> Route{Route}
  Route --> SelfService[Self service close]
  Route --> Action[Invoke Main.xaml]
  Route --> HITL[Flow HITL]
  Action --> Close[Close + audit]
  HITL --> Close
  SelfService --> Close
```

### `graph.py`

```mermaid
flowchart TD
  Input[Ticket schema] --> Classify[classify_ticket]
  Classify --> Policy[apply_policy]
  Policy --> Output[route/confidence/accessRisk]
```

### `support-routing.dmn`

```mermaid
flowchart TD
  Inputs[confidence + accessRisk] --> Rules[DMN rows]
  Rules --> Output[requiresHumanReview]
```

### `Main.xaml`

```mermaid
flowchart TD
  Start[Action request] --> Decide{recommendedAction}
  Decide --> Reset[Password reset]
  Decide --> Provision[Access provisioning]
  Decide --> Escalate[Escalate to human]
  Reset --> Done[ActionExecuted]
  Provision --> Done
  Escalate --> Done
```

## Readiness gate for execution

- `uipcli --help`, `uip --version`, `uipath --version`, `uv --version`
- Studio Web access for Flow/HITL
- Orchestrator Dev/personal workspace only for smoke tests
- No secrets in repo; assets/env vars only
- DMN in scope explicitly recorded before task generation
