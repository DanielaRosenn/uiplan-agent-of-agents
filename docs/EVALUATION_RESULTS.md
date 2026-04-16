# Evaluation Results

Test results from CLI benchmark runs with agentic execution mode.

## Test Environment

- **Date**: April 15, 2026
- **Agent Version**: dev
- **Max Iterations**: 25
- **Debug Mode**: Enabled
- **UiPath CLI**: uip rpa (local)

## Test Results Summary

| Test | Status | Iterations | Validation | Duration | Notes |
|------|--------|------------|------------|----------|-------|
| Outlook Email Workflow | Partial | 8 | Failed | 153s | Package install error, validation issues |
| Excel Read/Write | **PASS** | 11 | **0 errors** | 253s | Full success |
| Web Automation | Running | TBD | TBD | TBD | In progress |

## Test 1: Outlook Email Workflow

**Prompt**: "Create a complete UiPath project that reads the first 5 emails from Outlook and logs each subject. Set up project.json and install required packages."

**Session ID**: 20260414-160951-7414606c

**Execution Flow:**
1. Iteration 1-2: Attempted `run_uip_command` (error: unexpected argument 'v__args')
3. Iteration 3: Attempted `install_package` (error: no project.json)
4. Iteration 4: Called `ensure_project_structure` (success)
5. Iteration 5: Attempted `install_package` (error: NullReferenceException)
6. Iteration 6: Called `write_file` for Main.xaml (success, 1811 bytes)
7. Iteration 7: Called `validate_file` (failed: activity missing or could not be loaded)
8. Iteration 8: Agent gave up, suggested manual Studio validation

**Issues:**
- `run_uip_command` tool has argument passing issue
- Package installation failed with NullReferenceException
- Validation failed due to missing/incorrect activity

**Files Created:**
- `Main.xaml` (1811 bytes)
- `project.json`

**Verdict**: Partial success - project structure created but validation failed.

## Test 2: Excel Read/Write Workflow

**Prompt**: "Create a complete UiPath project that reads data from an Excel file and writes it to another sheet. Set up project.json and install required packages."

**Session ID**: 20260414-161008-bcb53f2f

**Execution Flow:**
1. Iteration 1-2: Attempted `run_uip_command` (error: unexpected argument 'v__args')
2. Iteration 3: Called `ensure_project_structure` (success)
3. Iteration 4: Attempted `install_package` (error: project already loaded)
4. Iteration 5: Attempted `run_uip_command` (error: unexpected argument)
5. Iteration 6: Called `install_package` (success - UiPath.Excel.Activities installed)
6. Iteration 7: Attempted `write_file` with escaped XML (error: XML parsing)
7. Iteration 8: Retried `write_file` (error: XML parsing)
8. Iteration 9: Called `write_file` with correct XML (success)
9. Iteration 10: Called `validate_file` (**PASSED: 0 errors**)
10. Iteration 11: Agent confirmed success

**Files Created:**
- `ExcelDataTransfer/Main.xaml` (valid XAML)
- `ExcelDataTransfer/project.json` (with UiPath.Excel.Activities dependency)

**Verdict**: **FULL SUCCESS** - Project created, validated, and ready to use.

## Test 3: Web Automation

**Prompt**: "Create a complete UiPath project that opens a browser, navigates to google.com and types a search query. Set up project.json and install required packages."

**Session ID**: 20260414-161440-28dd087b

**Status**: In progress (still running at time of documentation)

## New Evaluation Cases Added (April 15, 2026)

The following 4 new evaluation cases were added to the `EvaluationDataset` to expand the benchmark suite to 7 total cases:

### 1. Data Manipulation (Medium)
**Prompt**: "Create a UiPath workflow that reads a CSV file into a DataTable, filters it to keep only rows where Status is 'Active', and writes the result to a new CSV file"
**Expected Activities**: `ReadCsvFile`, `FilterDataTable`, `WriteCsvFile`
**Expected Packages**: `UiPath.System.Activities`

### 2. API & JSON Parsing (Hard)
**Prompt**: "Create a UiPath workflow that makes an HTTP GET request to a public API, parses the JSON response, and logs a specific field"
**Expected Activities**: `HttpClient`, `DeserializeJson`, `LogMessage`
**Expected Packages**: `UiPath.WebAPI.Activities`

### 3. File System Operations (Easy)
**Prompt**: "Create a UiPath workflow that gets all PDF files from an 'Input' folder and moves them to an 'Archive' folder using a For Each loop"
**Expected Activities**: `ForEach`, `MoveFile`
**Expected Packages**: `UiPath.System.Activities`

### 4. Exception Handling (Medium)
**Prompt**: "Create a UiPath workflow with a Try Catch block that attempts to read a text file. If a FileNotFoundException occurs, it should log a warning message instead of failing"
**Expected Activities**: `TryCatch`, `ReadTextFile`, `LogMessage`
**Expected Packages**: `UiPath.System.Activities`

## Debug Output Improvements

The new `AgenticProgressReporter` provides much more readable output:

### Before (old format):
```
[DEBUG] Iteration 3/15
[DEBUG] Tool call: install_package({"project_dir": ".", "package_id": "UiPath.Mail.Activities"})
[DEBUG] Tool result: Successfully installed UiPath.Mail.Activities...
```

### After (new format):
```
+------------------------------------------------------------------------------+
| Iteration 3 of 25                              [=>        ]                  |
+------------------------------------------------------------------------------+

   install_package
         -> UiPath.Mail.Activities
     Successfully installed UiPath.Mail.Activities
```

**Improvements:**
- Clear iteration progress bar
- Visual separation between iterations
- Indented tool arguments for readability
- Truncated output with key information highlighted
- Color-coded status (would show in terminal with colors)

## Key Findings

### Successes
1. **Agentic loop works**: Agent iterates, calls tools, observes results
2. **Self-correction**: Agent retries with different approaches
3. **Validation-driven**: Continuous validation feedback guides generation
4. **Excel workflow**: Full end-to-end success with 0 validation errors

### Issues
1. **run_uip_command tool**: Argument passing error ('v__args')
2. **Package installation**: Intermittent NullReferenceException
3. **Activity discovery**: Agent doesn't always find correct activity syntax
4. **Outlook workflow**: Validation failures persist

### Recommendations
1. Fix `run_uip_command` argument handling
2. Improve activity documentation bundling
3. Add more examples to skill templates
4. Increase MAX_ITERATIONS for complex workflows (already done: 25)

## Evaluation Metrics

| Metric | Value |
|--------|-------|
| **Success Rate** | 50% (1/2 completed tests) |
| **Average Iterations** | 9.5 |
| **Average Duration** | 203s |
| **Validation Pass Rate** | 50% |
| **Tool Error Rate** | 30% (run_uip_command failures) |

## Next Steps

1. Fix `run_uip_command` tool argument handling
2. Run remaining web automation test
3. Run the 4 newly added evaluation cases (Data Manipulation, API, File System, Exception Handling)
4. Implement trajectory tracking for evaluation
5. Set up automated evaluation runs