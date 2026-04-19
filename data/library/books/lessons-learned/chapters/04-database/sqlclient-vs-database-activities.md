# `System.Data.SqlClient` vs `UiPath.Database.Activities`

For coded workflows, prefer `System.Data.SqlClient` directly:

```csharp
using var conn = new SqlConnection(connectionString);
conn.Open();
using var cmd = new SqlCommand(sql, conn);
cmd.Parameters.AddWithValue("@Vendor", vendor);
cmd.ExecuteNonQuery();
```

## Why

- `UiPath.Database.Activities` adds a heavy dependency to `project.json`
  and was unresolvable on our environment via
  `uip rpa get-default-activity-xaml --activity-class-name UiPath.Database.Activities.ExecuteNonQuery`
  (`Activity 'UiPath.Database.Activities.ExecuteNonQuery' was not found in
  the loaded assemblies`).
- `SqlClient` keeps the package surface area small and avoids dependency
  pinning conflicts with `UiPath.System.Activities` 26.x.

## Required hygiene

- Always use parameterized queries (`AddWithValue`); never string-format
  user-supplied data into SQL.
- Always wrap connections / commands in `using` so they dispose on
  exception paths.
- Read the connection string from a workflow argument or Orchestrator
  asset; never commit one into `project.json` or a `.cs` file.
