# UiPlan (spec + plan + tasks)

UiPlan is the **three-file planning bundle** used before implementation: `spec.md` (what), `plan.md` (how), and `tasks.md` (executable steps). It pairs with MCP plan tools and the local **`tools/uiplan`** CLI for generate → review → scaffold workflows.
![UiPlan logo](../assets/uiplan-logo.svg)

## First 15 minutes

If you are new, do this in order:

1. Read [HOW_TO_USE.md](HOW_TO_USE.md) for the mode matrix (MCP vs CLI vs skill).
2. Generate a bundle: `uv run python -m tools.uiplan generate-docs <slug>`.
3. Review the three files (`spec.md`, `plan.md`, `tasks.md`) and tighten scope.
4. Run review (`uipath_plan_review` or `/uiplan-review <slug>`) and resolve findings.
5. Move to scaffold/build only after acceptance.

This flow is the fastest way to keep planning quality high and implementation predictable.

## Decision tree (when to use UiPlan)

```mermaid
flowchart TD
  startNode["Need to change behavior"] --> scopeNode{"Single-file small fix?"}
  scopeNode -->|yes| directNode["Edit directly + validate"]
  scopeNode -->|no| formalNode{"Need formal BA/SA/ADD/TDD outputs?"}
  formalNode -->|yes| pddNode["Use /pdd lifecycle"]
  formalNode -->|no| uiplanNode["Use UiPlan bundle"]
  uiplanNode --> reviewNode["Review and accept"]
  reviewNode --> buildNode["Scaffold/build"]
```

## Audience

- **Humans** authoring or reviewing build-ready specs in Cursor or on GitHub.
- **Agents** using `uipath_plan_*` tools and the [UiPlan Cursor skill](../../.cursor/skills/uiplan/SKILL.md).

## Where to start

| Doc | Purpose |
| --- | --- |
| [HOW_TO_USE.md](HOW_TO_USE.md) | MCP vs CLI vs skill; folder conventions; approval gate |
| [UiPlan framework (MCP matrix)](../plans/2026-04-21-uiplan-framework.md) | Tooling roles and storage model |
| [Template kit](../../templates/uiplan/) | `_spec-template.md`, `_plan-template.md`, `_tasks-template.md`, `_diagram-patterns.md` |
| [Orchestrator deployment runbook](../ORCHESTRATOR_DEPLOYMENT.md) | Optional deploy gates and compatibility preflight for generated tasks |
| [Mermaid Pro Standard](../../.cursor/skills/mermaid-diagram-builder/SKILL.md) | Diagram style contract for this repo |
| [MERMAID_VALIDATION.md](MERMAID_VALIDATION.md) | Optional `mmdc` batch check for fenced diagrams |
| [SCAFFOLD_CODE.md](SCAFFOLD_CODE.md) | What `tools.uiplan scaffold-code` does today |
| [../CAPABILITY_CONTRACT.md](../CAPABILITY_CONTRACT.md) | Canonical CLI/Cursor/MCP surface and non-goals |

## Repository layout (UiPlan-related)

```mermaid
flowchart TB
  subgraph Guides["Human guides (context)"]
    H[docs/uiplan/]:::human
  end
  subgraph Templates["Reusable kit"]
    U[templates/uiplan/]:::service
  end
  subgraph Published["Published bundles"]
    P[docs/plans/]:::process
  end
  subgraph Runtime["Runtime"]
    T[tools/uiplan CLI]:::service
    F[framework/mcp_server plan tools]:::service
  end
  subgraph Drafts["Drafts (gitignored)"]
    C[".cursor/plans/<slug>/"]:::human
  end
  U --> T
  H -.->|read before drafting| C
  T --> C
  C -->|review + accept| P
  F --> C
```

## Generate → review → scaffold (sequence)

```mermaid
sequenceDiagram
  autonumber
  actor Dev as Developer
  participant CLI as tools/uiplan
  participant FS as Plan folder
  participant Rev as Review / MCP
  Dev->>CLI: generate-docs <slug>
  CLI->>FS: spec.md plan.md tasks.md
  Dev->>Rev: Human + uipath_plan_review
  Rev-->>Dev: ok / findings
  Dev->>CLI: scaffold-code <slug>
  CLI-->>Dev: implementation loop (capped)
```

## Best leverage patterns

| Pattern | Use UiPlan this way | Expected benefit |
| --- | --- | --- |
| Small feature | Keep spec short, focus plan on integration points, split 3-6 tasks | Fast implementation with low overhead |
| Medium refactor | Expand risks/rollback in plan, enforce task-level validation checks | Lower regression risk |
| Formal initiative | Use UiPlan for build contract, then handoff to `/pdd` for full lifecycle docs | Better cross-team coordination |
