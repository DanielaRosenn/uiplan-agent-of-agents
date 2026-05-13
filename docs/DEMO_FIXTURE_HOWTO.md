# How to Create Demo Fixtures from Real Projects

The UiPlan Studio displays a demo project by default. This guide shows you how to create or update demo fixtures from actual codebases.

## Quick Start

1. **Identify a project to export** (must be within the allowed roots):
   ```bash
   # Example paths:
   # - c:\Users\YourName\projects\my-uipath-project
   # - c:\workspace\renewal-automation
   ```

2. **Export via API**:
   ```bash
   curl -X POST http://localhost:8000/fixtures/export-demo \
     -H "Content-Type: application/json" \
     -d '{
       "source_path": "c:/Users/YourName/projects/my-project",
       "output_name": "sample"
     }'
   ```

3. **Import in the frontend**:
   The fixture is automatically saved to `studio/web/src/__fixtures__/{output_name}.ts`

4. **Use in api.ts**:
   ```typescript
   import { sampleGraph } from "../__fixtures__/sample";
   
   const SAMPLE_FIXTURES: Record<string, ProjectGraph> = {
     demo: sampleGraph,
   };
   ```

## Creating Multiple Demo Fixtures

You can create multiple demo fixtures for different project types:

```bash
# Export an RPA project
curl -X POST http://localhost:8000/fixtures/export-demo \
  -d '{"source_path": "./projects/rpa-invoice", "output_name": "rpaDemo"}'

# Export a coded agent project
curl -X POST http://localhost:8000/fixtures/export-demo \
  -d '{"source_path": "./projects/email-analyzer-agent", "output_name": "agentDemo"}'

# Export a Maestro flow
curl -X POST http://localhost:8000/fixtures/export-demo \
  -d '{"source_path": "./projects/approval-flow", "output_name": "flowDemo"}'
```

Then update `studio/web/src/projectGraph/api.ts`:

```typescript
import { sampleGraph } from "../__fixtures__/sample";
import { rpaDemoGraph } from "../__fixtures__/rpaDemo";
import { agentDemoGraph } from "../__fixtures__/agentDemo";
import { flowDemoGraph } from "../__fixtures__/flowDemo";

const SAMPLE_FIXTURES: Record<string, ProjectGraph> = {
  demo: sampleGraph,        // Default
  "demo-rpa": rpaDemoGraph,
  "demo-agent": agentDemoGraph,
  "demo-flow": flowDemoGraph,
};
```

## List Existing Fixtures

```bash
curl http://localhost:8000/fixtures/list
```

## Updating the Current Demo

The current demo fixture is `studio/web/src/__fixtures__/sample.ts`. To update it:

```bash
# Export from your best example project
curl -X POST http://localhost:8000/fixtures/export-demo \
  -d '{"source_path": "/path/to/showcase/project", "output_name": "sample"}'

# Restart the dev server to see changes
cd studio/web
npm run dev
```

## What Gets Exported

The fixture includes:
- **Project metadata** (type, branch, revision)
- **Overview** (name, summary, owner, stakeholders, triggers, actors, KPIs)
- **Nodes** (all indexed files, components, skills, with their metadata)
- **Edges** (relationships, dependencies, calls, invocations)
- **Errors** (linter/validation issues if any)

## Allowed Source Paths

For security, only projects within configured roots can be exported:
- Set `UIPATH_EXPLORER_ROOTS` environment variable
- Or use paths relative to the repo root
- The API will return 403 if the path is not allowed

## Example: Showcase Project Setup

To create a polished demo:

1. **Build a small showcase project**:
   ```
   showcase-project/
   ├── Main.xaml              # RPA workflow
   ├── agent.py               # Coded agent
   ├── approval.flow          # Maestro flow
   ├── docs/
   │   └── PDD.md            # Process design doc
   └── .uiplan/
       └── explorer.yaml      # Project metadata
   ```

2. **Add rich metadata** in `explorer.yaml`:
   ```yaml
   project:
     name: "Sales Renewal Automation"
     type: solution
     overview:
       summary: "End-to-end renewal commitment processing..."
       owner: "Sales Operations"
       kpis:
         - label: "volume"
           value: "120 / day"
         - label: "auto-approval rate"
           value: "62%"
   ```

3. **Export as demo**:
   ```bash
   curl -X POST http://localhost:8000/fixtures/export-demo \
     -d '{"source_path": "./showcase-project", "output_name": "sample"}'
   ```

## Troubleshooting: Large Main Flow Files

RPA projects often have large Main.xaml or Main-Queue.xaml files (500KB+). By default, the indexer skips files larger than 256 KB to avoid performance issues.

**Solution**: Create a `.uiplan/explorer.yaml` config with increased file size limits:

```yaml
---
project:
  name: Your Project Name
  type: rpa

indexing:
  # Increase file size limit to include large Main flows
  max_file_bytes: 1048576  # 1 MB (default is 256 KB)
  max_files_per_layer: 200
```

After adding this config, re-export the fixture. Main entry points will now be included and marked with a green "MAIN" badge in the canvas.

## Tips

- **Keep demos small**: 20-30 nodes is ideal for quick loading
- **Use meaningful names**: Choose projects that showcase different patterns
- **Include documentation**: Nodes with citations and descriptions are more helpful
- **Update regularly**: Re-export when you improve the showcase projects
- **Check file sizes**: Use `explorer.yaml` to increase limits if important files are missing
