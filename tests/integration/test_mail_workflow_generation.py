"""Integration test for mail workflow generation."""
import pytest
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
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

<<<UIPATH_FILE path="Main.xaml">>>
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
<<<END_UIPATH_FILE>>>
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


@patch("uipath_claude.tools.uipath.cli_runner.subprocess.run")
def test_mail_workflow_validation_detects_hallucinated_activities(mock_run, test_output_dir):
    """Test that activity validation detects hallucinated activities."""
    
    # Skip if activity validation is disabled
    if os.environ.get("UIPATH_SKIP_ACTIVITY_VALIDATION", "0").lower() in ("1", "true", "yes"):
        pytest.skip("Activity validation is disabled")
    
    # Mock CLI to return empty activities list (activity not found)
    mock_result = {
        "Result": "Success",
        "Data": {
            "Activities": []
        }
    }
    mock_proc = MagicMock()
    mock_proc.stdout = json.dumps(mock_result)
    mock_proc.returncode = 0
    mock_run.return_value = mock_proc
    
    # Create XAML with hallucinated activity
    assistant_response = """
<<<UIPATH_FILE path="Main.xaml">>>
<Activity xmlns:ui="http://schemas.uipath.com/workflow/activities">
  <Sequence>
    <ui:FakeHallucinatedActivity />
  </Sequence>
</Activity>
<<<END_UIPATH_FILE>>>
"""
    
    # Materialize should succeed but emit warnings
    with pytest.warns(UserWarning, match="Activity validation.*FakeHallucinatedActivity"):
        written_files = materialize_from_assistant_text(
            assistant_response,
            output_root=test_output_dir,
            allow_project_files=True,
        )
    
    assert len(written_files) == 1
