# Invoking a coded workflow from a XAML entry point

## Why a XAML entry point at all

Setting `project.json -> main` to a `.cs` file is fragile across CLI / Studio
versions: `uip rpa get-errors` returned `IAutopilotValidationService.ValidateFile
threw System.InvalidOperationException: "Failed to open the file ProcessInvoices.cs"`.

Keep `main: "Main.xaml"` and call into the coded workflow from there.

## Use `InvokeWorkflowFile`, not `InvokeCodedWorkflow`

`ui:InvokeCodedWorkflow` was rejected by the CLI / version combo we were
running. `ui:InvokeWorkflowFile` against the `.cs` file works:

```xml
<Sequence DisplayName="InvoiceQueueProcessor">
  <ui:InvokeWorkflowFile DisplayName="Invoke ProcessInvoices"
                         WorkflowFileName="ProcessInvoices.cs">
    <ui:InvokeWorkflowFile.Arguments>
      <InArgument x:TypeArguments="x:String" x:Key="sqlConnectionString">[sqlConnectionString]</InArgument>
      <InArgument x:TypeArguments="x:String" x:Key="orchestratorFolder">[orchestratorFolder]</InArgument>
    </ui:InvokeWorkflowFile.Arguments>
  </ui:InvokeWorkflowFile>
</Sequence>
```

Match the argument names exactly to the C# `[Workflow] public void Execute(...)`
parameter names.
