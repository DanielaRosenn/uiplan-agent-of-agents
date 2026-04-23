"""Integration tests for mail workflow generation invariants."""

from unittest.mock import patch

import pytest

from uipath_claude.artifacts.materialize import materialize_from_assistant_text


@pytest.mark.integration
def test_mail_workflow_uses_correct_activities(tmp_path):
    output_dir = tmp_path / "mail-workflow"
    output_dir.mkdir(parents=True)

    assistant_response = """
```xml
path: Main.xaml
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
    <ui:GetOutlookMailMessages DisplayName="Get Outlook Mail Messages" Top="5">
      <ui:GetOutlookMailMessages.Result>
        <OutArgument x:TypeArguments="scg:List(snm:MailMessage)">[emails]</OutArgument>
      </ui:GetOutlookMailMessages.Result>
    </ui:GetOutlookMailMessages>
    <ui:ForEach x:TypeArguments="snm:MailMessage" Values="[emails]">
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

    written = materialize_from_assistant_text(
        assistant_response,
        output_root=output_dir,
        allow_project_files=True,
    )

    assert len(written) == 1
    content = written[0].read_text(encoding="utf-8")
    assert "ui:GetOutlookMailMessages" in content
    assert "snm:MailMessage" in content
    assert "System.Net.Mail" in content
    assert "ui:StartOutlook" not in content
    assert "ui:GetOutlookNamespace" not in content
    assert "ui:GetOutlookFolder" not in content
    assert "ui:ForEachOutlookMessageFile" not in content
    assert "outlook:MailItem" not in content


@pytest.mark.integration
def test_mail_workflow_validation_detects_hallucinated_activities(tmp_path):
    output_dir = tmp_path / "hallucinated-workflow"
    output_dir.mkdir(parents=True)

    assistant_response = """
```xml
path: Main.xaml
<Activity xmlns:ui="http://schemas.uipath.com/workflow/activities">
  <Sequence>
    <ui:FakeHallucinatedActivity />
  </Sequence>
</Activity>
```
"""

    with patch(
        "uipath_claude.validation.activity_validator.run_uip_rpa_find_activities"
    ) as mock_find_activities:
        mock_find_activities.return_value = {
            "success": True,
            "activities": [],
            "raw_output": "{}",
        }

        with pytest.warns(UserWarning, match="FakeHallucinatedActivity"):
            written = materialize_from_assistant_text(
                assistant_response,
                output_root=output_dir,
                allow_project_files=True,
            )

    assert len(written) == 1
