# Deployment Integration Guide

## Overview

The UiPath Claude Code CLI now has **fully integrated deployment capabilities** that allow you to create, test, and deploy workflows directly to UiPath Orchestrator or Studio Web through conversational chat.

## What's New

### 1. Deploy Tool for the LLM

The LLM can now call `deploy_to_orchestrator` during chat sessions to:
- Package UiPath projects as `.nupkg` files
- Upload packages to Orchestrator/Studio Web
- Deploy to specific folders and tenants
- Handle authentication and error reporting

### 2. Smart Process Tracking

The CLI automatically tracks UiPath Studio and Executor processes:
- Takes a snapshot of running processes at chat start
- Tracks new processes spawned during workflow testing
- Cleans up **only test-spawned processes** on exit
- Leaves your existing Studio instances open

### 3. Enhanced System Prompts

The LLM is now aware of deployment capabilities through updated system prompts that include:
- Deployment workflow instructions
- When to deploy vs when to just create workflows
- Environment variable requirements
- Error handling for common deployment issues

## Default configuration

Copy [`.env.example`](../.env.example) to `.env` and set your Automation Cloud account and tenant. The template uses **`UIPATH_TENANT_NAME=Test`** and a placeholder `YOUR_ACCOUNT` in the Orchestrator URL — replace both with values from your portal (they must match what `uipath auth` expects).

- **Orchestrator URL**: `https://cloud.uipath.com/<account>/<tenant>/orchestrator_`
- **Tenant**: Logical tenant name for auth (often `DefaultTenant`, `Test`, or a custom name)
- **Default folder**: `UIPATH_DEFAULT_FOLDER` for package deploy (`Dev`, `Prod`, `Test`, …)

## Prerequisites

Before using deployment features, ensure you have:

1. **UiPath CLI installed**: Download from [UiPath CLI Documentation](https://docs.uipath.com/automation-cloud/automation-cloud/latest/admin-guide/managing-automation-suite-using-the-cli)

2. **UiPath CLI authenticated**: 
   ```bash
   # Cloud — tenant must match UIPATH_TENANT_NAME (example: Test)
   uipath auth --cloud --tenant Test
   
   # On-premise Orchestrator
   uipath auth --base-url [orchestrator-url] --tenant [tenant-name]
   
   # Force new authentication (if token expired)
   uipath auth --cloud --tenant Test --force
   ```

3. **Environment variables** (set in `.env` or the shell):
   ```bash
   $env:UIPATH_ORCHESTRATOR_URL = "https://cloud.uipath.com/[org]/[tenant]/orchestrator_"
   $env:UIPATH_TENANT_NAME = "[tenant]"
   ```

## Usage

### Conversational Deployment

Simply ask the LLM to create and deploy workflows:

```
You: Create a simple workflow that logs "Hello World" and deploy it to Orchestrator

Agent: [Creates project, writes Main.xaml, validates, tests]
       [Calls deploy_to_orchestrator tool]
       ✓ Deployment successful! Package 'HelloWorld' v1.0.0 deployed to Shared folder.
```

The LLM automatically:
1. Creates the project structure
2. Writes the workflow XAML
3. Validates the workflow
4. Optionally tests with `run_workflow`
5. Calls `deploy_to_orchestrator` to package and upload
6. Reports deployment status

### Keywords that Trigger Deployment

The LLM recognizes these phrases:
- "deploy to orchestrator"
- "publish to orchestrator"
- "upload to studio web"
- "deploy to studio web"
- "deploy to production"
- "push to orchestrator"

### Process Cleanup

The CLI now has smart cleanup:

```bash
# Default: Automatically tracks and cleans up test processes
uipath-claude chat

# Disable cleanup (keep all processes running)
uipath-claude chat --no-track-processes
```

**What gets cleaned up:**
- UiPath.Studio.exe instances opened by `run_workflow` tool
- UiPath.Executor.exe instances spawned during testing

**What stays open:**
- Your existing Studio IDE
- Other Studio instances you opened manually
- Orchestrator Robot processes

## How It Works

### Deployment Flow

1. **User Request**: "Create workflow X and deploy it"
2. **LLM Planning**: Determines what to build
3. **Project Creation**: Calls `ensure_project_structure`
4. **Workflow Writing**: Calls `write_file` for Main.xaml
5. **Validation**: Calls `validate_file` to check syntax
6. **Auto-fix Loop**: If validation fails, LLM fixes errors
7. **Testing** (optional): Calls `run_workflow` to test
8. **Deployment**: Calls `deploy_to_orchestrator`
9. **Cleanup**: On chat exit, closes test processes

### Tool Registration

The `deploy_to_orchestrator` tool is registered in:
- `uipath_claude/tools/skill_execution_tools.py`
- Added to `get_skill_execution_tools()` list
- Available to all agentic execution paths

### Process Tracking

Process tracking is implemented via:
- `uipath_claude/utils/process_tracker.py`
- Stores PID snapshots in `~/.uipath-claude/test_processes.json`
- Tracks: `UiPath.Studio.exe`, `UiPath.Executor.exe`, `UiPathStudio.exe`

## Environment Configuration

### Required Variables

Set these in your shell profile or `.env`:

```bash
# Cloud Orchestrator
$env:UIPATH_ORCHESTRATOR_URL = "https://cloud.uipath.com/myorg/mytenant/orchestrator_"
$env:UIPATH_TENANT_NAME = "DefaultTenant"

# Optional: Specify account (if multiple accounts)
$env:UIPATH_ACCOUNT_NAME = "MyAccount"
```

### Optional Variables

```bash
# Disable streaming
$env:UIPATH_CHAT_STREAM = "0"

# Debug mode (shows more details)
$env:UIPATH_DEBUG_AGENT = "1"

# Custom output directory
$env:UIPATH_CHAT_OUTPUT_DIR = "C:\MyProjects\Generated"
```

## Examples

### Example 1: Create and Deploy Simple Workflow (Default to Test)

```
You: Create a workflow that writes today's date to a file and deploy it

Agent:
  [Thinking] Creating DateWriter workflow...
  ✓ Created project structure
  ✓ Wrote Main.xaml
  ✓ Validation passed (0 errors)
  ✓ Testing workflow...
  ✓ Workflow executed successfully
  [Deploying] Packaging and deploying to Orchestrator...
  ✓ Deployment successful!
  
  Package: DateWriter v1.0.0
  Folder: Test (default)
  Next: Create a process in Orchestrator to assign to robots.
```

### Example 2: Deploy to Prod Folder

```
You: Create a workflow that sends email notifications and deploy it to Prod

Agent:
  [Thinking] Creating EmailNotifier workflow...
  ✓ Created project structure
  ✓ Installed UiPath.Mail.Activities
  ✓ Wrote Main.xaml with Gmail integration
  ✓ Validation passed (0 errors)
  [Deploying] Packaging and deploying to Prod folder...
  ✓ Deployment successful!
  
  Package: EmailNotifier v1.0.0
  Folder: Prod
  Orchestrator: https://cloud.uipath.com/myorg/mytenant/
```

### Example 2b: Deploy to Dev Folder

```
You: Create a simple log message workflow and deploy it to Dev for testing

Agent:
  [Thinking] Creating LogMessage workflow...
  ✓ Created project structure
  ✓ Wrote Main.xaml
  ✓ Validation passed (0 errors)
  [Deploying] Packaging and deploying to Dev folder...
  ✓ Deployment successful!
  
  Package: LogMessage v1.0.0
  Folder: Dev
```

### Example 3: Deploy to Studio Web

```powershell
# Set Studio Web environment
$env:UIPATH_ORCHESTRATOR_URL = "https://cloud.uipath.com/myorg/mytenant"
$env:UIPATH_TENANT_NAME = "DefaultTenant"

# Run chat
uipath-claude chat
```

```
You: Create a simple Hello World workflow and deploy to Studio Web

Agent:
  [Thinking] Creating HelloWorld workflow...
  ✓ Created project structure
  ✓ Wrote Main.xaml
  ✓ Validation passed (0 errors)
  [Deploying] Packaging and deploying to Studio Web...
  ✓ Deployment successful!
  
  Package: HelloWorld v1.0.0
  Access your workflow at: https://cloud.uipath.com/myorg/mytenant
```

## Troubleshooting

### "UiPath CLI not found"

**Solution**: Install UiPath CLI:
```bash
# Download from:
https://docs.uipath.com/automation-cloud/automation-cloud/latest/admin-guide/managing-automation-suite-using-the-cli
```

### "Missing Orchestrator URL or tenant name"

**Solution**: Set environment variables:
```powershell
$env:UIPATH_ORCHESTRATOR_URL = "https://cloud.uipath.com/[org]/[tenant]/orchestrator_"
$env:UIPATH_TENANT_NAME = "DefaultTenant"
```

### "Authentication failed"

**Solution**: Authenticate UiPath CLI (tenant must match `UIPATH_TENANT_NAME`):
```bash
uipath auth --cloud --tenant Test

# Or your tenant name
uipath auth --cloud --tenant [your-tenant]

# Force new token if expired
uipath auth --cloud --tenant [your-tenant] --force
```

### "Packaging failed: Missing project.json"

**Solution**: Ensure the LLM created the project structure first. The deployment tool expects a valid UiPath project.

### "Deployment succeeded but package not visible"

**Issue**: Package deployed but no process created.

**Solution**: In Orchestrator UI:
1. Go to **Automation > Processes**
2. Click **Add Process**
3. Select your deployed package
4. Assign to folder and environments
5. Create process

### Process cleanup not working

**Symptoms**: Studio windows remain open after chat exit.

**Check**:
1. Is `--no-track-processes` flag used? (If yes, cleanup is disabled)
2. Are the Studio windows from before the chat started? (Only new ones are closed)
3. Check `~/.uipath-claude/test_processes.json` for tracked PIDs

**Manual cleanup**:
```powershell
# Kill all UiPath Studio and Executor processes
.\cleanup_after_tests.ps1
```

## Integration Points

### For Developers

If you're extending the CLI, here's how deployment integrates:

**1. Tool Registration**
```python
# In uipath_claude/tools/skill_execution_tools.py
@tool
def deploy_to_orchestrator(...):
    # Implementation
    pass

# Add to tool list
def get_skill_execution_tools() -> list:
    return [
        ...,
        deploy_to_orchestrator,
    ]
```

**2. System Prompt Updates**
```python
# In uipath_claude/query/agentic_executor.py
parts = [
    "## DEPLOYMENT",
    "You can deploy workflows to Orchestrator using deploy_to_orchestrator.",
    ...,
]
```

**3. Process Tracking Integration**
```python
# In uipath_claude/cli/app.py
try:
    from uipath_claude.utils.process_tracker import start_tracking_test
    before_pids = start_tracking_test()
    
    # ... chat loop ...
    
finally:
    finish_tracking_test(before_pids)
    close_test_processes()
```

## Next Steps

1. Test deployment with a simple workflow
2. Verify authentication with `uipath auth status`
3. Check deployed packages in Orchestrator UI
4. Create processes from deployed packages
5. Assign to robots and trigger executions

## Related Documentation

- [UiPath CLI Guide](https://docs.uipath.com/automation-cloud/automation-cloud/latest/admin-guide/managing-automation-suite-using-the-cli)
- [Orchestrator User Guide](https://docs.uipath.com/orchestrator)
- [Studio Web Documentation](https://docs.uipath.com/studio-web)
- [Testing Guide](./Testing_Guide.md)
- [Manual Evaluation](./MANUAL_EVAL_AND_QA.md)