# Quick Start Guide

**Get up and running in 5-10 minutes**

---

## Choose Your Path

### 🎬 "Just show me the demo" (5 minutes)

1. **Watch the video:**
   ```
   📹 docs/assets/agenthack/agenthack-application-walkthrough-voiced.mp4
   Duration: 3-4 minutes
   ```

2. **Review the script:**
   ```
   📄 docs/agenthack/demo-script.md
   ```

3. **Done!** You now understand what the system does.

---

### 💻 "I want to run it locally" (10 minutes)

#### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

#### Setup

**Windows:**
```powershell
# Clone the repository
git clone <repo-url>
cd uipath-builder-agent

# Run automated setup
.\ops\scripts\cursor-quickstart.ps1

# Verify installation
uipath-claude doctor
```

**Linux/Mac:**
```bash
# Clone the repository
git clone <repo-url>
cd uipath-builder-agent

# Run automated setup
bash ops/scripts/cursor-quickstart.sh

# Verify installation
uipath-claude doctor
```

#### Start the System

**Terminal 1 - Backend:**
```bash
cd studio/api
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd studio/web
pnpm dev
```

**Access the UI:**
```
http://localhost:5174
```

#### Run a Test

```bash
cd agents/builder-orchestrator
uip codedagent run \
  --input-file ../../samples/invoice-exception/intake.json \
  --output-file out/test-run.json
```

---

### 🧪 "I want to validate it works" (5 minutes)

```bash
# Run all tests
pytest agents/*/tests -q             # Expect: 18 passed
cd studio/api && pytest tests -q     # Expect: 201 passed
cd studio/web && pnpm test           # Expect: 16 passed

# Check evidence
ls docs/evidence/

# Run local verification script
python ops/scripts/verify-local.ps1
```

---

### 📚 "I want to understand the architecture" (15 minutes)

**Read in this order:**

1. **High-level overview (5 min):**
   ```
   docs/PROJECT_OVERVIEW.md
   ```

2. **System diagrams (5 min):**
   ```
   docs/SYSTEM_DIAGRAM.md
   ```

3. **Architecture deep dive (5 min):**
   ```
   docs/ARCHITECTURE.md
   ```

---

### 🏗️ "I want to build something" (30 minutes)

#### Understand the Agent System

**Read agent documentation:**
```bash
# Orchestrator (main coordinator)
cat agents/builder-orchestrator/README.md

# Agent contracts (shared types)
cat agents/shared/agent_contracts.py

# Review graph visualization
cat agents/builder-orchestrator/agent.mermaid
```

#### Create a Simple Agent

**Template:**
```python
# agents/my-agent/main.py
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class MyState(TypedDict):
    input: str
    output: str

def process_node(state: MyState) -> MyState:
    """Process the input"""
    state["output"] = f"Processed: {state['input']}"
    return state

# Build graph
graph = StateGraph(MyState)
graph.add_node("process", process_node)
graph.add_edge(START, "process")
graph.add_edge("process", END)

# Compile
app = graph.compile()
```

**Test it:**
```python
# agents/my-agent/tests/test_my_agent.py
from agents.my_agent.main import app

def test_my_agent():
    result = app.invoke({"input": "test"})
    assert result["output"] == "Processed: test"
```

**Run:**
```bash
pytest agents/my-agent/tests -v
```

---

### 🎯 "I'm submitting to AgentHack" (10 minutes)

#### Pre-submission Checklist

**1. Validate everything works:**
```bash
pytest agents/*/tests studio/api/tests -q
cd studio/web && pnpm test
```

**2. Review submission materials:**
```
✅ docs/agenthack/submission-checklist.md   (Final checklist)
✅ docs/agenthack/submission-materials.md   (Asset list)
✅ docs/agenthack/forum-submission.md       (Forum post)
✅ docs/agenthack/pitch-deck-outline.md     (Pitch deck)
✅ docs/agenthack/judging-matrix.md         (Criteria mapping)
```

**3. Verify demo assets:**
```
✅ Video: docs/assets/agenthack/agenthack-application-walkthrough-voiced.mp4
✅ Subtitles: docs/assets/agenthack/agenthack-application-walkthrough.srt
✅ Script: docs/agenthack/demo-script.md
✅ UI Showcase: docs/assets/agentops-builder-ui.gif
```

**4. Final check:**
```bash
# All tests pass?
pytest -q  # Should see: 235 tests passed

# Evidence files present?
ls docs/evidence/

# Demo video plays?
# Open in VLC or browser
```

---

## Common Tasks

### Task 1: Generate Documentation

```bash
cd workflows/documentation-factory-workflow
python run.py
```

**Output:**
- `docs/generated/pdd.md`
- `docs/generated/sdd.md`
- `docs/generated/add.md`
- `docs/generated/test-plan.md`
- `docs/generated/deployment-runbook.md`
- `docs/generated/monitoring-runbook.md`

### Task 2: Collect Evidence

```bash
# Run evidence collection workflows
cd workflows/cicd-telemetry-workflow && python run.py
cd ../orchestrator-monitor-workflow && python run.py
cd ../evidence-api-workflow && python run.py

# Check evidence
ls -la docs/evidence/
```

### Task 3: Run Smoke Tests

```bash
cd workflows/smoke-test-workflow
python run.py --input ../evidence-api-workflow/out/handoff-summary.json
```

### Task 4: Package Solution

```bash
# Validate solution structure
cat solution/solution.uipx

# Check bindings
cat solution/bindings/dev.json

# Review solution design
cat solution/docs/solution-design.md
```

### Task 5: Record Demo Video

```bash
# Start the UI first
cd studio/web && pnpm dev

# In another terminal, record
node ../../ops/scripts/record-agenthack-application-demo.mjs http://127.0.0.1:5174/

# Add voiceover (if needed)
python ops/scripts/add-uiplan-voiceover.py \
  --video docs/assets/recording.webm \
  --srt docs/assets/recording.srt \
  --output docs/assets/recording-voiced.mp4
```

---

## Troubleshooting

### Issue: "Module not found"

```bash
# Reinstall dependencies
pip install -e ".[dev,mcp]"
cd studio/web && pnpm install
```

### Issue: "Port already in use"

```bash
# Check what's running on ports
netstat -ano | findstr :8000
netstat -ano | findstr :5174

# Kill processes or change ports
# Backend: uvicorn app.main:app --port 8001
# Frontend: pnpm dev --port 5175
```

### Issue: "Tests failing"

```bash
# Run with verbose output
pytest -v

# Run specific test
pytest agents/builder-orchestrator/tests/test_orchestrator.py -v

# Check logs
cat agents/builder-orchestrator/__uipath/state.db
```

### Issue: "UI not loading"

```bash
# Check backend health
curl http://localhost:8000/api/health

# Clear frontend cache
cd studio/web
rm -rf node_modules/.vite
pnpm dev
```

### Issue: "Agent execution fails"

```bash
# Validate input format
cat samples/invoice-exception/intake.json

# Run with verbose logging
uip codedagent run --input-file input.json --verbose

# Check agent tests
pytest agents/builder-orchestrator/tests -v
```

---

## Next Steps

### For Learning
1. Read `docs/PROJECT_OVERVIEW.md` (complete guide)
2. Watch demo video (3 min)
3. Explore `docs/SYSTEM_DIAGRAM.md` (visual guide)
4. Study `docs/ARCHITECTURE.md` (technical details)

### For Development
1. Set up local environment (10 min)
2. Run all tests (validate setup)
3. Review agent code in `agents/*/main.py`
4. Create a test agent (follow template above)

### For Submission
1. Complete `docs/agenthack/submission-checklist.md`
2. Validate all tests pass
3. Review demo assets
4. Prepare forum post from `docs/agenthack/forum-submission.md`

---

## Key File Locations

| What | Where |
|------|-------|
| **Main README** | `README.md` |
| **Project Overview** | `docs/PROJECT_OVERVIEW.md` |
| **Navigation Guide** | `docs/NAVIGATION_GUIDE.md` |
| **System Diagrams** | `docs/SYSTEM_DIAGRAM.md` |
| **Architecture** | `docs/ARCHITECTURE.md` |
| **Demo Video** | `docs/assets/agenthack/agenthack-application-walkthrough-voiced.mp4` |
| **Demo Script** | `docs/agenthack/demo-script.md` |
| **Submission Checklist** | `docs/agenthack/submission-checklist.md` |
| **Orchestrator Code** | `agents/builder-orchestrator/main.py` |
| **Agent Contracts** | `agents/shared/agent_contracts.py` |
| **UI Components** | `studio/web/src/components/` |
| **API Routes** | `studio/api/app/routers/` |
| **Evidence** | `docs/evidence/` |
| **Generated Docs** | `docs/generated/` |

---

## Command Cheat Sheet

```bash
# Setup
./ops/scripts/cursor-quickstart.ps1        # Windows setup
bash ops/scripts/cursor-quickstart.sh      # Linux/Mac setup

# Start services
cd studio/api && uvicorn app.main:app --reload    # Backend
cd studio/web && pnpm dev                          # Frontend

# Run tests
pytest agents/*/tests -q                           # Agent tests
cd studio/api && pytest tests -q                   # API tests
cd studio/web && pnpm test                         # Frontend tests

# Run orchestrator
cd agents/builder-orchestrator
uip codedagent run --input-file ../../samples/invoice-exception/intake.json

# Generate docs
cd workflows/documentation-factory-workflow && python run.py

# Collect evidence
cd workflows/evidence-api-workflow && python run.py

# Validate
python ops/scripts/verify-local.ps1

# Health check
uipath-claude doctor
```

---

## Support

For detailed information, see:
- **Complete Guide:** `docs/PROJECT_OVERVIEW.md`
- **Navigation:** `docs/NAVIGATION_GUIDE.md`
- **Diagrams:** `docs/SYSTEM_DIAGRAM.md`
- **Architecture:** `docs/ARCHITECTURE.md`

---

**Last Updated:** May 17, 2026  
**Version:** 1.0
