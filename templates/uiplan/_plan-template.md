# Implementation Plan: {{TITLE}}

> **Grounding:** {{GROUNDING_CITATIONS}}
> **Spec:** `./spec.md`

**Date**: {{DATE}}
**Spec**: ./spec.md

## Summary

{{SUMMARY}}

## Grounding Inputs

{{GROUNDING_CONTEXT}}

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

## Architecture diagram

Implementation layering and dependencies (adapt nodes to this plan).

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#E2E8F0','primaryTextColor':'#0F172A','primaryBorderColor':'#94A3B8','lineColor':'#94A3B8','secondaryColor':'#F1F5F9','tertiaryColor':'#F8FAFC','background':'#FFFFFF','clusterBkg':'#F8FAFC','clusterBorder':'#CBD5E1','titleColor':'#0F172A','edgeLabelBackground':'#FFFFFF','fontFamily':'Inter, ui-sans-serif, system-ui'}}}%%
flowchart LR
  subgraph Packages["UiPath packages / projects"]
    A[Process or library project]:::process
    B[Shared library or test project]:::service
  end
  subgraph Tests["Verification"]
    T[uipcli analyze / test / pack]:::human
  end
  A --> B
  B --> T

  classDef process  fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:1.25px
  classDef service  fill:#EFF6FF,stroke:#3B82F6,color:#1E3A8A,stroke-width:1.25px
  classDef human    fill:#F5F3FF,stroke:#8B5CF6,color:#5B21B6,stroke-width:1.5px

  linkStyle default stroke:#94A3B8,stroke-width:1.5px
  linkStyle 0 stroke:#3B82F6,stroke-width:2px
  linkStyle 1 stroke:#10B981,stroke-width:2px
```

## Build and verify gates

Restore, analyze, test, and pack (adapt steps to your project type).

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#E2E8F0','primaryTextColor':'#0F172A','primaryBorderColor':'#94A3B8','lineColor':'#94A3B8','secondaryColor':'#F1F5F9','tertiaryColor':'#F8FAFC','background':'#FFFFFF','clusterBkg':'#F8FAFC','clusterBorder':'#CBD5E1','titleColor':'#0F172A','edgeLabelBackground':'#FFFFFF','fontFamily':'Inter, ui-sans-serif, system-ui'}}}%%
flowchart TB
  subgraph Prep["Prepare"]
    R[Restore deps]:::process
  end
  subgraph Gates["Quality gates"]
    A[Analyze]:::service
    T[Tests]:::service
    P[Pack]:::process
  end
  subgraph Ship["Optional handoff"]
    D[Approval-required deploy via runbook]:::human
  end
  R --> A
  A -->|errors| R
  A --> T
  T -->|fail| R
  T --> P
  P --> D

  classDef process  fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:1.25px
  classDef service  fill:#EFF6FF,stroke:#3B82F6,color:#1E3A8A,stroke-width:1.25px
  classDef human    fill:#F5F3FF,stroke:#8B5CF6,color:#5B21B6,stroke-width:1.5px

  linkStyle default stroke:#94A3B8,stroke-width:1.5px
  linkStyle 0,1 stroke:#3B82F6,stroke-width:2px
  linkStyle 4,5 stroke:#10B981,stroke-width:2px
```

## Deployment policy

Deployment tasks are optional and approval-required. If this plan includes
publish/deploy work, reference [docs/ORCHESTRATOR_DEPLOYMENT.md](../../docs/ORCHESTRATOR_DEPLOYMENT.md)
instead of embedding long deploy recipes. The first task must be the
compatibility preflight: Studio, CLI, package versions, target framework,
Orchestrator target, and Solution/Maestro support.

## Activity references (optional)

`uipath_plan_tasks_new` scans **plan.md** and **spec.md** for machine-readable activity tags (up to 8 unique pairs) and appends matching documentation to **tasks.md**.

Tag shape on **one line** (no line breaks inside the tag): an opening square bracket `[`, the literal prefix `activity:`, your NuGet-style **PackageId**, a colon, the **ActivityName** as in Studio, then `]`. Only add tags for activities you will actually use; omit demo or placeholder tags so **Resolved activity docs** stays short.

Human-readable shape (not a tag - note the space after `[` so tooling ignores it): `[ activity:YourPackage.YourActivities:YourActivityName ]`.

## Complexity Tracking

{{COMPLEXITY_TABLE}}
