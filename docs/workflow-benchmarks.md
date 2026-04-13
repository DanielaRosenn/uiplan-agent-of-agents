# Workflow Benchmarks

## Validation Loop Runbook

Use this runbook when benchmarking generation quality or triaging validation behavior in
chat-driven workflow creation.

### 1) Generate and Materialize

1. Run chat generation for a workflow prompt.
2. Confirm at least one `.xaml` file is materialized in the chat output folder.

### 2) Validate

1. Run project validation (`validate_generated_project`) on the generated folder.
2. Capture these fields from the result:
   - `success`
   - `fully_validated`
   - `warnings` count
   - `errors` count

### 3) Apply Strict Validation Semantics

- Report **full pass** only when:
  - `success == True`, and
  - `fully_validated == True`
- Report **partial pass with warnings** when:
  - `success == True`, and
  - `fully_validated == False`
- Report **failure** when:
  - `success == False`

Never claim a full pass if diagnostics were partial.

### 4) Auto-Fix Loop (when failures exist)

1. Build a remediation prompt from validation errors.
2. Regenerate only the affected files.
3. Re-run validation.
4. Repeat up to the current hardcoded chat auto-fix limit (`max_fix_attempts=3`).
5. If still failing, record blocker and stop.

### 5) Benchmark Recording Template

For each benchmark run, record:

- Prompt identifier
- Generated artifact path
- Validation status (`full_pass`, `partial_pass`, `failed`)
- `success` / `fully_validated` raw values
- Warning count
- Error count
- Auto-fix attempts used
- Final blocker summary (if any)
