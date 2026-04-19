# `ErrorType` lives in `UiPath.Core.Activities` and uses `Business` / `Application`

## Symptom

Compile errors like:

```
The name 'ErrorType' does not exist in the current context
'ErrorType' does not contain a definition for 'BusinessException'
```

## Reality

- The `ErrorType` enum required by `system.SetTransactionStatus` is in
  the `UiPath.Core.Activities` namespace (assembly: `UiPath.System.Activities`).
- The enum members are `ErrorType.Business` and `ErrorType.Application` —
  **not** `BusinessException` / `ApplicationException`. Some doc snippets
  in `skills/.../25.10/coded/examples.md` still show the latter; trust the
  default activity XAML (which uses `ErrorType="Business"`) over the
  examples document.

## Recipe

```csharp
using UiPath.CodedWorkflows;
using UiPath.Core;
using UiPath.Core.Activities;

system.SetTransactionStatus(
    transaction,
    ProcessingStatus.Failed,
    folderPath: null,
    analytics: null,
    output: null,
    details: validation.Error,
    errorType: ErrorType.Business,
    reason: validation.Error,
    timeoutMS: 30000);
```

## How to confirm enum members locally

```
uip rpa get-default-activity-xaml --activity-class-name UiPath.Core.Activities.SetTransactionStatus --output json
```

The returned XAML attribute (`ErrorType="Business"`) is the source of
truth for the enum literals.
