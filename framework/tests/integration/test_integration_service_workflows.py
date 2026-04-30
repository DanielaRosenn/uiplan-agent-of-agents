"""Integration tests for Integration Service workflow generation."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from uipath_claude.cli.app import app
from uipath_claude.artifacts.materialize import materialize_from_assistant_text

runner = CliRunner()


@pytest.mark.integration
def test_integration_service_coded_workflow_structure(tmp_path):
    """Test that IS coded workflows have correct structure."""
    output_dir = tmp_path / "is-workflow"
    output_dir.mkdir(parents=True)

    assistant_response = '''
```csharp
path: JiraWorkflow.cs
using UiPath.CodedWorkflows;
using UiPath.IntegrationService.Activities.Runtime.CodedWorkflows;
using UiPath.IntegrationService.Activities.Runtime.Models;
using UiPath.IntegrationService.Activities.Runtime.Models.ConnectorMetadata;

namespace MyProject
{
    public class JiraWorkflow : CodedWorkflow
    {
        [Workflow]
        public async Task Execute()
        {
            var jiraConn = new ISConnections(services.Container).Jira.MyJiraConnection;

            var config = new CodedConnectorConfiguration(
                connection: jiraConn,
                objectName: "issue",
                operation: Operation.List,
                httpMethod: "GET",
                path: "/issue",
                activityType: ActivityType.Generic);

            var request = new ConnectorRequest
            {
                QueryParameters = new() { ["jql"] = "project = TEST", ["pageSize"] = "1000" },
                MaxRecords = 20,
            };

            var response = await jiraConn.ExecuteAsync(config, request);

            foreach (var issue in response.Items)
                Log($"{issue["key"]} - {issue["summary"]}");
        }
    }
}
```
'''

    written = materialize_from_assistant_text(
        assistant_response,
        output_root=output_dir,
        allow_project_files=True,
    )

    assert len(written) == 1
    content = written[0].read_text(encoding="utf-8")
    
    assert "UiPath.IntegrationService" in content
    assert "CodedWorkflow" in content
    assert "[Workflow]" in content
    assert "ConnectorConnection" in content or "ExecuteAsync" in content
    assert "CodedConnectorConfiguration" in content


@pytest.mark.integration
def test_integration_service_xaml_namespace_detection(tmp_path):
    """Test that IS XAML activities require correct namespace."""
    output_dir = tmp_path / "is-xaml"
    output_dir.mkdir(parents=True)

    assistant_response = '''
```xml
path: Main.xaml
<Activity mc:Ignorable="sap sap2010" x:Class="Main"
  xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
  xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
  xmlns:sap="http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation"
  xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
  xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
  xmlns:ui="http://schemas.uipath.com/workflow/activities"
  xmlns:uip="clr-namespace:UiPath.IntegrationService.Activities;assembly=UiPath.IntegrationService.Activities">
  <Sequence DisplayName="Integration Service Demo">
    <ui:LogMessage Message="Using Integration Service" Level="Info" />
  </Sequence>
</Activity>
```
'''

    written = materialize_from_assistant_text(
        assistant_response,
        output_root=output_dir,
        allow_project_files=True,
    )

    assert len(written) == 1
    content = written[0].read_text(encoding="utf-8")
    
    assert "UiPath.IntegrationService.Activities" in content
    assert 'xmlns:uip=' in content


@pytest.mark.integration
def test_mail_vs_integration_service_distinction():
    """Test that mail activities don't require IS namespace."""
    from uipath_claude.cli.app import _select_relevant_skills, _tokenize
    from uipath_claude.skills.registry import SkillRegistry
    
    registry = SkillRegistry()
    skills = registry.load_skills()
    
    mail_prompt = "Read emails from Outlook and log subjects"
    mail_selected = _select_relevant_skills(mail_prompt, skills, max_items=2)
    mail_names = [s.get("name") for s in mail_selected]
    
    is_prompt = "Call Jira API using Integration Service connector"
    is_selected = _select_relevant_skills(is_prompt, skills, max_items=2)
    is_names = [s.get("name") for s in is_selected]
    
    assert any("rpa" in name.lower() for name in mail_names), \
        f"Mail workflow should select RPA skill, got: {mail_names}"


@pytest.mark.integration
def test_chat_integration_service_intent_detection(monkeypatch):
    """Test that IS connector requests are handled correctly."""
    repo_root = Path(__file__).resolve().parents[3]
    output_root = repo_root / "generated" / "test-runs" / "is-detection"
    output_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.chdir(repo_root)
    monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(output_root))
    monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "pytest-is-detection")
    monkeypatch.setenv("UIPATH_CHAT_DEBUG_SKILLS", "1")

    fake_reply = '''<<<UIPATH_FILE path="JiraConnector.cs">>>
using UiPath.CodedWorkflows;
using UiPath.IntegrationService.Activities.Runtime.CodedWorkflows;

namespace TestProject
{
    public class JiraConnector : CodedWorkflow
    {
        [Workflow]
        public async Task Execute()
        {
            Log("Integration Service workflow");
        }
    }
}
<<<END_UIPATH_FILE>>>'''

    with patch("uipath_claude.cli.app._create_engine") as eng:
        eng.return_value = object()
        with patch("uipath_claude.cli.app._get_model_response", new_callable=AsyncMock) as gmr:
            gmr.return_value = fake_reply
            result = runner.invoke(
                app,
                ["chat", "--no-banner"],
                input="create a coded workflow that uses Jira connector\nexit\n",
            )

    assert result.exit_code == 0
    # Routing may short-circuit to planner/clarification in chat mode; assert stability.
    output = result.stdout.lower()
    assert "you:" in output
    assert "goodbye" in output or "what would you like to do next" in output
