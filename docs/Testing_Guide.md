# Testing Guide for UiPath Claude CLI

## Quick Start

### Run a Single Test with Auto-Cleanup
```powershell
.\run_test_with_cleanup.ps1 -TestInput "Create a workflow that logs Hello World" -TestID "BUILD-001"
```

### Manual Test Process

1. **Create test directory**
   ```powershell
   $testDir = "C:\Users\$env:USERNAME\projects\test-$(Get-Date -Format 'HHmmss')"
   mkdir $testDir
   cd $testDir
   ```

2. **Run the test**
   ```powershell
   echo "Your test input here`nexit" | uipath-claude chat --no-plan 2>&1 | Tee-Object output.txt
   ```

3. **Check results**
   ```powershell
   # Check created files
   Get-ChildItem -Recurse -Include "*.xaml","project.json"
   
   # Check validation
   Select-String -Path output.txt -Pattern "validation passed"
   
   # Check for specific features
   Select-String -Path output.txt -Pattern "\[ANSWERING\]|\[CLARIFYING\]"
   ```

4. **⚠️ IMPORTANT: Cleanup Studio processes**
   ```powershell
   cd C:\Users\DanielaRosenstein\projects\uipath-builder-agent
   .\cleanup_after_tests.ps1
   ```

## Why Cleanup is Necessary

Running tests creates UiPath Studio processes that:
- Validate XAML files
- Execute workflows
- Remain running in background consuming resources

### Processes to Close
- `UiPath.Studio` - Studio UI instances
- `UiPath.Executor` - Workflow execution engine
- `UiRobot` - Robot instances
- `UiPath.Agent` - Agent processes

### When to Run Cleanup
- ✅ After each test session
- ✅ Before running a new batch of tests
- ✅ If tests are failing unexpectedly
- ✅ If system performance is degraded

## Automated Testing Workflow

```powershell
# 1. Run tests
foreach ($test in $testList) {
    .\run_test_with_cleanup.ps1 -TestInput $test.Input -TestID $test.ID
}

# 2. Verify cleanup
Get-Process UiPath* -ErrorAction SilentlyContinue
# Should return nothing or minimal processes

# 3. Update Excel with results
python update_excel_with_5_tests.py
```

## Troubleshooting

### Test Hangs or Takes Too Long
```powershell
# Kill the CLI process
Get-Process uipath-claude -ErrorAction SilentlyContinue | Stop-Process -Force

# Kill Studio processes
.\cleanup_after_tests.ps1
```

### "Access Denied" or "File Locked" Errors
Usually caused by Studio processes holding file locks.
```powershell
# Force close all UiPath processes
Get-Process UiPath* | Stop-Process -Force

# Wait a moment
Start-Sleep -Seconds 2

# Try test again
```

### Too Many Studio Instances Running
```powershell
# Check how many
(Get-Process UiPath.Studio -ErrorAction SilentlyContinue).Count

# If more than 5, cleanup needed
.\cleanup_after_tests.ps1
```

## Best Practices

1. **Always cleanup between test batches**
   - Prevents resource exhaustion
   - Ensures consistent test environment

2. **Monitor process count**
   ```powershell
   Get-Process UiPath* | Measure-Object
   ```

3. **Use timeouts**
   - Tests shouldn't run more than 2-3 minutes
   - Use `-TimeoutSeconds` parameter

4. **Clean up test directories periodically**
   ```powershell
   # Remove test dirs older than 1 day
   Get-ChildItem C:\Users\$env:USERNAME\projects -Directory -Filter "test-*" |
       Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-1) } |
       Remove-Item -Recurse -Force
   ```

## Cleanup Script Details

### What it does
```powershell
# Gracefully closes Studio windows
$process.CloseMainWindow()

# Force kills if still running after 500ms
Stop-Process -Force

# Handles multiple instances
# Reports what was closed
```

### Safe to run anytime
- ✅ Won't affect production Studio usage (if not testing)
- ✅ Only closes test-related processes
- ✅ No data loss (files already saved)

## Example: Full Test Cycle with Cleanup

```powershell
# Start fresh
.\cleanup_after_tests.ps1

# Run 5 tests
$tests = @(
    "Create workflow with log message",
    "What is project.json?",
    "Automate my email",
    "Create Excel workflow",
    "Create workflow with variables"
)

foreach ($test in $tests) {
    Write-Host "Testing: $test" -ForegroundColor Yellow
    
    # Run test
    echo "$test`nexit" | uipath-claude chat --no-plan
    
    # Quick cleanup
    Get-Process UiPath.Executor -ErrorAction SilentlyContinue | Stop-Process -Force
    
    Start-Sleep -Seconds 2
}

# Final cleanup
.\cleanup_after_tests.ps1

# Verify clean
if (Get-Process UiPath* -ErrorAction SilentlyContinue) {
    Write-Host "⚠️  Some processes still running" -ForegroundColor Yellow
} else {
    Write-Host "✅ All clean!" -ForegroundColor Green
}
```

## Remember

**After every test session, run:**
```powershell
.\cleanup_after_tests.ps1
```

This ensures:
- No lingering processes
- Resources freed
- Clean slate for next tests
- System stability
