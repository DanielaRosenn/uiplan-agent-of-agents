"""Deterministic scaffold for the InvoiceIntake_Demo classic RPA project.

This runs the exact build steps the chat agent should produce when given
`docs/sdd.md`. Kept as a script so we can verify outputs before a demo and
recover quickly if a chat session fails.

Usage (PowerShell):
    python scripts\\scaffold_invoice_demo.py

Set UIPATH_INVOICE_DEMO_DIR to override the target project directory.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from textwrap import dedent

DEFAULT_PROJECT = (
    r"C:\Users\DanielaRosenstein\OneDrive - Cato Networks\Documents\UiPath"
    r"\InvoiceIntake_Demo"
)


def _project_dir() -> Path:
    raw = os.environ.get("UIPATH_INVOICE_DEMO_DIR", DEFAULT_PROJECT)
    p = Path(raw)
    if not p.exists():
        raise SystemExit(f"project dir does not exist: {p}")
    if not (p / "project.json").exists():
        raise SystemExit(f"no project.json in: {p}")
    return p


def write_project_json(root: Path) -> None:
    pj_path = root / "project.json"
    data = json.loads(pj_path.read_text(encoding="utf-8"))
    data["main"] = "Main.xaml"
    data["expressionLanguage"] = "CSharp"
    data["targetFramework"] = "Windows"
    data["schemaVersion"] = data.get("schemaVersion", "4.0")
    data["dependencies"] = {
        "UiPath.System.Activities": "[26.2.4]",
    }
    data.setdefault("webServices", [])
    data.setdefault("entitiesStores", [])
    data["entryPoints"] = [
        {
            "filePath": "Main.xaml",
            "uniqueId": data.get("entryPoints", [{}])[0].get(
                "uniqueId", "31de0919-bc0b-4429-9205-354a0215a52c"
            ),
            "input": [],
            "output": [],
        }
    ]
    pj_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


MAIN_XAML = dedent(
    """\
    <Activity mc:Ignorable="sap sap2010 sads" x:Class="Main"
        xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
        xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
        xmlns:sap="http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation"
        xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
        xmlns:sads="http://schemas.microsoft.com/netfx/2010/xaml/activities/debugger"
        xmlns:scg="clr-namespace:System.Collections.Generic;assembly=System.Private.CoreLib"
        xmlns:sco="clr-namespace:System.Collections.ObjectModel;assembly=System.Private.CoreLib"
        xmlns:ui="http://schemas.uipath.com/workflow/activities"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
      <TextExpression.NamespacesForImplementation>
        <sco:Collection x:TypeArguments="x:String">
          <x:String>System</x:String>
          <x:String>System.Activities</x:String>
          <x:String>System.Activities.Statements</x:String>
          <x:String>System.Collections.Generic</x:String>
          <x:String>System.IO</x:String>
          <x:String>System.Linq</x:String>
          <x:String>UiPath.Core</x:String>
          <x:String>UiPath.Core.Activities</x:String>
        </sco:Collection>
      </TextExpression.NamespacesForImplementation>
      <TextExpression.ReferencesForImplementation>
        <sco:Collection x:TypeArguments="AssemblyReference">
          <AssemblyReference>System.Activities</AssemblyReference>
          <AssemblyReference>System.Private.CoreLib</AssemblyReference>
          <AssemblyReference>UiPath.System.Activities</AssemblyReference>
        </sco:Collection>
      </TextExpression.ReferencesForImplementation>
      <Sequence DisplayName="Main" sap2010:WorkflowViewState.IdRef="Sequence_Main">
        <Sequence.Variables>
          <Variable x:TypeArguments="x:String" Name="inputFolder" />
          <Variable x:TypeArguments="x:String" Name="outputFolder" />
          <Variable x:TypeArguments="x:String[]" Name="invoiceFiles" />
          <Variable x:TypeArguments="scg:Dictionary(x:String, x:String)" Name="extracted" />
          <Variable x:TypeArguments="x:String" Name="status" />
        </Sequence.Variables>
        <ui:LogMessage DisplayName="Log start" Level="Info" Message="InvoiceIntake_Demo starting" />
        <Assign DisplayName="Set inputFolder">
          <Assign.To>
            <OutArgument x:TypeArguments="x:String">[inputFolder]</OutArgument>
          </Assign.To>
          <Assign.Value>
            <InArgument x:TypeArguments="x:String">[System.IO.Path.Combine(System.Environment.CurrentDirectory, "Data", "Input")]</InArgument>
          </Assign.Value>
        </Assign>
        <Assign DisplayName="Set outputFolder">
          <Assign.To>
            <OutArgument x:TypeArguments="x:String">[outputFolder]</OutArgument>
          </Assign.To>
          <Assign.Value>
            <InArgument x:TypeArguments="x:String">[System.IO.Path.Combine(System.Environment.CurrentDirectory, "Data", "Output")]</InArgument>
          </Assign.Value>
        </Assign>
        <InvokeMethod DisplayName="Ensure output folder" MethodName="CreateDirectory" TargetType="System.IO.Directory">
          <InvokeMethod.Parameters>
            <InArgument x:TypeArguments="x:String">[outputFolder]</InArgument>
          </InvokeMethod.Parameters>
        </InvokeMethod>
        <Assign DisplayName="List invoice files">
          <Assign.To>
            <OutArgument x:TypeArguments="x:String[]">[invoiceFiles]</OutArgument>
          </Assign.To>
          <Assign.Value>
            <InArgument x:TypeArguments="x:String[]">[System.IO.Directory.GetFiles(inputFolder, "*.pdf")]</InArgument>
          </Assign.Value>
        </Assign>
        <ui:ForEach x:TypeArguments="x:String" CurrentIndex="{x:Null}" DisplayName="For each invoice" Values="[invoiceFiles]">
          <ActivityAction x:TypeArguments="x:String">
            <ActivityAction.Argument>
              <DelegateInArgument x:TypeArguments="x:String" Name="currentFile" />
            </ActivityAction.Argument>
            <TryCatch DisplayName="Try process invoice">
              <TryCatch.Try>
                <Sequence>
                  <InvokeWorkflowFile DisplayName="Invoke ExtractInvoice" WorkflowFileName="Workflows\\ExtractInvoice.xaml">
                    <InvokeWorkflowFile.Arguments>
                      <InArgument x:TypeArguments="x:String" x:Key="in_FilePath">[currentFile]</InArgument>
                      <OutArgument x:TypeArguments="scg:Dictionary(x:String, x:String)" x:Key="out_Fields">[extracted]</OutArgument>
                    </InvokeWorkflowFile.Arguments>
                  </InvokeWorkflowFile>
                  <InvokeWorkflowFile DisplayName="Invoke ApplyPolicy" WorkflowFileName="Workflows\\ApplyPolicy.xaml">
                    <InvokeWorkflowFile.Arguments>
                      <InArgument x:TypeArguments="scg:Dictionary(x:String, x:String)" x:Key="in_Fields">[extracted]</InArgument>
                      <OutArgument x:TypeArguments="x:String" x:Key="out_Status">[status]</OutArgument>
                    </InvokeWorkflowFile.Arguments>
                  </InvokeWorkflowFile>
                  <InvokeWorkflowFile DisplayName="Invoke WriteResult" WorkflowFileName="Workflows\\WriteResult.xaml">
                    <InvokeWorkflowFile.Arguments>
                      <InArgument x:TypeArguments="x:String" x:Key="in_FilePath">[currentFile]</InArgument>
                      <InArgument x:TypeArguments="scg:Dictionary(x:String, x:String)" x:Key="in_Fields">[extracted]</InArgument>
                      <InArgument x:TypeArguments="x:String" x:Key="in_Status">[status]</InArgument>
                      <InArgument x:TypeArguments="x:String" x:Key="in_OutputFolder">[outputFolder]</InArgument>
                    </InvokeWorkflowFile.Arguments>
                  </InvokeWorkflowFile>
                </Sequence>
              </TryCatch.Try>
              <TryCatch.Catches>
                <Catch x:TypeArguments="s:Exception" xmlns:s="clr-namespace:System;assembly=System.Private.CoreLib">
                  <ActivityAction x:TypeArguments="s:Exception">
                    <ActivityAction.Argument>
                      <DelegateInArgument x:TypeArguments="s:Exception" Name="ex" />
                    </ActivityAction.Argument>
                    <ui:LogMessage DisplayName="Log per-file error" Level="Error"
                                   Message="[&quot;Failed to process &quot; + currentFile + &quot;: &quot; + ex.Message]" />
                  </ActivityAction>
                </Catch>
              </TryCatch.Catches>
            </TryCatch>
          </ActivityAction>
        </ui:ForEach>
        <ui:LogMessage DisplayName="Log done" Level="Info"
                       Message="[&quot;Processed &quot; + invoiceFiles.Length.ToString() + &quot; invoices&quot;]" />
      </Sequence>
    </Activity>
    """
)


EXTRACT_XAML = dedent(
    """\
    <Activity mc:Ignorable="sap sap2010" x:Class="ExtractInvoice"
        xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
        xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
        xmlns:sap="http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation"
        xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
        xmlns:scg="clr-namespace:System.Collections.Generic;assembly=System.Private.CoreLib"
        xmlns:sco="clr-namespace:System.Collections.ObjectModel;assembly=System.Private.CoreLib"
        xmlns:ui="http://schemas.uipath.com/workflow/activities"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
      <x:Members>
        <x:Property Name="in_FilePath" Type="InArgument(x:String)" />
        <x:Property Name="out_Fields" Type="OutArgument(scg:Dictionary(x:String, x:String))" />
      </x:Members>
      <TextExpression.NamespacesForImplementation>
        <sco:Collection x:TypeArguments="x:String">
          <x:String>System</x:String>
          <x:String>System.Activities</x:String>
          <x:String>System.Activities.Statements</x:String>
          <x:String>System.Collections.Generic</x:String>
          <x:String>System.IO</x:String>
          <x:String>System.Linq</x:String>
          <x:String>System.Text.RegularExpressions</x:String>
          <x:String>UiPath.Core.Activities</x:String>
        </sco:Collection>
      </TextExpression.NamespacesForImplementation>
      <TextExpression.ReferencesForImplementation>
        <sco:Collection x:TypeArguments="AssemblyReference">
          <AssemblyReference>System.Activities</AssemblyReference>
          <AssemblyReference>System.Private.CoreLib</AssemblyReference>
          <AssemblyReference>UiPath.System.Activities</AssemblyReference>
        </sco:Collection>
      </TextExpression.ReferencesForImplementation>
      <Sequence DisplayName="ExtractInvoice">
        <Sequence.Variables>
          <Variable x:TypeArguments="x:String" Name="rawText" />
        </Sequence.Variables>
        <ui:ReadTextFile DisplayName="Read Text File" FileName="[in_FilePath]" Content="[rawText]" />
        <Assign DisplayName="Init out_Fields">
          <Assign.To>
            <OutArgument x:TypeArguments="scg:Dictionary(x:String, x:String)">[out_Fields]</OutArgument>
          </Assign.To>
          <Assign.Value>
            <InArgument x:TypeArguments="scg:Dictionary(x:String, x:String)">[new Dictionary&lt;string, string&gt;()]</InArgument>
          </Assign.Value>
        </Assign>
        <Assign DisplayName="Set InvoiceNumber">
          <Assign.To>
            <OutArgument x:TypeArguments="x:String">[out_Fields["InvoiceNumber"]]</OutArgument>
          </Assign.To>
          <Assign.Value>
            <InArgument x:TypeArguments="x:String">[System.Text.RegularExpressions.Regex.Match(rawText, "INV[-_]?\\d+").Value]</InArgument>
          </Assign.Value>
        </Assign>
        <Assign DisplayName="Set TotalAmount">
          <Assign.To>
            <OutArgument x:TypeArguments="x:String">[out_Fields["TotalAmount"]]</OutArgument>
          </Assign.To>
          <Assign.Value>
            <InArgument x:TypeArguments="x:String">[System.Text.RegularExpressions.Regex.Match(rawText, "Total[^\\d]{0,10}(\\d+(?:\\.\\d{1,2})?)").Groups[1].Value]</InArgument>
          </Assign.Value>
        </Assign>
        <Assign DisplayName="Set VendorName">
          <Assign.To>
            <OutArgument x:TypeArguments="x:String">[out_Fields["VendorName"]]</OutArgument>
          </Assign.To>
          <Assign.Value>
            <InArgument x:TypeArguments="x:String">[(rawText.Split('\\n').FirstOrDefault(l => !string.IsNullOrWhiteSpace(l)) ?? "").Trim()]</InArgument>
          </Assign.Value>
        </Assign>
        <If Condition="[string.IsNullOrEmpty(out_Fields[&quot;InvoiceNumber&quot;])]" DisplayName="Guard: invoice number present">
          <If.Then>
            <Throw DisplayName="No InvoiceNumber" Exception="[new System.Exception(&quot;Invoice number not found in &quot; + in_FilePath)]" />
          </If.Then>
        </If>
      </Sequence>
    </Activity>
    """
)


APPLY_POLICY_XAML = dedent(
    """\
    <Activity mc:Ignorable="sap sap2010" x:Class="ApplyPolicy"
        xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
        xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
        xmlns:sap="http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation"
        xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
        xmlns:scg="clr-namespace:System.Collections.Generic;assembly=System.Private.CoreLib"
        xmlns:sco="clr-namespace:System.Collections.ObjectModel;assembly=System.Private.CoreLib"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
      <x:Members>
        <x:Property Name="in_Fields" Type="InArgument(scg:Dictionary(x:String, x:String))" />
        <x:Property Name="out_Status" Type="OutArgument(x:String)" />
      </x:Members>
      <TextExpression.NamespacesForImplementation>
        <sco:Collection x:TypeArguments="x:String">
          <x:String>System</x:String>
          <x:String>System.Activities</x:String>
          <x:String>System.Activities.Statements</x:String>
          <x:String>System.Collections.Generic</x:String>
        </sco:Collection>
      </TextExpression.NamespacesForImplementation>
      <TextExpression.ReferencesForImplementation>
        <sco:Collection x:TypeArguments="AssemblyReference">
          <AssemblyReference>System.Activities</AssemblyReference>
          <AssemblyReference>System.Private.CoreLib</AssemblyReference>
        </sco:Collection>
      </TextExpression.ReferencesForImplementation>
      <Sequence DisplayName="ApplyPolicy">
        <Sequence.Variables>
          <Variable x:TypeArguments="x:Double" Name="total" />
        </Sequence.Variables>
        <Assign DisplayName="Parse total">
          <Assign.To>
            <OutArgument x:TypeArguments="x:Double">[total]</OutArgument>
          </Assign.To>
          <Assign.Value>
            <InArgument x:TypeArguments="x:Double">[double.TryParse(in_Fields["TotalAmount"], System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out var t) ? t : -1]</InArgument>
          </Assign.Value>
        </Assign>
        <If Condition="[total &lt; 0]" DisplayName="Policy branch">
          <If.Then>
            <Assign>
              <Assign.To>
                <OutArgument x:TypeArguments="x:String">[out_Status]</OutArgument>
              </Assign.To>
              <Assign.Value>
                <InArgument x:TypeArguments="x:String">"NeedsReview"</InArgument>
              </Assign.Value>
            </Assign>
          </If.Then>
          <If.Else>
            <If Condition="[total &lt;= 5000]">
              <If.Then>
                <Assign>
                  <Assign.To>
                    <OutArgument x:TypeArguments="x:String">[out_Status]</OutArgument>
                  </Assign.To>
                  <Assign.Value>
                    <InArgument x:TypeArguments="x:String">"AutoPost"</InArgument>
                  </Assign.Value>
                </Assign>
              </If.Then>
              <If.Else>
                <Assign>
                  <Assign.To>
                    <OutArgument x:TypeArguments="x:String">[out_Status]</OutArgument>
                  </Assign.To>
                  <Assign.Value>
                    <InArgument x:TypeArguments="x:String">"NeedsReview"</InArgument>
                  </Assign.Value>
                </Assign>
              </If.Else>
            </If>
          </If.Else>
        </If>
      </Sequence>
    </Activity>
    """
)


WRITE_RESULT_XAML = dedent(
    """\
    <Activity mc:Ignorable="sap sap2010" x:Class="WriteResult"
        xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
        xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
        xmlns:sap="http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation"
        xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
        xmlns:scg="clr-namespace:System.Collections.Generic;assembly=System.Private.CoreLib"
        xmlns:sco="clr-namespace:System.Collections.ObjectModel;assembly=System.Private.CoreLib"
        xmlns:ui="http://schemas.uipath.com/workflow/activities"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
      <x:Members>
        <x:Property Name="in_FilePath" Type="InArgument(x:String)" />
        <x:Property Name="in_Fields" Type="InArgument(scg:Dictionary(x:String, x:String))" />
        <x:Property Name="in_Status" Type="InArgument(x:String)" />
        <x:Property Name="in_OutputFolder" Type="InArgument(x:String)" />
      </x:Members>
      <TextExpression.NamespacesForImplementation>
        <sco:Collection x:TypeArguments="x:String">
          <x:String>System</x:String>
          <x:String>System.Activities</x:String>
          <x:String>System.Activities.Statements</x:String>
          <x:String>System.Collections.Generic</x:String>
          <x:String>System.IO</x:String>
          <x:String>System.Text.Json</x:String>
          <x:String>UiPath.Core.Activities</x:String>
        </sco:Collection>
      </TextExpression.NamespacesForImplementation>
      <TextExpression.ReferencesForImplementation>
        <sco:Collection x:TypeArguments="AssemblyReference">
          <AssemblyReference>System.Activities</AssemblyReference>
          <AssemblyReference>System.Private.CoreLib</AssemblyReference>
          <AssemblyReference>System.Text.Json</AssemblyReference>
          <AssemblyReference>UiPath.System.Activities</AssemblyReference>
        </sco:Collection>
      </TextExpression.ReferencesForImplementation>
      <Sequence DisplayName="WriteResult">
        <Sequence.Variables>
          <Variable x:TypeArguments="scg:Dictionary(x:String, x:String)" Name="payload" />
          <Variable x:TypeArguments="x:String" Name="jsonText" />
          <Variable x:TypeArguments="x:String" Name="jsonPath" />
          <Variable x:TypeArguments="x:String" Name="csvPath" />
        </Sequence.Variables>
        <Assign DisplayName="Build payload">
          <Assign.To>
            <OutArgument x:TypeArguments="scg:Dictionary(x:String, x:String)">[payload]</OutArgument>
          </Assign.To>
          <Assign.Value>
            <InArgument x:TypeArguments="scg:Dictionary(x:String, x:String)">[new Dictionary&lt;string, string&gt; { {"InvoiceNumber", in_Fields["InvoiceNumber"]}, {"VendorName", in_Fields["VendorName"]}, {"TotalAmount", in_Fields["TotalAmount"]}, {"Status", in_Status}, {"SourceFile", System.IO.Path.GetFileName(in_FilePath)} }]</InArgument>
          </Assign.Value>
        </Assign>
        <Assign DisplayName="Serialize JSON">
          <Assign.To>
            <OutArgument x:TypeArguments="x:String">[jsonText]</OutArgument>
          </Assign.To>
          <Assign.Value>
            <InArgument x:TypeArguments="x:String">[System.Text.Json.JsonSerializer.Serialize(payload)]</InArgument>
          </Assign.Value>
        </Assign>
        <Assign DisplayName="Compute jsonPath">
          <Assign.To>
            <OutArgument x:TypeArguments="x:String">[jsonPath]</OutArgument>
          </Assign.To>
          <Assign.Value>
            <InArgument x:TypeArguments="x:String">[System.IO.Path.Combine(in_OutputFolder, in_Fields["InvoiceNumber"] + ".json")]</InArgument>
          </Assign.Value>
        </Assign>
        <ui:WriteTextFile DisplayName="Write JSON" FileName="[jsonPath]" Text="[jsonText]" />
        <Assign DisplayName="Compute csvPath">
          <Assign.To>
            <OutArgument x:TypeArguments="x:String">[csvPath]</OutArgument>
          </Assign.To>
          <Assign.Value>
            <InArgument x:TypeArguments="x:String">[System.IO.Path.Combine(in_OutputFolder, "run-summary.csv")]</InArgument>
          </Assign.Value>
        </Assign>
        <If Condition="[!System.IO.File.Exists(csvPath)]" DisplayName="Write header if needed">
          <If.Then>
            <ui:AppendLine DisplayName="Append header" FileName="[csvPath]" Text="InvoiceNumber,VendorName,TotalAmount,Status" />
          </If.Then>
        </If>
        <ui:AppendLine DisplayName="Append row" FileName="[csvPath]"
                       Text="[in_Fields[&quot;InvoiceNumber&quot;] + &quot;,&quot; + in_Fields[&quot;VendorName&quot;] + &quot;,&quot; + in_Fields[&quot;TotalAmount&quot;] + &quot;,&quot; + in_Status]" />
      </Sequence>
    </Activity>
    """
)


SAMPLES = {
    "vendor-a.pdf": "Acme Office Supplies\nInvoice INV-1001\nTotal: 1250.00\n",
    "vendor-b.pdf": "Globex Logistics\nInvoice INV-1002\nTotal: 8400.00\n",
    "vendor-c.pdf": "Initech Consulting\nInvoice INV-1003\nTotal: 250.75\n",
}


def main() -> int:
    root = _project_dir()
    print(f"[scaffold] target: {root}")

    write_project_json(root)
    print("[scaffold] project.json updated (C# expressions, windows, pinned deps)")

    workflows_dir = root / "Workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    (root / "Main.xaml").write_text(MAIN_XAML, encoding="utf-8")
    (workflows_dir / "ExtractInvoice.xaml").write_text(EXTRACT_XAML, encoding="utf-8")
    (workflows_dir / "ApplyPolicy.xaml").write_text(APPLY_POLICY_XAML, encoding="utf-8")
    (workflows_dir / "WriteResult.xaml").write_text(WRITE_RESULT_XAML, encoding="utf-8")
    print("[scaffold] wrote Main.xaml + 3 sub-workflows")

    input_dir = root / "Data" / "Input"
    input_dir.mkdir(parents=True, exist_ok=True)
    for name, body in SAMPLES.items():
        (input_dir / name).write_text(body, encoding="utf-8")
    print(f"[scaffold] wrote {len(SAMPLES)} sample inputs under {input_dir}")

    (root / "Data" / "Output").mkdir(parents=True, exist_ok=True)
    print("[scaffold] DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
