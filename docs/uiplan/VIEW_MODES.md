# UiPlan Studio View Modes

The UiPlan Studio now supports two visualization modes to handle projects of any size:

## Focus Mode (Default)

**Best for**: Large projects (50+ nodes), understanding main flows

Focus Mode shows a curated view starting from entry points:
- **Entry points ONLY** are shown by default (Main.xaml, Main-Queue.xaml, main.py, etc.)
- **No children** visible initially - completely clean view
- **Double-click nodes** to expand and see their immediate children
- **Double-click again** to collapse back to clean view
- **Skills layer** always visible for context

This creates the most readable, hierarchical view centered on the main flow. Perfect for projects with 100+ nodes.

### How Entry Points are Detected

The indexer automatically marks nodes as entry points based on:
- Filename patterns: `Main.xaml`, `Main-Queue.xaml`, `main.py`, `graph.py`, `agent.py`, `index.ts`
- Node kind: `workflow`, `flow`, `case`, `coded_app`, `action_app`
- Manual annotation: `roles: ["entrypoint"]` in the project graph

Entry points display a green **MAIN** badge on the canvas.

### What Gets Expanded

When you double-click a node to expand it, you'll see its immediate children:
- **Invoked workflows** (for `.xaml` files)
- **External integrations** (Salesforce, Slack, ZenDesk, HTTP APIs, Email, Integration Service, Webhooks)
- **Orchestrator resources** (Queues, Assets, Storage Buckets, Action Center, Robots)
- **Imported modules** (for Python/TypeScript)
- **Related skills** (always visible from the skills layer)

### Integration & Orchestrator Nodes

The indexer automatically extracts:
- **External integrations**: Detected from activity patterns (e.g., `Salesforce.*Activity`, `HTTP Request`, `Send Mail`)
  - Appear as **red nodes** (layer: `external`, kind: `external`)
- **Orchestrator resources**: Detected from platform activities (e.g., `Add Queue Item`, `Get Asset`, `Create Form Task`)
  - Appear as **gray nodes** (layer: `orchestrator`, kind: `orchestrator_resource`)
- **"uses" edges**: Dashed connections from workflow to integration/resource

### Expanding Nodes

In Focus Mode:
1. Look for the **chevron indicator** (►) on nodes that have children
2. Double-click any node with a chevron to expand its immediate children
3. The chevron rotates down (▼) to show the node is expanded
4. Double-click again to collapse
5. The status bar shows `NODES · 1 / 111` (visible / total) - only Main visible by default
6. After expanding Main-Queue: `NODES · 25 / 111` (Main + its 24 children)

**Visual Indicators**:
- **Green MAIN badge**: Entry point node
- **Gray chevron (►)**: Node has children, click to expand
- **Green chevron (▼)**: Node is expanded, click to collapse

## Full Mode

**Best for**: Small projects (< 30 nodes), comprehensive audits

Full Mode displays the entire project graph:
- All indexed nodes visible
- All detected relationships shown
- Same layout as before the update

Use Full Mode when you need to see everything at once or are working with a small codebase.

## Switching Modes

Click the **FOCUS** / **FULL** toggle in the top bar:
- FOCUS: Collapsed view from entry points
- FULL: Show all nodes

## For Large Projects

Focus Mode now defaults to showing **only entry points** (`maxDepth: 0`). This is perfect for projects with 100+ nodes.

Additional tips:

1. **Create custom entry points** by adding to `.uiplan/explorer.yaml`:
   ```yaml
   nodes:
     specific-file.xaml:
       roles: ["entrypoint"]
   ```

2. **Filter by layer**: Use the left rail to hide layers you don't need

3. **Use search**: Type `/` to filter nodes by name/desc

4. **Skills are always visible**: The skills layer provides context even in Focus mode

## Performance

Focus Mode dramatically improves performance for large projects:
- Renders only visible nodes (faster initial load)
- Smoother panning/zooming
- Reduced memory footprint
- Instant expand/collapse interactions
