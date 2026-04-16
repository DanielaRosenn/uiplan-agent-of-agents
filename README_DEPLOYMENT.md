# Deployment Integration - Ready to Use

## What's Now Integrated

The `uipath-claude chat` CLI can now:
1. **Deploy workflows** to Orchestrator/Studio Web conversationally
2. **Smart cleanup** - closes only test-spawned Studio processes, leaving your IDE open

## Quick Start

### 1. Configure Orchestrator (required)

Copy [`.env.example`](.env.example) to `.env` and set your Automation Cloud values:

- **`UIPATH_ORCHESTRATOR_URL`**: `https://cloud.uipath.com/<YOUR_ACCOUNT>/<TENANT>/orchestrator_` (both path segments come from your portal).
- **`UIPATH_TENANT_NAME`**: Same logical tenant name used for CLI auth (template default is `Test`; change if yours differs).
- **`UIPATH_DEFAULT_FOLDER`**: Orchestrator folder for packages (`Dev`, `Prod`, `Test`, `Shared`, …).

### 2. Authenticate UiPath CLI

```bash
# Opens browser for interactive OAuth (tenant must match UIPATH_TENANT_NAME)
uipath auth --cloud --tenant Test
```

### 3. Start Chat

```bash
uipath-claude chat
```

### 4. Deploy Workflows

```
You: Create a simple log message workflow and deploy it

Agent: [Creates workflow, validates, deploys]
       ✓ Deployment successful! Package 'LogMessage' v1.0.0 deployed to Test folder.

You: Deploy it to Prod instead

Agent: ✓ Deployment successful! Package 'LogMessage' v1.0.0 deployed to Prod folder.
```

### 5. Override Defaults (Optional)

For different Orchestrator setups:

```powershell
# Custom Orchestrator
$env:UIPATH_ORCHESTRATOR_URL = "https://cloud.uipath.com/[org]/[tenant]/orchestrator_"
$env:UIPATH_TENANT_NAME = "[tenant]"
```

## What Changed

### Files Modified

1. **`uipath_claude/tools/skill_execution_tools.py`**
   - Added `deploy_to_orchestrator` tool
   - Tool is now available to the LLM during chat

2. **`uipath_claude/query/agentic_executor.py`**
   - Updated system prompt with deployment instructions
   - LLM now knows when and how to deploy

3. **`uipath_claude/cli/app.py`**
   - Added process tracking at chat start
   - Smart cleanup on chat exit
   - Only closes test-spawned Studio processes

## Features

### 1. Conversational Deployment

The LLM recognizes these phrases:
- "deploy to orchestrator"
- "publish to orchestrator"  
- "upload to studio web"
- "deploy to production"

Example:
```
You: Build a workflow that sends emails and deploy it to Production folder

Agent: ✓ Created EmailSender workflow
       ✓ Installed UiPath.Mail.Activities
       ✓ Validation passed
       ✓ Deployed to Production folder
```

### 2. Smart Process Cleanup

On chat exit, the CLI:
- Closes Studio.exe instances opened by `run_workflow`
- Closes Executor.exe spawned during testing
- **Keeps** your Studio IDE and other manually opened instances

Disable if needed:
```bash
uipath-claude chat --no-track-processes
```

### 3. Deployment Workflow

1. User requests workflow creation + deployment
2. LLM creates project structure
3. LLM writes workflow XAML
4. LLM validates (auto-fixes errors)
5. LLM optionally tests with `run_workflow`
6. LLM calls `deploy_to_orchestrator` tool
7. Tool packages project as `.nupkg`
8. Tool uploads to Orchestrator/Studio Web
9. LLM reports deployment status

## Testing

### Verification Checks

```powershell
# 1. Verify tool is registered
cd uipath-builder-agent
python -c "from uipath_claude.tools.skill_execution_tools import get_skill_execution_tools; print('deploy_to_orchestrator' in [t.name for t in get_skill_execution_tools()])"
# Expected: True

# 2. Verify process tracker
python -c "from uipath_claude.utils.process_tracker import ProcessTracker; print('OK')"
# Expected: OK

# 3. Check CLI flag
uipath-claude chat --help
# Expected: Should show --track-processes flag
```

### Manual Test

```bash
# Terminal 1: Start chat
uipath-claude chat

# In chat:
You: Create a simple Hello World workflow and deploy it

# Expected output:
# - Project created
# - Main.xaml written
# - Validation passed
# - Deployment successful with package name and version

# Exit chat
exit

# Verify: Test-spawned Studio processes closed, your IDE still open
```

## Documentation

- **Complete Guide**: [docs/DEPLOYMENT_INTEGRATION.md](docs/DEPLOYMENT_INTEGRATION.md)
- **Testing Guide**: [docs/Testing_Guide.md](docs/Testing_Guide.md)
- **Integration Details**: [INTEGRATION_COMPLETE.md](INTEGRATION_COMPLETE.md)

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Tool not found | `pip install -e .` to reinstall |
| CLI not found | `uipath --version` to verify installation |
| Auth failed | `uipath auth --cloud --tenant <your UIPATH_TENANT_NAME>` to authenticate |
| Missing env vars | Set `UIPATH_ORCHESTRATOR_URL` and `UIPATH_TENANT_NAME` in `.env` |
| All Studio closed | Bug - report with logs |

## Prerequisites

- ✅ Python 3.12+ with `uipath-claude` installed
- ✅ UiPath CLI installed and in PATH
- ✅ UiPath CLI authenticated (`uipath auth status`)
- ✅ Environment variables set (Orchestrator URL, tenant)
- ✅ Valid Orchestrator/Studio Web access

## Architecture

```
Chat Input → Intent Classification → Agentic Executor → LLM with Tools
                                                          ├─ ensure_project_structure
                                                          ├─ write_file
                                                          ├─ validate_file
                                                          ├─ run_workflow
                                                          └─ deploy_to_orchestrator ← NEW
                                                              ├─ Pack (uipath package pack)
                                                              └─ Deploy (uipath package deploy)
```

## Status

| Component | Status |
|-----------|--------|
| Tool Registration | ✅ Complete |
| System Prompts | ✅ Complete |
| Process Tracking | ✅ Complete |
| Documentation | ✅ Complete |
| Unit Tests | ⏳ Pending |
| Integration Tests | ⏳ Pending |
| User Testing | ⏳ Ready |

## Next Steps

1. **Test**: Try creating and deploying a simple workflow
2. **Verify**: Check package appears in Orchestrator
3. **Feedback**: Report any issues or unexpected behavior
4. **Iterate**: Refine based on real-world usage

---

**Ready to use!** Start with `uipath-claude chat` and try deploying a workflow.