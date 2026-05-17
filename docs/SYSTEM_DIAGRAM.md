# UiPath Builder Agent - System Diagram

**Visual guide to system architecture and data flow**

---

## Complete System Architecture

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#E2E8F0','primaryTextColor':'#0F172A','primaryBorderColor':'#94A3B8','lineColor':'#94A3B8','secondaryColor':'#F1F5F9','tertiaryColor':'#F8FAFC','background':'#FFFFFF','clusterBkg':'#F8FAFC','clusterBorder':'#CBD5E1','titleColor':'#0F172A','edgeLabelBackground':'#FFFFFF','fontFamily':'Inter, ui-sans-serif, system-ui'}}}%%
graph TB
    subgraph UserLayer["👤 User Layer"]
        BA[Business Analyst]
        SA[Solution Architect]
        DEV[Developer]
        QA[QA Engineer]
        OPS[Operations]
    end
    
    subgraph InterfaceLayer["🖥️ Interface Layer - Studio Web"]
        UI1[Orient Mode<br/>AS-IS Context]
        UI2[Decide Mode<br/>Planning Review]
        UI3[Execute Mode<br/>Kanban + Files]
        UI4[Verify Mode<br/>Evidence + Readiness]
    end
    
    subgraph APILayer["⚡ API Layer - FastAPI"]
        API1[/api/projects]
        API2[/api/agentops/intake]
        API3[/api/agentops/orchestrate]
        API4[/api/projects/{id}/graph]
        API5[/api/projects/{id}/tasks]
    end
    
    subgraph OrchestrationLayer["🎯 Orchestration Layer"]
        ORCH[Builder Orchestrator<br/>LangGraph State Machine]
        ORCH_CLASSIFY[Classify Request]
        ORCH_ASSIGN[Assign Agents]
        ORCH_DRAFT[Draft Plan]
        ORCH_APPROVE[Request Approval]
        ORCH_BUILD[Prepare Build]
        ORCH_HANDOFF[Summarize Handoff]
    end
    
    subgraph AgentLayer["🤖 Agent Layer"]
        AGENT1[Discovery Agent<br/>Context Extraction]
        AGENT2[Solution Architect<br/>Technical Design]
        AGENT3[Verifier Agent<br/>Quality Gates]
        AGENT4[Deployment Evidence<br/>Readiness Checks]
    end
    
    subgraph WorkflowLayer["🔄 Workflow Layer"]
        WF1[CI/CD Telemetry<br/>Build Metrics]
        WF2[Orchestrator Monitor<br/>Agent Health]
        WF3[Documentation Factory<br/>Doc Generation]
        WF4[Evidence API<br/>Data Aggregation]
        WF5[Smoke Test<br/>Deployment Validation]
    end
    
    subgraph ArtifactLayer["📄 Artifact Layer"]
        ART1[spec.md<br/>Business Scope]
        ART2[plan.md<br/>Architecture]
        ART3[tasks.md<br/>Implementation]
        ART4[PDD/SDD/ADD<br/>Formal Docs]
        ART5[Evidence Package<br/>Validation Data]
    end
    
    subgraph StorageLayer["💾 Storage Layer"]
        FS[(File System<br/>Projects & Artifacts)]
        DB[(SQLite<br/>State & Metadata)]
        EVIDENCE[(Evidence Store<br/>Telemetry & Logs)]
    end
    
    subgraph IntegrationLayer["🔌 Integration Layer"]
        UIPATH[UiPath Platform<br/>Orchestrator + Studio]
        MCP[MCP Tools<br/>Skill Registry]
        CLI[UiPath CLI<br/>uipcli, uipath, uip]
    end
    
    %% User to Interface
    BA --> UI1
    SA --> UI2
    DEV --> UI3
    QA --> UI4
    OPS --> UI4
    
    %% Interface to API
    UI1 --> API1
    UI2 --> API2
    UI3 --> API3
    UI3 --> API4
    UI3 --> API5
    UI4 --> API5
    
    %% API to Orchestration
    API2 --> ORCH
    API3 --> ORCH
    
    %% Orchestration Flow
    ORCH --> ORCH_CLASSIFY
    ORCH_CLASSIFY --> ORCH_ASSIGN
    ORCH_ASSIGN --> ORCH_DRAFT
    ORCH_DRAFT --> ORCH_APPROVE
    ORCH_APPROVE --> ORCH_BUILD
    ORCH_BUILD --> ORCH_HANDOFF
    
    %% Orchestration to Agents
    ORCH_ASSIGN --> AGENT1
    ORCH_ASSIGN --> AGENT2
    ORCH_DRAFT --> AGENT3
    ORCH_BUILD --> AGENT4
    
    %% Agents to Workflows
    AGENT1 --> WF4
    AGENT2 --> WF3
    AGENT3 --> WF5
    AGENT4 --> WF1
    AGENT4 --> WF2
    
    %% Workflows to Artifacts
    WF3 --> ART1
    WF3 --> ART2
    WF3 --> ART3
    WF3 --> ART4
    WF4 --> ART5
    WF5 --> ART5
    
    %% Artifacts to Storage
    ART1 --> FS
    ART2 --> FS
    ART3 --> FS
    ART4 --> FS
    ART5 --> EVIDENCE
    
    %% Orchestration to Storage
    ORCH --> DB
    
    %% Integration Layer
    ORCH --> MCP
    AGENT2 --> CLI
    WF5 --> UIPATH
    
    %% Storage to API (read back)
    FS --> API4
    DB --> API5
    EVIDENCE --> API5
    
    classDef userStyle fill:#F3E8FF,stroke:#9333EA,color:#0F172A,stroke-width:2px
    classDef uiStyle fill:#DBEAFE,stroke:#2563EB,color:#0F172A,stroke-width:2px
    classDef apiStyle fill:#D1FAE5,stroke:#10B981,color:#0F172A,stroke-width:2px
    classDef orchStyle fill:#FEE2E2,stroke:#EF4444,color:#0F172A,stroke-width:2px
    classDef agentStyle fill:#FCE7F3,stroke:#EC4899,color:#0F172A,stroke-width:2px
    classDef workflowStyle fill:#FEF3C7,stroke:#F59E0B,color:#0F172A,stroke-width:2px
    classDef artifactStyle fill:#E0E7FF,stroke:#6366F1,color:#0F172A,stroke-width:2px
    classDef storageStyle fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:2px
    classDef integrationStyle fill:#FED7AA,stroke:#EA580C,color:#0F172A,stroke-width:2px
    
    class BA,SA,DEV,QA,OPS userStyle
    class UI1,UI2,UI3,UI4 uiStyle
    class API1,API2,API3,API4,API5 apiStyle
    class ORCH,ORCH_CLASSIFY,ORCH_ASSIGN,ORCH_DRAFT,ORCH_APPROVE,ORCH_BUILD,ORCH_HANDOFF orchStyle
    class AGENT1,AGENT2,AGENT3,AGENT4 agentStyle
    class WF1,WF2,WF3,WF4,WF5 workflowStyle
    class ART1,ART2,ART3,ART4,ART5 artifactStyle
    class FS,DB,EVIDENCE storageStyle
    class UIPATH,MCP,CLI integrationStyle
```

---

## Data Flow Diagrams

### 1. Business Intake to Artifacts

```mermaid
sequenceDiagram
    participant User as Business Analyst
    participant UI as Studio Web (Orient)
    participant API as FastAPI Backend
    participant Orch as Orchestrator
    participant Disc as Discovery Agent
    participant Arch as Solution Architect
    participant FS as File System
    
    User->>UI: Submit Business Intake
    UI->>API: POST /api/agentops/intake
    API->>Orch: Initialize State
    
    Orch->>Orch: Classify Request Type
    Note over Orch: RPA, Agent, Flow, etc.
    
    Orch->>Disc: Extract Context
    Disc->>Disc: Parse Stakeholders<br/>Systems, Constraints
    Disc-->>Orch: Context Data
    
    Orch->>Arch: Generate Plan
    Arch->>Arch: Create spec.md
    Arch->>Arch: Create plan.md
    Arch->>Arch: Create tasks.md
    Arch-->>Orch: UiPlan Bundle
    
    Orch->>FS: Write Artifacts
    FS-->>API: Artifacts Saved
    API-->>UI: Planning Complete
    UI-->>User: Show Decide Mode
```

### 2. Planning Review to Execution

```mermaid
sequenceDiagram
    participant User as Solution Architect
    participant UI as Studio Web (Decide)
    participant API as FastAPI Backend
    participant Orch as Orchestrator
    participant Verif as Verifier Agent
    participant FS as File System
    
    User->>UI: Review Plan
    UI->>API: GET /api/projects/{id}/graph
    API->>FS: Read Artifacts
    FS-->>API: spec.md, plan.md, tasks.md
    API-->>UI: Display Plans + Diagrams
    
    User->>UI: Approve Plan
    UI->>API: POST /api/agentops/orchestrate
    API->>Orch: Set verificationStatus = "approved"
    
    Orch->>Verif: Validate Artifacts
    Verif->>Verif: Check Spec Completeness
    Verif->>Verif: Check Plan Feasibility
    Verif->>Verif: Check Task Traceability
    
    alt Verification Passed
        Verif-->>Orch: Findings: []
        Orch->>Orch: Set Status = "ready_for_build"
        Orch-->>API: Build Preparation Complete
        API-->>UI: Switch to Execute Mode
        UI-->>User: Show Kanban Board
    else Verification Failed
        Verif-->>Orch: Findings: [blockers]
        Orch-->>API: Blockers Identified
        API-->>UI: Show Blockers
        UI-->>User: Remain in Decide Mode
    end
```

### 3. Implementation to Evidence Collection

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant UI as Studio Web (Execute)
    participant API as FastAPI Backend
    participant WF as Workflows
    participant Evidence as Evidence Store
    participant Verify as Deployment Evidence Agent
    
    Dev->>UI: Update Task Status
    UI->>API: PATCH /api/projects/{id}/tasks/{tid}
    API->>API: Update Kanban State
    
    loop For Each Completed Task
        Dev->>UI: Mark Task Complete
        API->>WF: Trigger Evidence Collection
        
        WF->>WF: CI/CD Telemetry Workflow
        WF->>Evidence: Store Build Metrics
        
        WF->>WF: Orchestrator Monitor
        WF->>Evidence: Store Agent Health
        
        WF->>WF: Smoke Test Workflow
        WF->>Evidence: Store Test Results
    end
    
    Dev->>UI: Request Verification
    UI->>API: POST /api/agentops/verify
    API->>Verify: Collect Evidence
    
    Verify->>Evidence: Get Telemetry
    Verify->>Evidence: Get Test Results
    Verify->>Evidence: Get Documentation
    
    alt All Evidence Complete
        Verify-->>API: Deployment Ready
        API->>WF: Documentation Factory
        WF->>WF: Generate Handoff Docs
        API-->>UI: Show Verify Mode (Green)
        UI-->>Dev: Ready for Handoff
    else Missing Evidence
        Verify-->>API: Blockers Identified
        API-->>UI: Show Verify Mode (Red)
        UI-->>Dev: Show Missing Items
    end
```

---

## Component Interaction Map

### Frontend to Backend

```mermaid
graph LR
    subgraph Frontend["React Frontend (Port 5174)"]
        Orient[OrientMode.tsx]
        Decide[DecideMode.tsx]
        Execute[ExecuteMode.tsx]
        Verify[VerifyMode.tsx]
    end
    
    subgraph Backend["FastAPI Backend (Port 8000)"]
        ProjectAPI[/api/projects]
        GraphAPI[/api/projects/{id}/graph]
        TaskAPI[/api/projects/{id}/tasks]
        IntakeAPI[/api/agentops/intake]
        OrchestrateAPI[/api/agentops/orchestrate]
        VerifyAPI[/api/agentops/verify]
    end
    
    Orient -->|GET| ProjectAPI
    Orient -->|GET| GraphAPI
    
    Decide -->|GET| GraphAPI
    Decide -->|POST| IntakeAPI
    Decide -->|POST| OrchestrateAPI
    
    Execute -->|GET| TaskAPI
    Execute -->|PATCH| TaskAPI
    Execute -->|GET| GraphAPI
    
    Verify -->|GET| TaskAPI
    Verify -->|POST| VerifyAPI
    
    classDef frontendStyle fill:#DBEAFE,stroke:#2563EB,color:#0F172A,stroke-width:2px
    classDef backendStyle fill:#D1FAE5,stroke:#10B981,color:#0F172A,stroke-width:2px
    
    class Orient,Decide,Execute,Verify frontendStyle
    class ProjectAPI,GraphAPI,TaskAPI,IntakeAPI,OrchestrateAPI,VerifyAPI backendStyle
```

### Agent Communication Pattern

```mermaid
graph TB
    subgraph Orchestrator["Orchestrator State Machine"]
        S1[Classify Request]
        S2[Assign Agents]
        S3[Draft Plan]
        S4[Request Approval]
        S5[Prepare Build]
        S6[Summarize Handoff]
    end
    
    subgraph SharedContracts["Shared Contracts Layer"]
        C1[IntakeRequest]
        C2[ClassificationResult]
        C3[PlanBundle]
        C4[VerificationResult]
        C5[DeploymentEvidence]
    end
    
    subgraph Agents["Specialized Agents"]
        A1[Discovery]
        A2[Solution Architect]
        A3[Verifier]
        A4[Deployment Evidence]
    end
    
    S1 --> C2
    S2 --> C1
    C1 --> A1
    C1 --> A2
    
    A1 --> C3
    A2 --> C3
    
    S3 --> C3
    C3 --> A3
    
    A3 --> C4
    S4 --> C4
    
    S5 --> C5
    C5 --> A4
    
    A4 --> S6
    
    classDef orchStyle fill:#FEE2E2,stroke:#EF4444,color:#0F172A,stroke-width:2px
    classDef contractStyle fill:#FEF3C7,stroke:#F59E0B,color:#0F172A,stroke-width:2px
    classDef agentStyle fill:#FCE7F3,stroke:#EC4899,color:#0F172A,stroke-width:2px
    
    class S1,S2,S3,S4,S5,S6 orchStyle
    class C1,C2,C3,C4,C5 contractStyle
    class A1,A2,A3,A4 agentStyle
```

---

## Artifact Generation Flow

```mermaid
flowchart TB
    START([Business Intake]) --> CLASSIFY{Classify}
    
    CLASSIFY -->|RPA| RPA_PATH[RPA Planning]
    CLASSIFY -->|Agent| AGENT_PATH[Agent Planning]
    CLASSIFY -->|Flow| FLOW_PATH[Flow Planning]
    CLASSIFY -->|Solution| SOLUTION_PATH[Solution Planning]
    
    RPA_PATH --> GENERATE
    AGENT_PATH --> GENERATE
    FLOW_PATH --> GENERATE
    SOLUTION_PATH --> GENERATE
    
    GENERATE[Generate Artifacts]
    
    GENERATE --> SPEC[spec.md<br/>Business Scope]
    GENERATE --> PLAN[plan.md<br/>Architecture]
    GENERATE --> TASKS[tasks.md<br/>Implementation]
    
    SPEC --> REVIEW{Review Gate}
    PLAN --> REVIEW
    TASKS --> REVIEW
    
    REVIEW -->|Pass| APPROVE[Human Approval]
    REVIEW -->|Fail| BLOCKERS[Identify Blockers]
    
    BLOCKERS --> GENERATE
    
    APPROVE --> EXECUTE[Execute Tasks]
    
    EXECUTE --> DOC_FACTORY[Documentation Factory]
    
    DOC_FACTORY --> PDD[PDD.md]
    DOC_FACTORY --> SDD[SDD.md]
    DOC_FACTORY --> ADD[ADD.md]
    DOC_FACTORY --> TEST_PLAN[test-plan.md]
    DOC_FACTORY --> DEPLOY_RUNBOOK[deployment-runbook.md]
    DOC_FACTORY --> MONITOR_RUNBOOK[monitoring-runbook.md]
    
    PDD --> EVIDENCE
    SDD --> EVIDENCE
    ADD --> EVIDENCE
    TEST_PLAN --> EVIDENCE
    DEPLOY_RUNBOOK --> EVIDENCE
    MONITOR_RUNBOOK --> EVIDENCE
    
    EVIDENCE[Evidence Collection] --> HANDOFF([Handoff Package])
    
    classDef startStyle fill:#ECFDF5,stroke:#10B981,color:#065F46,stroke-width:2px
    classDef processStyle fill:#DBEAFE,stroke:#2563EB,color:#0F172A,stroke-width:2px
    classDef artifactStyle fill:#E0E7FF,stroke:#6366F1,color:#0F172A,stroke-width:2px
    classDef decisionStyle fill:#FEF3C7,stroke:#F59E0B,color:#0F172A,stroke-width:2px
    classDef endStyle fill:#ECFDF5,stroke:#10B981,color:#065F46,stroke-width:2px
    
    class START,HANDOFF startStyle,endStyle
    class CLASSIFY,REVIEW decisionStyle
    class RPA_PATH,AGENT_PATH,FLOW_PATH,SOLUTION_PATH,GENERATE,APPROVE,EXECUTE,DOC_FACTORY,EVIDENCE processStyle
    class SPEC,PLAN,TASKS,PDD,SDD,ADD,TEST_PLAN,DEPLOY_RUNBOOK,MONITOR_RUNBOOK artifactStyle
```

---

## Test and Validation Pipeline

```mermaid
flowchart LR
    subgraph Dev["Development"]
        CODE[Write Code]
        UNIT[Unit Tests]
    end
    
    subgraph CI["Continuous Integration"]
        LINT[Linting]
        TYPE[Type Check]
        AGENT_TEST[Agent Tests<br/>18 tests]
        API_TEST[API Tests<br/>201 tests]
        WEB_TEST[Frontend Tests<br/>16 tests]
    end
    
    subgraph Evidence["Evidence Collection"]
        TELEM[Telemetry]
        SMOKE[Smoke Tests]
        DOC_CHECK[Doc Validation]
    end
    
    subgraph Deploy["Deployment Gate"]
        VERIFY{All Pass?}
        READY[Deployment Ready]
        BLOCK[Blocked]
    end
    
    CODE --> UNIT
    UNIT --> LINT
    LINT --> TYPE
    TYPE --> AGENT_TEST
    TYPE --> API_TEST
    TYPE --> WEB_TEST
    
    AGENT_TEST --> TELEM
    API_TEST --> TELEM
    WEB_TEST --> TELEM
    
    TELEM --> SMOKE
    SMOKE --> DOC_CHECK
    
    DOC_CHECK --> VERIFY
    
    VERIFY -->|Yes| READY
    VERIFY -->|No| BLOCK
    
    BLOCK -->|Fix| CODE
    
    classDef devStyle fill:#FEF3C7,stroke:#F59E0B,color:#0F172A,stroke-width:2px
    classDef ciStyle fill:#DBEAFE,stroke:#2563EB,color:#0F172A,stroke-width:2px
    classDef evidenceStyle fill:#E0E7FF,stroke:#6366F1,color:#0F172A,stroke-width:2px
    classDef deployStyle fill:#D1FAE5,stroke:#10B981,color:#0F172A,stroke-width:2px
    classDef blockStyle fill:#FEE2E2,stroke:#EF4444,color:#0F172A,stroke-width:2px
    
    class CODE,UNIT devStyle
    class LINT,TYPE,AGENT_TEST,API_TEST,WEB_TEST ciStyle
    class TELEM,SMOKE,DOC_CHECK evidenceStyle
    class VERIFY,READY deployStyle
    class BLOCK blockStyle
```

---

## Directory to Component Mapping

```mermaid
graph TB
    subgraph Repo["uipath-builder-agent/"]
        subgraph AgentsDir["agents/"]
            ORCH_DIR[builder-orchestrator/]
            DISC_DIR[discovery-agent/]
            ARCH_DIR[solution-architect-agent/]
            VERIF_DIR[verifier-agent/]
            DEPLOY_DIR[deployment-evidence-agent/]
            SHARED_DIR[shared/]
        end
        
        subgraph WorkflowsDir["workflows/"]
            WF1_DIR[cicd-telemetry-workflow/]
            WF2_DIR[orchestrator-monitor-workflow/]
            WF3_DIR[documentation-factory-workflow/]
            WF4_DIR[evidence-api-workflow/]
            WF5_DIR[smoke-test-workflow/]
        end
        
        subgraph StudioDir["studio/"]
            API_DIR[api/]
            WEB_DIR[web/]
        end
        
        subgraph DocsDir["docs/"]
            AGENTHACK_DIR[agenthack/]
            EVIDENCE_DIR[evidence/]
            GENERATED_DIR[generated/]
            ASSETS_DIR[assets/]
        end
        
        SOLUTION_DIR[solution/]
        EXAMPLES_DIR[examples/]
    end
    
    ORCH_DIR -.-> |"Coordinates"| DISC_DIR
    ORCH_DIR -.-> |"Coordinates"| ARCH_DIR
    ORCH_DIR -.-> |"Coordinates"| VERIF_DIR
    ORCH_DIR -.-> |"Coordinates"| DEPLOY_DIR
    
    DISC_DIR -.-> |"Uses"| SHARED_DIR
    ARCH_DIR -.-> |"Uses"| SHARED_DIR
    VERIF_DIR -.-> |"Uses"| SHARED_DIR
    DEPLOY_DIR -.-> |"Uses"| SHARED_DIR
    
    ARCH_DIR -.-> |"Triggers"| WF3_DIR
    DEPLOY_DIR -.-> |"Triggers"| WF1_DIR
    DEPLOY_DIR -.-> |"Triggers"| WF2_DIR
    VERIF_DIR -.-> |"Triggers"| WF5_DIR
    
    WF3_DIR -.-> |"Generates"| GENERATED_DIR
    WF4_DIR -.-> |"Aggregates"| EVIDENCE_DIR
    WF5_DIR -.-> |"Validates"| EVIDENCE_DIR
    
    WEB_DIR -.-> |"Calls"| API_DIR
    API_DIR -.-> |"Invokes"| ORCH_DIR
    
    ORCH_DIR -.-> |"Packages"| SOLUTION_DIR
    
    classDef agentStyle fill:#FCE7F3,stroke:#EC4899,color:#0F172A,stroke-width:2px
    classDef workflowStyle fill:#FEF3C7,stroke:#F59E0B,color:#0F172A,stroke-width:2px
    classDef uiStyle fill:#DBEAFE,stroke:#2563EB,color:#0F172A,stroke-width:2px
    classDef docsStyle fill:#E0E7FF,stroke:#6366F1,color:#0F172A,stroke-width:2px
    classDef otherStyle fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:2px
    
    class ORCH_DIR,DISC_DIR,ARCH_DIR,VERIF_DIR,DEPLOY_DIR,SHARED_DIR agentStyle
    class WF1_DIR,WF2_DIR,WF3_DIR,WF4_DIR,WF5_DIR workflowStyle
    class API_DIR,WEB_DIR uiStyle
    class AGENTHACK_DIR,EVIDENCE_DIR,GENERATED_DIR,ASSETS_DIR docsStyle
    class SOLUTION_DIR,EXAMPLES_DIR otherStyle
```

---

## Key Takeaways

### System Layers (Top to Bottom)
1. **User Layer:** BA, SA, Dev, QA, Ops personas
2. **Interface Layer:** 4 UI modes (Orient, Decide, Execute, Verify)
3. **API Layer:** RESTful endpoints for frontend-backend communication
4. **Orchestration Layer:** LangGraph state machine coordination
5. **Agent Layer:** Specialized agents for domain tasks
6. **Workflow Layer:** Evidence collection and doc generation
7. **Artifact Layer:** Planning files and documentation
8. **Storage Layer:** File system, database, evidence store
9. **Integration Layer:** UiPath platform, MCP, CLI tools

### Data Flow Pattern
```
Intake → Classification → Agent Assignment → Planning → Approval → 
Implementation → Evidence Collection → Verification → Handoff
```

### Key Integration Points
- Frontend ↔ Backend: REST API (JSON)
- Backend ↔ Orchestrator: Python function calls
- Orchestrator ↔ Agents: Shared contracts (typed)
- Agents ↔ Workflows: File system writes
- Workflows ↔ Storage: Evidence persistence
- System ↔ UiPath: CLI commands and MCP tools

---

**Navigate to:**
- [Project Overview](PROJECT_OVERVIEW.md) - Complete documentation
- [Navigation Guide](NAVIGATION_GUIDE.md) - Find what you need
- [Main README](../README.md) - Quick start

**Last Updated:** May 17, 2026  
**Version:** 1.0
