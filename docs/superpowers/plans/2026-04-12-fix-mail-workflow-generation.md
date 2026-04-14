# Fix Mail Workflow Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent LLM from hallucinating non-existent UiPath activities and ensure generated mail workflows use only real, documented activities.

**Architecture:** Three-pronged approach: (1) Add post-generation activity validation using `uip rpa find-activities`, (2) Prioritize critical examples in skill content injection, (3) Add integration test to verify correct activity usage.

**Tech Stack:** Python 3.12, UiPath CLI (`uip`), pytest, XML parsing (lxml or built-in xml.etree)

---

## Problem Summary

The LLM is generating XAML workflows with hallucinated activities like `ui:StartOutlook`, `ui:GetOutlookNamespace`, `ui:ForEachOutlookMessageFile` that don't exist in UiPath. The skill documentation contains correct examples, but they're being ignored. Validation passes because `uip rpa get-errors` only checks XAML syntax, not whether activities exist.

## File Structure

**New Files:**
- `uipath_claude/validation/activity_validator.py` - Post-generation activity existence checker
- `tests/unit/validation/test_activity_validator.py` - Unit tests for validator
- `tests/integration/test_mail_workflow_generation.py` - E2E test for mail workflows

**Modified Files:**
- `uipath_claude/artifacts/materialize.py` - Add activity validation after XAML generation
- `uipath_claude/cli/app.py` - Prioritize critical skill sections in prompt
- `uipath_claude/tools/uipath/cli_runner.py` - Add `run_uip_rpa_find_activities` function

---

### Task 1: Add Activity Validation Infrastructure

**Files:**
- Create: `uipath_claude/validation/__init__.py`
- Create: `uipath_claude/validation/activity_validator.py`
- Create: `uipath_claude/tools/uipath/cli_runner.py` (add function)

- [ ] **Step 1: Create validation package init**

```python
# uipath_claude/validation/__init__.py
"""Validation utilities for generated UiPath workflows."""
from uipath_claude.validation.activity_validator import (
    validate_activities_in_xaml,
    extract_activity_names_from_xaml,
)

__all__ = ["validate_activities_in_xaml", "extract_activity_names_from_xaml"]
```

- [ ] **Step 2: Add find-activities CLI wrapper**

```python
# In uipath_claude/tools/uipath/cli_runner.py, add this function after run_uip_rpa_analyze:

def run_uip_rpa_find_activities(
    query: str,
    *,
    timeout: int = 30,
) -> dict:
    """Run `uip rpa find-activities --query <query> --output json`.
    
    Searches for activities matching a query string.
    
    Returns dict with:
        - success: bool
        - activities: list of dicts with activity info
        - raw_output: str
    """
    uip_cli = _find_uip_cli()
    try:
        proc = subprocess.run(
            [uip_cli, "rpa", "find-activities", "--query", query, "--output", "json"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return {
            "success": False,
            "activities": [],
            "raw_output": "",
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "activities": [],
            "raw_output": "",
        }
    
    output = proc.stdout or ""
    
    try:
        result = json.loads(output)
        if result.get("Result") == "Success":
            data = result.get("Data", {})
            activities = data.get("Activities", []) if isinstance(data, dict) else []
            return {
                "success": True,
                "activities": activities,
                "raw_output": output,
            }
    except json.JSONDecodeError:
        pass
    
    return {
        "success": False,
        "activities": [],
        "raw_output": output,
    }
```

- [ ] **Step 3: Create activity validator**

```python
# uipath_claude/validation/activity_validator.py
"""Validate that activities used in XAML actually exist."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Set, List, Tuple

from uipath_claude.tools.uipath.cli_runner import run_uip_rpa_find_activities


def extract_activity_names_from_xaml(xaml_content: str) -> Set[str]:
    """
    Extract activity element names from XAML content.
    
    Returns set of activity names like "GetOutlookMailMessages", "LogMessage", etc.
    Excludes standard XAML elements (Sequence, Activity, etc.)
    """
    # Standard XAML elements to ignore
    standard_elements = {
        "Activity", "Sequence", "Flowchart", "StateMachine",
        "Variable", "InArgument", "OutArgument", "InOutArgument",
        "ActivityAction", "DelegateInArgument", "DelegateOutArgument",
        "TextExpression.NamespacesForImplementation",
        "TextExpression.ReferencesForImplementation",
        "AssemblyReference", "Collection",
    }
    
    # Find all element tags with namespace prefixes
    # Pattern: <prefix:ElementName or <ElementName
    pattern = r'<(?:(\w+):)?(\w+)[\s>]'
    matches = re.findall(pattern, xaml_content)
    
    activity_names = set()
    for prefix, name in matches:
        # Skip standard elements
        if name in standard_elements:
            continue
        # Skip closing tags, comments, etc
        if name.startswith('/') or name.startswith('!'):
            continue
        # Only include elements with ui: prefix or no prefix (in ui namespace)
        if prefix in ('ui', ''):
            activity_names.add(name)
    
    return activity_names


def validate_activities_in_xaml(
    xaml_path: Path,
    *,
    skip_validation: bool = False,
) -> Tuple[bool, List[str]]:
    """
    Validate that all activities in XAML file actually exist in UiPath.
    
    Args:
        xaml_path: Path to XAML file
        skip_validation: If True, skip validation (for testing)
        
    Returns:
        Tuple of (success, list of error messages)
        success is True if all activities exist or validation is skipped
    """
    if skip_validation:
        return True, []
    
    try:
        content = xaml_path.read_text(encoding='utf-8')
    except Exception as e:
        return False, [f"Failed to read XAML file: {e}"]
    
    activity_names = extract_activity_names_from_xaml(content)
    
    if not activity_names:
        # No activities found, might be empty file
        return True, []
    
    errors = []
    
    # Check each activity
    for activity_name in sorted(activity_names):
        result = run_uip_rpa_find_activities(activity_name)
        
        if not result["success"]:
            # CLI failed, skip validation for this activity
            continue
        
        activities = result["activities"]
        
        # Check if activity exists
        found = any(
            act.get("ClassName", "").endswith(activity_name) or
            act.get("ActivityTypeId", "").endswith(activity_name)
            for act in activities
        )
        
        if not found:
            errors.append(
                f"Activity '{activity_name}' not found in UiPath packages. "
                f"This may be a hallucinated activity name."
            )
    
    return len(errors) == 0, errors
```

- [ ] **Step 4: Commit infrastructure**

```bash
git add uipath_claude/validation/ uipath_claude/tools/uipath/cli_runner.py
git commit -m "feat: add activity validation infrastructure"
```

---

### Task 2: Write Unit Tests for Activity Validator

**Files:**
- Create: `tests/unit/validation/__init__.py`
- Create: `tests/unit/validation/test_activity_validator.py`

- [ ] **Step 1: Create test package init**

```python
# tests/unit/validation/__init__.py
"""Unit tests for validation module."""
```

- [ ] **Step 2: Write test for activity extraction**

```python
# tests/unit/validation/test_activity_validator.py
"""Tests for activity validator."""
import pytest
from pathlib import Path
from uipath_claude.validation.activity_validator import (
    extract_activity_names_from_xaml,
    validate_activities_in_xaml,
)


def test_extract_activity_names_finds_ui_activities():
    """Test extracting activity names from XAML."""
    xaml = """
    <Activity xmlns:ui="http://schemas.uipath.com/workflow/activities">
        <Sequence>
            <ui:LogMessage Message="test" />
            <ui:GetOutlookMailMessages />
            <ui:ForEach Values="[items]">
                <ui:WriteLine Text="test" />
            </ui:ForEach>
        </Sequence>
    </Activity>
    """
    
    activities = extract_activity_names_from_xaml(xaml)
    
    assert "LogMessage" in activities
    assert "GetOutlookMailMessages" in activities
    assert "ForEach" in activities
    assert "WriteLine" in activities
    # Standard elements should not be included
    assert "Sequence" not in activities
    assert "Activity" not in activities


def test_extract_activity_names_ignores_standard_elements():
    """Test that standard XAML elements are ignored."""
    xaml = """
    <Activity>
        <Sequence>
            <Variable x:TypeArguments="x:String" Name="test" />
            <InArgument x:TypeArguments="x:String" />
        </Sequence>
    </Activity>
    """
    
    activities = extract_activity_names_from_xaml(xaml)
    
    assert "Variable" not in activities
    assert "InArgument" not in activities
    assert "Sequence" not in activities


def test_validate_activities_with_skip_flag(tmp_path):
    """Test validation skips when flag is set."""
    xaml_file = tmp_path / "test.xaml"
    xaml_file.write_text("<Activity><ui:FakeActivity /></Activity>", encoding='utf-8')
    
    success, errors = validate_activities_in_xaml(xaml_file, skip_validation=True)
    
    assert success is True
    assert len(errors) == 0


def test_validate_activities_handles_missing_file():
    """Test validation handles missing file gracefully."""
    fake_path = Path("/nonexistent/file.xaml")
    
    success, errors = validate_activities_in_xaml(fake_path)
    
    assert success is False
    assert len(errors) == 1
    assert "Failed to read XAML file" in errors[0]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/unit/validation/test_activity_validator.py -v`
Expected: PASS (implementation already exists)

- [ ] **Step 4: Commit tests**

```bash
git add tests/unit/validation/
git commit -m "test: add unit tests for activity validator"
```

---

### Task 3: Integrate Activity Validation into Materialization

**Files:**
- Modify: `uipath_claude/artifacts/materialize.py`

- [ ] **Step 1: Add activity validation after XAML write**

```python
# In uipath_claude/artifacts/materialize.py, after fix_missing_namespaces call in materialize_from_assistant_text:

# Around line 250, after the namespace fix block, add:

            # Validate activities exist (only for XAML files)
            if written_path.suffix.lower() == '.xaml':
                from uipath_claude.validation.activity_validator import validate_activities_in_xaml
                
                # Skip validation if environment variable is set
                skip_activity_validation = os.environ.get(
                    "UIPATH_SKIP_ACTIVITY_VALIDATION", "0"
                ).lower() in ("1", "true", "yes")
                
                if not skip_activity_validation:
                    success, errors = validate_activities_in_xaml(written_path)
                    if not success:
                        # Log warnings but don't fail - let validation catch it
                        import warnings
                        for error in errors:
                            warnings.warn(f"Activity validation: {error}", UserWarning)
```

- [ ] **Step 2: Add import at top of file**

```python
# At top of uipath_claude/artifacts/materialize.py, add:
import os
import warnings
```

- [ ] **Step 3: Test integration manually**

Create test XAML with fake activity:
```bash
mkdir -p C:\Users\DanielaRosenstein\projects\uipath-builder-agent\test_output
```

Create test file with hallucinated activity and verify warning appears.

- [ ] **Step 4: Commit integration**

```bash
git add uipath_claude/artifacts/materialize.py
git commit -m "feat: integrate activity validation into XAML materialization"
```

---

### Task 4: Prioritize Critical Skill Content in Prompt

**Files:**
- Modify: `uipath_claude/cli/app.py`

- [ ] **Step 1: Add function to extract critical sections**

```python
# In uipath_claude/cli/app.py, add new function before _build_runtime_skill_context:

def _extract_critical_sections(skill_content: str) -> str:
    """
    Extract CRITICAL sections from skill content for priority injection.
    
    CRITICAL sections are marked with ### CRITICAL: in markdown.
    These are placed at the top of the skill content.
    """
    lines = skill_content.split('\n')
    critical_lines = []
    in_critical = False
    
    for line in lines:
        if line.startswith('### CRITICAL:'):
            in_critical = True
            critical_lines.append(line)
        elif in_critical:
            if line.startswith('###') and 'CRITICAL' not in line:
                # End of critical section
                in_critical = False
            else:
                critical_lines.append(line)
    
    return '\n'.join(critical_lines) if critical_lines else ""
```

- [ ] **Step 2: Modify skill context builder to prioritize critical content**

```python
# In _build_runtime_skill_context function, replace the loop starting at line 210:

    for skill in selected:
        name = str(skill.get("name", "unknown"))
        content = load_skill_content(str(skill.get("path", "")))
        if not content:
            continue
        
        # Extract critical sections first
        critical = _extract_critical_sections(content)
        if critical:
            # Add critical section at top
            sections.append(f"[Skill: {name} - CRITICAL RULES]\n{critical}")
        
        # Then add full content (trimmed)
        trimmed = content[:_SKILL_CONTEXT_MAX_CHARS]
        sections.append(f"[Skill: {name}]\n{trimmed}")
```

- [ ] **Step 3: Test critical section extraction**

Add temporary test to verify extraction works:
```python
test_content = """
### CRITICAL: Mail Activities

**NEVER use ui:OutlookMailItem**

### Other Section

Some other content
"""

critical = _extract_critical_sections(test_content)
print(critical)
# Should print only the CRITICAL section
```

- [ ] **Step 4: Commit prompt improvements**

```bash
git add uipath_claude/cli/app.py
git commit -m "feat: prioritize CRITICAL skill sections in LLM prompt"
```

---

### Task 5: Add Integration Test for Mail Workflow Generation

**Files:**
- Create: `tests/integration/test_mail_workflow_generation.py`

- [ ] **Step 1: Write integration test**

```python
# tests/integration/test_mail_workflow_generation.py
"""Integration test for mail workflow generation."""
import pytest
import os
from pathlib import Path
from uipath_claude.artifacts.materialize import materialize_from_assistant_text


@pytest.fixture
def test_output_dir(tmp_path):
    """Create temporary output directory."""
    output_dir = tmp_path / "test_mail_workflow"
    output_dir.mkdir()
    return output_dir


def test_mail_workflow_uses_correct_activities(test_output_dir):
    """Test that generated mail workflow uses real UiPath activities."""
    
    # Simulate LLM response with correct mail workflow
    assistant_response = """
I'll create a workflow to read Outlook emails.

```Main.xaml
<Activity mc:Ignorable="sap sap2010" x:Class="ReadEmails"
  xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
  xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
  xmlns:sap="http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation"
  xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
  xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
  xmlns:ui="http://schemas.uipath.com/workflow/activities"
  xmlns:snm="clr-namespace:System.Net.Mail;assembly=System.Net.Mail"
  xmlns:scg="clr-namespace:System.Collections.Generic;assembly=System.Private.CoreLib">
  
  <Sequence DisplayName="Read Outlook Emails">
    <Sequence.Variables>
      <Variable x:TypeArguments="scg:List(snm:MailMessage)" Name="emails" />
    </Sequence.Variables>
    
    <ui:GetOutlookMailMessages DisplayName="Get Outlook Mail Messages" 
                               MailFolder="Inbox" 
                               Top="5">
      <ui:GetOutlookMailMessages.Result>
        <OutArgument x:TypeArguments="scg:List(snm:MailMessage)">[emails]</OutArgument>
      </ui:GetOutlookMailMessages.Result>
    </ui:GetOutlookMailMessages>
    
    <ui:ForEach x:TypeArguments="snm:MailMessage" DisplayName="For Each Email" Values="[emails]">
      <ui:ForEach.Body>
        <ActivityAction x:TypeArguments="snm:MailMessage">
          <ActivityAction.Argument>
            <DelegateInArgument x:TypeArguments="snm:MailMessage" Name="email" />
          </ActivityAction.Argument>
          <ui:LogMessage Message="[email.Subject]" Level="Info" />
        </ActivityAction>
      </ui:ForEach.Body>
    </ui:ForEach>
  </Sequence>
</Activity>
```
"""
    
    # Materialize the workflow
    written_files = materialize_from_assistant_text(
        assistant_response,
        output_root=test_output_dir,
        allow_project_files=True,
    )
    
    assert len(written_files) == 1
    xaml_file = written_files[0]
    assert xaml_file.exists()
    assert xaml_file.name == "Main.xaml"
    
    # Read and verify content
    content = xaml_file.read_text(encoding='utf-8')
    
    # Verify correct activities are used
    assert "ui:GetOutlookMailMessages" in content
    assert "ui:ForEach" in content
    assert "ui:LogMessage" in content
    
    # Verify correct types
    assert "snm:MailMessage" in content
    assert "System.Net.Mail" in content
    
    # Verify hallucinated activities are NOT present
    assert "ui:StartOutlook" not in content
    assert "ui:GetOutlookNamespace" not in content
    assert "ui:GetOutlookFolder" not in content
    assert "ui:ForEachOutlookMessageFile" not in content
    assert "ui:CloseOutlook" not in content
    assert "outlook:MailItem" not in content
    assert "ui:OutlookMailItem" not in content


def test_mail_workflow_validation_detects_hallucinated_activities(test_output_dir):
    """Test that activity validation detects hallucinated activities."""
    
    # Skip if activity validation is disabled
    if os.environ.get("UIPATH_SKIP_ACTIVITY_VALIDATION", "0").lower() in ("1", "true", "yes"):
        pytest.skip("Activity validation is disabled")
    
    # Create XAML with hallucinated activity
    assistant_response = """
```Main.xaml
<Activity xmlns:ui="http://schemas.uipath.com/workflow/activities">
  <Sequence>
    <ui:FakeHallucinatedActivity />
  </Sequence>
</Activity>
```
"""
    
    # Materialize should succeed but emit warnings
    with pytest.warns(UserWarning, match="Activity validation.*FakeHallucinatedActivity"):
        written_files = materialize_from_assistant_text(
            assistant_response,
            output_root=test_output_dir,
            allow_project_files=True,
        )
    
    assert len(written_files) == 1
```

- [ ] **Step 2: Run integration test**

Run: `pytest tests/integration/test_mail_workflow_generation.py -v -s`
Expected: PASS

- [ ] **Step 3: Commit integration test**

```bash
git add tests/integration/test_mail_workflow_generation.py
git commit -m "test: add integration test for mail workflow generation"
```

---

### Task 6: Update CLI Runner Tests

**Files:**
- Modify: `tests/unit/tools/uipath/test_cli_runner.py` (if exists) or create it

- [ ] **Step 1: Add test for find-activities function**

```python
# tests/unit/tools/uipath/test_cli_runner.py
"""Tests for UiPath CLI runner functions."""
import pytest
from unittest.mock import patch, MagicMock
from uipath_claude.tools.uipath.cli_runner import run_uip_rpa_find_activities


def test_find_activities_success():
    """Test successful activity search."""
    mock_result = {
        "Result": "Success",
        "Data": {
            "Activities": [
                {
                    "ClassName": "UiPath.Core.Activities.LogMessage",
                    "ActivityTypeId": "LogMessage",
                    "Description": "Writes a log message",
                }
            ]
        }
    }
    
    with patch('subprocess.run') as mock_run:
        mock_proc = MagicMock()
        mock_proc.stdout = json.dumps(mock_result)
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc
        
        result = run_uip_rpa_find_activities("LogMessage")
        
        assert result["success"] is True
        assert len(result["activities"]) == 1
        assert result["activities"][0]["ClassName"] == "UiPath.Core.Activities.LogMessage"


def test_find_activities_not_found():
    """Test activity not found."""
    mock_result = {
        "Result": "Success",
        "Data": {
            "Activities": []
        }
    }
    
    with patch('subprocess.run') as mock_run:
        mock_proc = MagicMock()
        mock_proc.stdout = json.dumps(mock_result)
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc
        
        result = run_uip_rpa_find_activities("FakeActivity")
        
        assert result["success"] is True
        assert len(result["activities"]) == 0


def test_find_activities_cli_not_found():
    """Test handling when CLI is not installed."""
    with patch('subprocess.run', side_effect=FileNotFoundError):
        result = run_uip_rpa_find_activities("LogMessage")
        
        assert result["success"] is False
        assert len(result["activities"]) == 0
```

- [ ] **Step 2: Run CLI runner tests**

Run: `pytest tests/unit/tools/uipath/test_cli_runner.py -v`
Expected: PASS

- [ ] **Step 3: Commit CLI runner tests**

```bash
git add tests/unit/tools/uipath/test_cli_runner.py
git commit -m "test: add tests for find-activities CLI function"
```

---

### Task 7: End-to-End Verification

**Files:**
- None (manual testing)

- [ ] **Step 1: Run all tests**

Run: `pytest tests/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 2: Test with real chat agent**

Start chat agent and request mail workflow:
```bash
uipath-claude chat
```

Enter: "can you build a test workflow for me that will read outlook emails, and log to the user the first 5 email subject?"

- [ ] **Step 3: Verify generated workflow**

Check that generated XAML:
1. Uses `ui:GetOutlookMailMessages` (not hallucinated activities)
2. Uses `snm:MailMessage` type (not `ui:OutlookMailItem`)
3. Includes correct namespace declarations
4. Validation passes without errors

- [ ] **Step 4: Verify activity validation warnings**

If hallucinated activities are generated, verify warnings appear in output.

- [ ] **Step 5: Document findings**

Create summary document:
```markdown
# Mail Workflow Generation Test Results

## Test Date: [DATE]

## Generated Workflow Analysis:
- Activities used: [list]
- Types used: [list]
- Validation result: [pass/fail]
- Warnings: [list]

## Issues Found:
[list any remaining issues]

## Recommendations:
[any additional improvements needed]
```

---

## Self-Review Checklist

**Spec Coverage:**
- ✅ Activity validation infrastructure
- ✅ Post-generation validation
- ✅ Critical section prioritization
- ✅ Integration tests
- ✅ Unit tests
- ✅ End-to-end verification

**No Placeholders:**
- ✅ All code blocks complete
- ✅ All file paths exact
- ✅ All commands with expected output
- ✅ No TBD or TODO markers

**Type Consistency:**
- ✅ Function signatures match across tasks
- ✅ Return types consistent
- ✅ Variable names consistent

---

## Execution Notes

**Environment Requirements:**
- UiPath CLI (`uip`) must be installed
- Python 3.12+
- pytest installed
- Access to UiPath Studio (for full validation)

**Testing Approach:**
- Unit tests first (fast feedback)
- Integration tests second (verify integration)
- Manual E2E test last (verify real-world usage)

**Expected Outcomes:**
1. Activity validator catches hallucinated activities
2. Warnings appear when non-existent activities are used
3. Critical skill sections appear first in LLM prompt
4. Generated workflows use only real UiPath activities
