# Documentation Index

**Complete guide to all UiPath Builder Agent documentation**

---

## 🚀 Start Here

### New to the Project?

1. **Quick Start (5-10 min):** `QUICKSTART.md`
   - Multiple paths based on your goal
   - Common tasks and troubleshooting
   - Command cheat sheet

2. **Watch the Demo (3 min):**
   - Video: `assets/agenthack/agenthack-application-walkthrough-voiced.mp4`
   - Script: `agenthack/demo-script.md`

3. **Complete Overview (30 min):** `PROJECT_OVERVIEW.md`
   - System architecture
   - Agent descriptions
   - Workflow explanations
   - UI component guide

---

## 📚 Master Documentation Suite

### Core Guides (Read These First)

| Document | Purpose | Time | Audience |
|----------|---------|------|----------|
| **QUICKSTART.md** | Get running in 5-10 minutes | 10 min | Everyone |
| **PROJECT_OVERVIEW.md** | Complete system documentation | 30 min | All roles |
| **NAVIGATION_GUIDE.md** | Find anything quickly | 5 min | Everyone |
| **SYSTEM_DIAGRAM.md** | Visual architecture & flows | 15 min | Technical |
| **COMPLETE_MATERIALS_SUMMARY.md** | Full file inventory | 15 min | Reviewers |

### Technical Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| **ARCHITECTURE.md** | Deep technical architecture | Developers, Architects |
| **CAPABILITY_CONTRACT.md** | API contracts and interfaces | Developers |
| **USER_GUIDE.md** | CLI usage guide | Developers, Ops |
| **CURSOR_USER_GUIDE.md** | Cursor/IDE integration | Developers |

### Planning & Process

| Document | Purpose | Audience |
|----------|---------|----------|
| **PDD_LIFECYCLE.md** | Process design lifecycle | BA, PM |
| **PLANNING_FRAMEWORK.md** | Planning methodology | SA, BA |
| **TESTING.md** | Test strategy | QA |
| **SMOKE_TESTS.md** | Validation scenarios | QA, Ops |

---

## 🎯 Find What You Need

### By Role

#### Business Analyst
1. `QUICKSTART.md` → "Just show me the demo"
2. Watch: `assets/agenthack/agenthack-application-walkthrough-voiced.mp4`
3. Read: `generated/pdd.md`
4. Sample: `samples/invoice-exception/intake.json`

#### Solution Architect
1. `PROJECT_OVERVIEW.md` → Agent System section
2. `SYSTEM_DIAGRAM.md` → Complete architecture
3. `ARCHITECTURE.md` → Technical details
4. `solution/solution.uipx` → Packaging

#### Developer
1. `QUICKSTART.md` → "I want to run it locally"
2. `NAVIGATION_GUIDE.md` → File finder
3. `agents/*/main.py` → Agent code
4. `studio/web/src/components/` → UI code

#### QA / Tester
1. `generated/test-plan.md`
2. `TESTING.md`
3. `evidence/` → Test results
4. `SMOKE_TESTS.md`

#### DevOps / Operations
1. `generated/deployment-runbook.md`
2. `generated/monitoring-runbook.md`
3. `solution/` → Packaging
4. `evidence/` → Evidence files

### By Goal

#### "Understand the Project"
→ `QUICKSTART.md` + Demo video + `PROJECT_OVERVIEW.md`

#### "Run the System"
→ `QUICKSTART.md` → "I want to run it locally"

#### "Understand Architecture"
→ `SYSTEM_DIAGRAM.md` → `ARCHITECTURE.md` → `PROJECT_OVERVIEW.md`

#### "Find Specific Code"
→ `NAVIGATION_GUIDE.md` → File finder section

#### "Submit to AgentHack"
→ `agenthack/submission-checklist.md` → All submission materials

#### "Review All Materials"
→ `COMPLETE_MATERIALS_SUMMARY.md`

---

## 🗂️ Documentation Structure

```
docs/
├── 📘 QUICKSTART.md                    ⭐ START HERE
├── 📘 PROJECT_OVERVIEW.md              ⭐ COMPLETE GUIDE
├── 📘 NAVIGATION_GUIDE.md              ⭐ FIND ANYTHING
├── 📘 SYSTEM_DIAGRAM.md                ⭐ VISUAL ARCHITECTURE
├── 📘 COMPLETE_MATERIALS_SUMMARY.md    ⭐ FILE INVENTORY
│
├── 📗 Technical Documentation
│   ├── ARCHITECTURE.md
│   ├── CAPABILITY_CONTRACT.md
│   ├── USER_GUIDE.md
│   ├── CURSOR_USER_GUIDE.md
│   ├── TESTING.md
│   └── SMOKE_TESTS.md
│
├── 📙 Planning & Process
│   ├── PDD_LIFECYCLE.md
│   ├── PLANNING_FRAMEWORK.md
│   └── LIBRARY.md
│
├── 📕 Reference
│   ├── SKILLS.md
│   ├── MCP_TOOLS.md
│   ├── TOOLS.md
│   └── README.md (this file)
│
├── 🎬 Demo & Submission
│   ├── agenthack/
│   │   ├── README.md
│   │   ├── submission-materials.md
│   │   ├── submission-checklist.md
│   │   ├── forum-submission.md
│   │   ├── pitch-deck-outline.md
│   │   ├── demo-script.md
│   │   └── judging-matrix.md
│   │
│   └── assets/
│       ├── agenthack/
│       │   ├── *.mp4 (demo videos)
│       │   └── *.srt (subtitles)
│       └── screenshots/
│
├── 📊 Generated Documentation
│   └── generated/
│       ├── pdd.md
│       ├── sdd.md
│       ├── add.md
│       ├── test-plan.md
│       ├── deployment-runbook.md
│       ├── monitoring-runbook.md
│       └── handoff.md
│
└── 📈 Evidence & Validation
    └── evidence/
        ├── cicd-telemetry.json
        ├── orchestrator-telemetry.json
        ├── solution-analyze.json
        └── *-verification.md
```

---

## 🔍 Search Index

### Keywords → Documents

| Looking for | See |
|-------------|-----|
| **Setup, installation** | `QUICKSTART.md`, `USER_GUIDE.md` |
| **Architecture, system design** | `SYSTEM_DIAGRAM.md`, `ARCHITECTURE.md` |
| **Agent code, implementation** | `PROJECT_OVERVIEW.md` → Agent System |
| **UI components** | `PROJECT_OVERVIEW.md` → Studio Web Interface |
| **API endpoints** | `CAPABILITY_CONTRACT.md`, `MCP_TOOLS.md` |
| **Workflows** | `PROJECT_OVERVIEW.md` → Workflows |
| **Testing** | `TESTING.md`, `SMOKE_TESTS.md` |
| **Demo video** | `assets/agenthack/*.mp4` |
| **Submission materials** | `agenthack/submission-checklist.md` |
| **File locations** | `NAVIGATION_GUIDE.md` |
| **All files inventory** | `COMPLETE_MATERIALS_SUMMARY.md` |

### Features → Documentation

| Feature | Documentation |
|---------|---------------|
| **Multi-agent orchestration** | `PROJECT_OVERVIEW.md` → Agent System |
| **Orient/Decide/Execute/Verify modes** | `PROJECT_OVERVIEW.md` → Studio Web Interface |
| **Planning artifacts (spec/plan/tasks)** | `PLANNING_FRAMEWORK.md`, `PDD_LIFECYCLE.md` |
| **Evidence collection** | `PROJECT_OVERVIEW.md` → Workflows |
| **UiPath integration** | `ARCHITECTURE.md`, `CAPABILITY_CONTRACT.md` |
| **Solution packaging** | `solution/solution.uipx`, `generated/sdd.md` |

---

## 📖 Recommended Reading Orders

### Path 1: Quick Demo (30 minutes)
1. `QUICKSTART.md` (5 min)
2. Watch demo video (3 min)
3. `PROJECT_OVERVIEW.md` → Executive Summary (5 min)
4. `SYSTEM_DIAGRAM.md` → High-Level Architecture (5 min)
5. Browse `agenthack/submission-materials.md` (5 min)
6. Skim `COMPLETE_MATERIALS_SUMMARY.md` (7 min)

### Path 2: Technical Deep Dive (2 hours)
1. `QUICKSTART.md` (10 min)
2. `PROJECT_OVERVIEW.md` (30 min)
3. `SYSTEM_DIAGRAM.md` (20 min)
4. `ARCHITECTURE.md` (30 min)
5. Review agent code in `agents/` (20 min)
6. Review UI code in `studio/web/` (10 min)

### Path 3: Developer Onboarding (1 hour)
1. `QUICKSTART.md` → Run locally (10 min)
2. `NAVIGATION_GUIDE.md` (5 min)
3. `PROJECT_OVERVIEW.md` → Agent System (15 min)
4. Study `agents/shared/agent_contracts.py` (10 min)
5. Review one agent: `agents/builder-orchestrator/main.py` (10 min)
6. Run tests: `pytest -q` (5 min)
7. Review API: `studio/api/app/routers/` (5 min)

### Path 4: AgentHack Judge (45 minutes)
1. Watch demo video (3 min)
2. `agenthack/submission-materials.md` (5 min)
3. `agenthack/judging-matrix.md` (5 min)
4. `PROJECT_OVERVIEW.md` (15 min)
5. `COMPLETE_MATERIALS_SUMMARY.md` (10 min)
6. Review evidence: `evidence/` (7 min)

---

## 🎓 Learning Resources

### Concepts & Patterns

| Concept | Where to Learn |
|---------|----------------|
| **Agent-of-agents** | `PROJECT_OVERVIEW.md` → Agent System |
| **LangGraph state machines** | `agents/builder-orchestrator/agent.mermaid` |
| **Four-mode UI pattern** | `PROJECT_OVERVIEW.md` → Studio Web Interface |
| **Planning workflow** | `PLANNING_FRAMEWORK.md` |
| **Evidence-driven delivery** | `PROJECT_OVERVIEW.md` → Workflows |
| **UiPath Solution packaging** | `solution/solution.uipx` |

### Code Examples

| Example | Location |
|---------|----------|
| **Agent implementation** | `agents/discovery-agent/main.py` |
| **Orchestrator flow** | `agents/builder-orchestrator/main.py` |
| **Shared contracts** | `agents/shared/agent_contracts.py` |
| **UI mode component** | `studio/web/src/components/OrientMode.tsx` |
| **API endpoint** | `studio/api/app/routers/agentops_demo.py` |
| **Workflow script** | `workflows/documentation-factory-workflow/run.py` |

---

## 🔗 External References

### UiPath Resources
- [UiPath CLI Documentation](https://docs.uipath.com/automation-cloud/docs/cli)
- [UiPath Agent Builder](https://docs.uipath.com/agent-builder)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)

### Project Links
- **GitHub Repository:** (Add your URL)
- **Demo Video:** `docs/assets/agenthack/`
- **Submission Materials:** `docs/agenthack/`

---

## 📊 Documentation Statistics

- **Total Documentation Pages:** 50+
- **Master Guides:** 5 (NEW)
- **Technical Docs:** 10+
- **Generated Docs:** 7
- **Submission Materials:** 7
- **Evidence Files:** 6
- **Demo Assets:** 15+

---

## 🆘 Need Help?

### Can't find something?
→ `NAVIGATION_GUIDE.md` → File Finder section

### Don't know where to start?
→ `QUICKSTART.md` → Choose Your Path section

### Need to understand architecture?
→ `SYSTEM_DIAGRAM.md` → Visual guides

### Want complete file list?
→ `COMPLETE_MATERIALS_SUMMARY.md` → Complete File Inventory

### Setting up locally?
→ `QUICKSTART.md` → "I want to run it locally"

### Reviewing for submission?
→ `agenthack/submission-checklist.md`

---

## ✅ Documentation Quality Checklist

All documentation includes:
- ✅ Clear purpose and audience
- ✅ Visual diagrams where helpful
- ✅ Code examples and snippets
- ✅ Cross-references to related docs
- ✅ Troubleshooting guidance
- ✅ Up-to-date file paths
- ✅ Version and last-updated info

---

**Last Updated:** May 17, 2026  
**Documentation Version:** 1.0  
**Project Status:** AgentHack Submission Ready

**Navigate back to:**
- [Main README](../README.md)
- [Quick Start](QUICKSTART.md)
- [Project Overview](PROJECT_OVERVIEW.md)
