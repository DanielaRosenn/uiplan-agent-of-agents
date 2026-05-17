# UiPath Builder Agent - Navigation Guide

**Quick reference for finding what you need**

---

## Start Here Based on Your Goal

### 🎯 "I want to understand what this is"
1. Start: `README.md` (2 min read)
2. Watch: `docs/assets/agenthack/agenthack-application-walkthrough-voiced.mp4` (3 min)
3. Read: `docs/PROJECT_OVERVIEW.md` (comprehensive guide)

### 🏗️ "I want to run the system"
1. Setup: `ops/scripts/cursor-quickstart.ps1` (automated)
2. Backend: `cd studio/api && uvicorn app.main:app --reload`
3. Frontend: `cd studio/web && pnpm dev`
4. Access: `http://localhost:5174`

### 🧪 "I want to test it"
1. All tests: `pytest agents/*/tests studio/api/tests -q`
2. Frontend: `cd studio/web && pnpm test`
3. Validation: `python ops/scripts/verify-local.ps1`

### 🤖 "I want to understand the agents"
1. Overview: `docs/PROJECT_OVERVIEW.md#agent-system`
2. Orchestrator: `agents/builder-orchestrator/README.md`
3. Contracts: `agents/shared/agent_contracts.py`
4. Graph: `agents/builder-orchestrator/agent.mermaid`

### 💻 "I want to see the UI"
1. Demo: `docs/assets/agenthack/agenthack-application-walkthrough-voiced.mp4`
2. Components: `studio/web/src/components/`
3. API: `studio/api/app/routers/agentops_demo.py`

### 📋 "I want to see the workflows"
1. List: `workflows/*/README.md`
2. Evidence: `docs/evidence/`
3. Outputs: `docs/generated/`

### 🎓 "I'm submitting to AgentHack"
1. Checklist: `docs/agenthack/submission-checklist.md`
2. Materials: `docs/agenthack/submission-materials.md`
3. Forum post: `docs/agenthack/forum-submission.md`
4. Deck: `docs/agenthack/pitch-deck-outline.md`

---

## Repository Map by Function

```
📦 uipath-builder-agent/
│
├── 🤖 AGENTS (Multi-agent system)
│   ├── builder-orchestrator/      Main coordinator
│   ├── discovery-agent/            Context extraction
│   ├── solution-architect-agent/   Planning generation
│   ├── verifier-agent/             Quality gates
│   ├── deployment-evidence-agent/  Readiness checks
│   └── shared/                     Contracts & types
│
├── 🔄 WORKFLOWS (Task execution)
│   ├── cicd-telemetry-workflow/
│   ├── orchestrator-monitor-workflow/
│   ├── documentation-factory-workflow/
│   ├── evidence-api-workflow/
│   └── smoke-test-workflow/
│
├── 🖥️ STUDIO (Web interface)
│   ├── api/                        FastAPI backend
│   └── web/                        React frontend
│       ├── components/
│       │   ├── OrientMode.tsx      AS-IS context
│       │   ├── DecideMode.tsx      Planning review
│       │   ├── ExecuteMode.tsx     Kanban + files
│       │   └── VerifyMode.tsx      Readiness checks
│       └── __tests__/
│
├── 📚 DOCUMENTATION
│   ├── agenthack/                  Submission materials
│   ├── evidence/                   Validation artifacts
│   ├── generated/                  Auto-generated docs
│   ├── assets/                     Videos and images
│   ├── PROJECT_OVERVIEW.md         ⭐ THIS IS THE MASTER GUIDE
│   ├── NAVIGATION_GUIDE.md         ⭐ YOU ARE HERE
│   └── ARCHITECTURE.md             Technical deep dive
│
├── 📦 SOLUTION
│   ├── solution.uipx               UiPath solution package
│   └── bindings/                   Environment configs
│
├── 🧪 EXAMPLES & SAMPLES
│   ├── examples/                   Demo projects
│   └── samples/                    Test fixtures
│
└── ⚙️ OPERATIONS
    └── ops/scripts/                Setup and utility scripts
```

---

## Quick Command Reference

### Setup Commands

```powershell
# Windows setup (Cursor + MCP)
.\ops\scripts\cursor-quickstart.ps1

# Linux/Mac setup
bash ops/scripts/cursor-quickstart.sh

# Install Python dependencies
pip install -e ".[dev,mcp]"

# Verify installation
uipath-claude doctor
```

### Run Commands

```bash
# Start backend API
cd studio/api
uvicorn app.main:app --reload --port 8000

# Start frontend
cd studio/web
pnpm dev

# Run orchestrator agent
cd agents/builder-orchestrator
uip codedagent run --input-file ../../samples/invoice-exception/intake.json

# Run all workflows
python workflows/cicd-telemetry-workflow/run.py
python workflows/documentation-factory-workflow/run.py
python workflows/evidence-api-workflow/run.py
python workflows/smoke-test-workflow/run.py
```

### Test Commands

```bash
# All agent tests
pytest agents/*/tests -q
# Expected: 18 passed

# API tests
cd studio/api && pytest tests -q
# Expected: 201 passed

# Frontend tests
cd studio/web && pnpm test
# Expected: 16 tests passed

# Full validation
python ops/scripts/verify-local.ps1
```

### Demo Commands

```bash
# Record UI walkthrough
cd studio/web
node ../../ops/scripts/record-agenthack-application-demo.mjs http://127.0.0.1:5174/

# Create workflow demo video
python ops/scripts/create-agenthack-workflow-demo-video.py

# Generate all documentation
cd workflows/documentation-factory-workflow
python run.py
```

---

## File Finder

### "Where is...?"

| Looking for | Path |
|-------------|------|
| **Main orchestrator code** | `agents/builder-orchestrator/main.py` |
| **Agent graph visualization** | `agents/builder-orchestrator/agent.mermaid` |
| **Shared agent contracts** | `agents/shared/agent_contracts.py` |
| **UI Orient mode** | `studio/web/src/components/OrientMode.tsx` |
| **UI Decide mode** | `studio/web/src/components/DecideMode.tsx` |
| **UI Execute mode** | `studio/web/src/components/ExecuteMode.tsx` |
| **UI Verify mode** | `studio/web/src/components/VerifyMode.tsx` |
| **API routes** | `studio/api/app/routers/` |
| **AgentOps endpoints** | `studio/api/app/routers/agentops_demo.py` |
| **Demo video (voiced)** | `docs/assets/agenthack/agenthack-application-walkthrough-voiced.mp4` |
| **Demo script** | `docs/agenthack/demo-script.md` |
| **Submission checklist** | `docs/agenthack/submission-checklist.md` |
| **Evidence files** | `docs/evidence/` |
| **Generated docs** | `docs/generated/` |
| **Solution package** | `solution/solution.uipx` |
| **Test fixtures** | `samples/invoice-exception/intake.json` |
| **Project overview** | `docs/PROJECT_OVERVIEW.md` |

---

## Decision Trees

### "What should I read first?"

```
Are you...

├─ A business stakeholder?
│  ├─ Start: README.md
│  ├─ Watch: agenthack-application-walkthrough-voiced.mp4
│  └─ Read: docs/generated/pdd.md
│
├─ A solution architect?
│  ├─ Start: docs/ARCHITECTURE.md
│  ├─ Review: docs/PROJECT_OVERVIEW.md#agent-system
│  └─ Check: solution/solution.uipx
│
├─ A developer?
│  ├─ Start: README.md → docs/USER_GUIDE.md
│  ├─ Setup: ops/scripts/cursor-quickstart.ps1
│  ├─ Code: agents/*/main.py
│  └─ Test: pytest agents/*/tests
│
├─ A QA tester?
│  ├─ Start: docs/generated/test-plan.md
│  ├─ Evidence: docs/evidence/
│  └─ Run: pytest agents/*/tests studio/api/tests
│
├─ DevOps/Operations?
│  ├─ Start: docs/generated/deployment-runbook.md
│  ├─ Check: docs/evidence/
│  └─ Package: solution/solution.uipx
│
└─ An AgentHack judge?
   ├─ Start: docs/agenthack/submission-materials.md
   ├─ Watch: docs/assets/agenthack/*.mp4
   ├─ Review: docs/agenthack/judging-matrix.md
   └─ Verify: pytest output (235 tests passing)
```

---

## Learning Paths

### Path 1: Quick Demo (15 minutes)
1. ⏱️ 2 min: Read `README.md`
2. ⏱️ 3 min: Watch `agenthack-application-walkthrough-voiced.mp4`
3. ⏱️ 5 min: Browse `studio/web/src/components/` UI code
4. ⏱️ 5 min: Run setup: `ops/scripts/cursor-quickstart.ps1`

### Path 2: Technical Deep Dive (1 hour)
1. ⏱️ 10 min: Read `docs/PROJECT_OVERVIEW.md`
2. ⏱️ 15 min: Study `agents/builder-orchestrator/main.py`
3. ⏱️ 15 min: Review `agents/shared/agent_contracts.py`
4. ⏱️ 10 min: Explore `studio/api/app/routers/`
5. ⏱️ 10 min: Run tests: `pytest -q`

### Path 3: Full System Understanding (2-3 hours)
1. ⏱️ 20 min: Read all of `docs/PROJECT_OVERVIEW.md`
2. ⏱️ 30 min: Study each agent: `agents/*/main.py`
3. ⏱️ 20 min: Review workflows: `workflows/*/README.md`
4. ⏱️ 30 min: Explore UI: `studio/web/src/`
5. ⏱️ 20 min: Check evidence: `docs/evidence/`
6. ⏱️ 30 min: Run full system locally

### Path 4: AgentHack Submission Review (30 minutes)
1. ⏱️ 5 min: Read `docs/agenthack/submission-materials.md`
2. ⏱️ 10 min: Watch demo videos
3. ⏱️ 5 min: Review `docs/agenthack/judging-matrix.md`
4. ⏱️ 5 min: Check `docs/agenthack/submission-checklist.md`
5. ⏱️ 5 min: Verify tests: `pytest -q` output

---

## Common Questions

### Q: How do I run the full system?
**A:** Follow the [Run Commands](#run-commands) section above. You need both backend (FastAPI) and frontend (React) running.

### Q: How do I run just one agent?
**A:** 
```bash
cd agents/builder-orchestrator
uip codedagent run --input-file ../../samples/invoice-exception/intake.json --output-file out/result.json
```

### Q: Where are the test results?
**A:** 
- Agent tests: Run `pytest agents/*/tests -q`
- API tests: Run `cd studio/api && pytest tests -q`
- Frontend tests: Run `cd studio/web && pnpm test`
- Evidence files: Check `docs/evidence/`

### Q: How do I regenerate documentation?
**A:**
```bash
cd workflows/documentation-factory-workflow
python run.py
```
Output goes to `docs/generated/`

### Q: Where are the demo videos?
**A:** `docs/assets/agenthack/`
- `agenthack-application-walkthrough-voiced.mp4` (main demo)
- `agenthack-workflow-run-demo.mp4` (workflow demo)

### Q: How do I create a new agent?
**A:** 
1. Copy structure from `agents/discovery-agent/`
2. Implement contracts from `agents/shared/agent_contracts.py`
3. Add to `solution/solution.uipx`
4. Add tests in `agents/your-agent/tests/`

### Q: How do I add a new UI mode?
**A:**
1. Create component in `studio/web/src/components/YourMode.tsx`
2. Add route in `studio/web/src/App.tsx`
3. Add API endpoint in `studio/api/app/routers/`
4. Add tests in `studio/web/src/__tests__/`

---

## Troubleshooting

### Issue: Tests fail
**Solution:**
```bash
# Ensure dependencies installed
pip install -e ".[dev,mcp]"
cd studio/web && pnpm install

# Run tests with verbose output
pytest -v
```

### Issue: UI won't start
**Solution:**
```bash
# Check if backend is running
curl http://localhost:8000/api/health

# Check if frontend dependencies installed
cd studio/web && pnpm install

# Clear cache and restart
pnpm run dev
```

### Issue: Agent execution fails
**Solution:**
```bash
# Check input format
cat samples/invoice-exception/intake.json

# Run with verbose logging
uip codedagent run --input-file input.json --output-file out.json --verbose

# Check agent tests
pytest agents/builder-orchestrator/tests -v
```

### Issue: Demo video playback
**Solution:**
- Use VLC or modern browser
- Check codec support (H.264)
- Subtitles: Load `.srt` file manually if needed

---

## External Links

### UiPath Resources
- [UiPath CLI Documentation](https://docs.uipath.com/automation-cloud/docs/cli)
- [UiPath Agent Builder](https://docs.uipath.com/agent-builder)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)

### Project Resources
- GitHub Repository: (Add your repo URL)
- Demo Video: `docs/assets/agenthack/`
- Forum Post: `docs/agenthack/forum-submission.md`

---

## Contact and Support

For questions about:
- **Architecture:** See `docs/ARCHITECTURE.md`
- **Usage:** See `docs/USER_GUIDE.md`
- **API:** See `docs/CAPABILITY_CONTRACT.md`
- **AgentHack:** See `docs/agenthack/`

---

**Last Updated:** May 17, 2026  
**Version:** 1.0

Navigate back to: [Project Overview](PROJECT_OVERVIEW.md) | [Main README](../README.md)
