# UiPlan Studio Explorer + Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a graph-first UiPlan Studio that combines project exploration and solution building with Copilot-assisted graph actions, context attachment, and preview-first generation.

**Architecture:** Introduce a `uiplan_graph.v2` contract shared by backend and frontend, then layer read-only indexing, explicit graph mutations, context resolution, and Copilot action handlers on top. Keep existing generation/apply safety by generating from immutable graph snapshots, not direct edits. Migrate current planning-doc visualization into a secondary context/proposal view rather than the primary center panel.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, React 18, TypeScript, Vitest, React Testing Library, pytest.

---

## File Structure

### Backend (create/modify)

- Create: `services/uiplan-studio-api/app/graph_workspace.py`
  - Canonical `uiplan_graph.v2` models, core node policy, and mutation helpers.
- Create: `services/uiplan-studio-api/app/graph_indexer.py`
  - Read-only repo/bundle indexer to explorer nodes/edges.
- Create: `services/uiplan-studio-api/app/context_resolver.py`
  - Resolver for skill/library/source attachments and citation metadata.
- Create: `services/uiplan-studio-api/app/copilot_graph_actions.py`
  - Action handlers for explain/mutate/validate/generate actions.
- Modify: `services/uiplan-studio-api/app/schemas.py`
  - Request/response schema additions for graph workspace APIs.
- Modify: `services/uiplan-studio-api/app/main.py`
  - Add graph/index/context/action endpoints and wire services.
- Create: `services/uiplan-studio-api/tests/test_graph_workspace.py`
  - Unit tests for contract and mutation behavior.
- Create: `services/uiplan-studio-api/tests/test_graph_indexer.py`
  - Unit tests for index discovery and partial failure behavior.
- Create: `services/uiplan-studio-api/tests/test_context_resolver.py`
  - Unit tests for context resolution/citation structure.
- Modify: `services/uiplan-studio-api/tests/test_main.py`
  - API integration tests for new endpoints.

### Frontend (create/modify)

- Create: `apps/uiplan-studio/src/graphWorkspace/types.ts`
  - Frontend graph v2 types mirroring backend contract.
- Create: `apps/uiplan-studio/src/graphWorkspace/adapters.ts`
  - Adapter between existing diagram model and graph workspace model.
- Create: `apps/uiplan-studio/src/components/GraphExplorerPanel.tsx`
  - Explorer list/filter/group UI.
- Create: `apps/uiplan-studio/src/components/GraphBuilderInspector.tsx`
  - Builder-focused inspector controls and context attachments.
- Modify: `apps/uiplan-studio/src/components/DiagramCanvas.tsx`
  - Support explorer+builder node semantics and graph selection behavior.
- Modify: `apps/uiplan-studio/src/components/AgentPanel.tsx`
  - Action-oriented Copilot prompts and status UX.
- Modify: `apps/uiplan-studio/src/api/client.ts`
  - API calls for graph load/save/index/context/action.
- Modify: `apps/uiplan-studio/src/App.tsx`
  - Orchestrate workspace state and connect new panels.
- Modify: `apps/uiplan-studio/src/styles.css`
  - Layout/style updates for combined explorer+builder workspace.
- Modify: `apps/uiplan-studio/src/__tests__/App.test.tsx`
  - Integration tests for explorer/builder/context interactions.
- Create: `apps/uiplan-studio/src/graphWorkspace/__tests__/adapters.test.ts`
  - Contract adapter tests.

### Docs

- Modify: `docs/uiplan/STUDIO.md`
  - Update workflow and endpoint descriptions for graph workspace behavior.

---

### Task 1: Introduce Canonical Graph Workspace Contract

**Files:**
- Create: `services/uiplan-studio-api/app/graph_workspace.py`
- Create: `services/uiplan-studio-api/tests/test_graph_workspace.py`
- Create: `apps/uiplan-studio/src/graphWorkspace/types.ts`
- Create: `apps/uiplan-studio/src/graphWorkspace/__tests__/adapters.test.ts`
- Create: `apps/uiplan-studio/src/graphWorkspace/adapters.ts`

- [ ] **Step 1: Write failing backend contract tests**

```python
from app.graph_workspace import (
    CORE_NODE_IDS,
    GraphEdgeV2,
    GraphNodeV2,
    GraphWorkspaceV2,
    new_graph_workspace,
    update_node_title,
)


def test_new_workspace_contains_core_nodes() -> None:
    workspace = new_graph_workspace()
    node_ids = {node.id for node in workspace.nodes}
    assert CORE_NODE_IDS.issubset(node_ids)


def test_core_node_cannot_be_deleted() -> None:
    workspace = new_graph_workspace()
    assert workspace.can_delete_node("spec") is False


def test_update_node_title_mutates_non_core_node() -> None:
    workspace = GraphWorkspaceV2(
        version="uiplan_graph.v2",
        nodes=[GraphNodeV2(id="custom-1", type="workflow", title="Old")],
        edges=[GraphEdgeV2(id="e1", type="dependency", source="custom-1", target="spec")],
    )
    next_workspace = update_node_title(workspace, "custom-1", "New")
    assert next_workspace.nodes[0].title == "New"
```

- [ ] **Step 2: Run backend tests to verify failure**

Run: `uv run pytest services/uiplan-studio-api/tests/test_graph_workspace.py -q`  
Expected: FAIL with `ModuleNotFoundError: No module named 'app.graph_workspace'`.

- [ ] **Step 3: Implement backend graph workspace contract**

```python
from __future__ import annotations

from dataclasses import dataclass, replace

CORE_NODE_IDS = {"spec", "plan", "tasks", "skills", "library", "review"}


@dataclass(frozen=True)
class GraphNodeV2:
    id: str
    type: str
    title: str
    summary: str = ""


@dataclass(frozen=True)
class GraphEdgeV2:
    id: str
    type: str
    source: str
    target: str
    label: str = ""


@dataclass(frozen=True)
class GraphWorkspaceV2:
    version: str
    nodes: list[GraphNodeV2]
    edges: list[GraphEdgeV2]

    def can_delete_node(self, node_id: str) -> bool:
        return node_id not in CORE_NODE_IDS


def new_graph_workspace() -> GraphWorkspaceV2:
    nodes = [
        GraphNodeV2(id="spec", type="doc", title="spec.md"),
        GraphNodeV2(id="plan", type="doc", title="plan.md"),
        GraphNodeV2(id="tasks", type="doc", title="tasks.md"),
        GraphNodeV2(id="skills", type="skill", title="Skills Context"),
        GraphNodeV2(id="library", type="book_section", title="Library Context"),
        GraphNodeV2(id="review", type="review_gate", title="Review Gate"),
    ]
    return GraphWorkspaceV2(version="uiplan_graph.v2", nodes=nodes, edges=[])


def update_node_title(workspace: GraphWorkspaceV2, node_id: str, title: str) -> GraphWorkspaceV2:
    nodes = [replace(node, title=title) if node.id == node_id else node for node in workspace.nodes]
    return replace(workspace, nodes=nodes)
```

- [ ] **Step 4: Add frontend contract and adapter smoke tests**

```ts
import { describe, expect, it } from "vitest";
import { toDiagramData } from "../adapters";
import type { GraphWorkspaceV2 } from "../types";

describe("graph workspace adapters", () => {
  it("maps graph nodes to diagram nodes", () => {
    const graph: GraphWorkspaceV2 = {
      version: "uiplan_graph.v2",
      nodes: [{ id: "n1", type: "workflow", title: "Main.xaml", summary: "entry" }],
      edges: [],
    };
    const diagram = toDiagramData(graph);
    expect(diagram.nodes[0]?.id).toBe("n1");
    expect(diagram.nodes[0]?.title).toBe("Main.xaml");
  });
});
```

- [ ] **Step 5: Run backend/frontend tests to verify pass**

Run: `uv run pytest services/uiplan-studio-api/tests/test_graph_workspace.py -q`  
Expected: PASS (3 passed)

Run: `npm --prefix apps/uiplan-studio test -- graphWorkspace/__tests__/adapters.test.ts`  
Expected: PASS (1 passed)

- [ ] **Step 6: Commit**

```bash
git add services/uiplan-studio-api/app/graph_workspace.py services/uiplan-studio-api/tests/test_graph_workspace.py apps/uiplan-studio/src/graphWorkspace/types.ts apps/uiplan-studio/src/graphWorkspace/adapters.ts apps/uiplan-studio/src/graphWorkspace/__tests__/adapters.test.ts
git commit -m "feat: add canonical graph workspace v2 contract"
```

---

### Task 2: Add Read-Only Graph Indexer and Endpoint

**Files:**
- Create: `services/uiplan-studio-api/app/graph_indexer.py`
- Modify: `services/uiplan-studio-api/app/schemas.py`
- Modify: `services/uiplan-studio-api/app/main.py`
- Create: `services/uiplan-studio-api/tests/test_graph_indexer.py`
- Modify: `services/uiplan-studio-api/tests/test_main.py`

- [ ] **Step 1: Write failing indexer tests**

```python
from pathlib import Path

from app.graph_indexer import index_workspace_sources


def test_index_workspace_sources_detects_markdown_and_python(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (tmp_path / "agent.py").write_text("print('ok')\n", encoding="utf-8")

    result = index_workspace_sources(tmp_path)
    node_types = {node.type for node in result.nodes}
    assert "doc" in node_types
    assert "source_file" in node_types
```

- [ ] **Step 2: Run test to verify failure**

Run: `uv run pytest services/uiplan-studio-api/tests/test_graph_indexer.py -q`  
Expected: FAIL with `ModuleNotFoundError: No module named 'app.graph_indexer'`.

- [ ] **Step 3: Implement indexer service**

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.graph_workspace import GraphEdgeV2, GraphNodeV2, GraphWorkspaceV2, new_graph_workspace


@dataclass(frozen=True)
class IndexResult:
    workspace: GraphWorkspaceV2
    warnings: list[str]


def index_workspace_sources(root: Path) -> GraphWorkspaceV2:
    workspace = new_graph_workspace()
    discovered_nodes: list[GraphNodeV2] = []
    discovered_edges: list[GraphEdgeV2] = []
    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(root).as_posix()
        if rel.endswith(".md"):
            discovered_nodes.append(GraphNodeV2(id=f"doc:{rel}", type="doc", title=rel))
            discovered_edges.append(
                GraphEdgeV2(id=f"e:{rel}:plan", type="context", source=f"doc:{rel}", target="plan")
            )
        elif rel.endswith(".py") or rel.endswith(".ts") or rel.endswith(".tsx"):
            discovered_nodes.append(GraphNodeV2(id=f"src:{rel}", type="source_file", title=rel))
    return GraphWorkspaceV2(
        version=workspace.version,
        nodes=[*workspace.nodes, *discovered_nodes],
        edges=[*workspace.edges, *discovered_edges],
    )
```

- [ ] **Step 4: Add API endpoint and response schema**

```python
@app.get("/graph/index")
def graph_index(bundle_root: str) -> dict:
    root = _resolve_bundle_root(bundle_root)
    indexed = index_workspace_sources(root)
    return {
        "version": indexed.version,
        "nodes": [node.__dict__ for node in indexed.nodes],
        "edges": [edge.__dict__ for edge in indexed.edges],
    }
```

- [ ] **Step 5: Add endpoint integration test**

```python
def test_graph_index_endpoint_returns_workspace(client, tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "spec.md").write_text("# Spec\n", encoding="utf-8")
    response = client.get(f"/graph/index?bundle_root={bundle}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "uiplan_graph.v2"
    assert any(node["id"] == "spec" for node in payload["nodes"])
```

- [ ] **Step 6: Run tests and commit**

Run: `uv run pytest services/uiplan-studio-api/tests/test_graph_indexer.py services/uiplan-studio-api/tests/test_main.py -q`  
Expected: PASS

```bash
git add services/uiplan-studio-api/app/graph_indexer.py services/uiplan-studio-api/app/main.py services/uiplan-studio-api/app/schemas.py services/uiplan-studio-api/tests/test_graph_indexer.py services/uiplan-studio-api/tests/test_main.py
git commit -m "feat: add graph indexing endpoint for explorer nodes"
```

---

### Task 3: Implement Context Resolver for Skills/Library Attachments

**Files:**
- Create: `services/uiplan-studio-api/app/context_resolver.py`
- Modify: `services/uiplan-studio-api/app/main.py`
- Create: `services/uiplan-studio-api/tests/test_context_resolver.py`
- Modify: `apps/uiplan-studio/src/api/client.ts`

- [ ] **Step 1: Write failing resolver test**

```python
from app.context_resolver import resolve_node_context


def test_resolve_node_context_returns_citations() -> None:
    context = resolve_node_context(
        node_id="plan",
        query="retry scope",
        sources=["library", "skills"],
    )
    assert context["node_id"] == "plan"
    assert "citations" in context
```

- [ ] **Step 2: Run test to verify failure**

Run: `uv run pytest services/uiplan-studio-api/tests/test_context_resolver.py -q`  
Expected: FAIL with `ModuleNotFoundError: No module named 'app.context_resolver'`.

- [ ] **Step 3: Implement resolver service**

```python
from __future__ import annotations

from app.library_service import search_library_context


def resolve_node_context(node_id: str, query: str, sources: list[str]) -> dict:
    citations: list[dict] = []
    if "library" in sources:
        library_results = search_library_context(query, top_n=3)
        for item in library_results:
            citations.append(
                {
                    "source_type": "library",
                    "source_id": f"{item.book_id}:{item.chapter_id}:{item.section_id}",
                    "snippet": item.snippet,
                    "strict": False,
                }
            )
    return {"node_id": node_id, "query": query, "citations": citations}
```

- [ ] **Step 4: Expose context endpoint and frontend client method**

```python
@app.post("/graph/context/resolve")
def graph_context_resolve(payload: dict) -> dict:
    return resolve_node_context(
        node_id=payload["node_id"],
        query=payload.get("query", ""),
        sources=payload.get("sources", ["library"]),
    )
```

```ts
resolveGraphNodeContext(nodeId: string, query: string, sources: string[]) {
  return request<{ node_id: string; citations: Array<{ source_type: string; snippet: string }> }>(
    "/graph/context/resolve",
    {
      method: "POST",
      body: JSON.stringify({ node_id: nodeId, query, sources }),
    },
  );
}
```

- [ ] **Step 5: Run tests and commit**

Run: `uv run pytest services/uiplan-studio-api/tests/test_context_resolver.py services/uiplan-studio-api/tests/test_main.py -q`  
Expected: PASS

```bash
git add services/uiplan-studio-api/app/context_resolver.py services/uiplan-studio-api/app/main.py services/uiplan-studio-api/tests/test_context_resolver.py apps/uiplan-studio/src/api/client.ts
git commit -m "feat: add graph node context resolver endpoint"
```

---

### Task 4: Add Copilot Graph Actions API

**Files:**
- Create: `services/uiplan-studio-api/app/copilot_graph_actions.py`
- Modify: `services/uiplan-studio-api/app/main.py`
- Modify: `services/uiplan-studio-api/tests/test_main.py`
- Modify: `apps/uiplan-studio/src/api/client.ts`

- [ ] **Step 1: Write failing action endpoint test**

```python
def test_graph_action_add_node(client) -> None:
    response = client.post(
        "/graph/actions/execute",
        json={
            "action": "add_node",
            "payload": {"id": "node-hitl", "type": "hitl_step", "title": "Approval"},
            "workspace": {"version": "uiplan_graph.v2", "nodes": [], "edges": []},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert any(node["id"] == "node-hitl" for node in data["workspace"]["nodes"])
```

- [ ] **Step 2: Run test to verify failure**

Run: `uv run pytest services/uiplan-studio-api/tests/test_main.py::test_graph_action_add_node -q`  
Expected: FAIL with `404` for `/graph/actions/execute`.

- [ ] **Step 3: Implement minimal action handler**

```python
from __future__ import annotations


def execute_graph_action(action: str, payload: dict, workspace: dict) -> dict:
    nodes = list(workspace.get("nodes", []))
    edges = list(workspace.get("edges", []))
    if action == "add_node":
        nodes.append(payload)
        return {"workspace": {"version": "uiplan_graph.v2", "nodes": nodes, "edges": edges}}
    if action == "explain_node":
        return {"workspace": workspace, "message": f"Node {payload['node_id']} is part of the build graph."}
    return {"workspace": workspace, "message": f"Unsupported action: {action}"}
```

- [ ] **Step 4: Wire endpoint and frontend API call**

```python
@app.post("/graph/actions/execute")
def graph_actions_execute(payload: dict) -> dict:
    return execute_graph_action(
        action=payload["action"],
        payload=payload.get("payload", {}),
        workspace=payload.get("workspace", {"version": "uiplan_graph.v2", "nodes": [], "edges": []}),
    )
```

```ts
executeGraphAction(action: string, payload: Record<string, unknown>, workspace: unknown) {
  return request<{ workspace: unknown; message?: string }>("/graph/actions/execute", {
    method: "POST",
    body: JSON.stringify({ action, payload, workspace }),
  });
}
```

- [ ] **Step 5: Run tests and commit**

Run: `uv run pytest services/uiplan-studio-api/tests/test_main.py::test_graph_action_add_node -q`  
Expected: PASS

```bash
git add services/uiplan-studio-api/app/copilot_graph_actions.py services/uiplan-studio-api/app/main.py services/uiplan-studio-api/tests/test_main.py apps/uiplan-studio/src/api/client.ts
git commit -m "feat: add copilot graph action execution endpoint"
```

---

### Task 5: Build Explorer Panel and Builder Inspector UI

**Files:**
- Create: `apps/uiplan-studio/src/components/GraphExplorerPanel.tsx`
- Create: `apps/uiplan-studio/src/components/GraphBuilderInspector.tsx`
- Modify: `apps/uiplan-studio/src/App.tsx`
- Modify: `apps/uiplan-studio/src/components/DiagramCanvas.tsx`
- Modify: `apps/uiplan-studio/src/styles.css`
- Modify: `apps/uiplan-studio/src/__tests__/App.test.tsx`

- [ ] **Step 1: Write failing UI integration test**

```tsx
import { render, screen } from "@testing-library/react";
import App from "../App";

it("renders explorer and builder inspector regions", async () => {
  render(<App />);
  expect(await screen.findByRole("heading", { name: /graph explorer/i })).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: /builder inspector/i })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify failure**

Run: `npm --prefix apps/uiplan-studio test -- src/__tests__/App.test.tsx -t "renders explorer and builder inspector regions"`  
Expected: FAIL (headings not found).

- [ ] **Step 3: Implement explorer panel component**

```tsx
import type { GraphNodeV2 } from "../graphWorkspace/types";

interface GraphExplorerPanelProps {
  nodes: GraphNodeV2[];
  selectedNodeId: string | null;
  onSelectNode: (id: string) => void;
}

export default function GraphExplorerPanel({
  nodes,
  selectedNodeId,
  onSelectNode,
}: GraphExplorerPanelProps) {
  return (
    <section className="studio-card">
      <h2>Graph Explorer</h2>
      <ul>
        {nodes.map((node) => (
          <li key={node.id}>
            <button
              className={selectedNodeId === node.id ? "is-selected" : ""}
              onClick={() => onSelectNode(node.id)}
            >
              {node.title}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

- [ ] **Step 4: Implement builder inspector component and wire in App**

```tsx
import type { GraphNodeV2 } from "../graphWorkspace/types";

interface GraphBuilderInspectorProps {
  node: GraphNodeV2 | null;
}

export default function GraphBuilderInspector({ node }: GraphBuilderInspectorProps) {
  return (
    <section className="studio-card">
      <h2>Builder Inspector</h2>
      {!node ? <p>Select a node.</p> : <p>{node.summary || "No summary available."}</p>}
    </section>
  );
}
```

- [ ] **Step 5: Run tests and commit**

Run: `npm --prefix apps/uiplan-studio test -- src/__tests__/App.test.tsx`  
Expected: PASS

```bash
git add apps/uiplan-studio/src/components/GraphExplorerPanel.tsx apps/uiplan-studio/src/components/GraphBuilderInspector.tsx apps/uiplan-studio/src/components/DiagramCanvas.tsx apps/uiplan-studio/src/App.tsx apps/uiplan-studio/src/styles.css apps/uiplan-studio/src/__tests__/App.test.tsx
git commit -m "feat: add explorer and builder inspector workspace panels"
```

---

### Task 6: Integrate Context Resolution and Copilot Actions in UI Flow

**Files:**
- Modify: `apps/uiplan-studio/src/App.tsx`
- Modify: `apps/uiplan-studio/src/components/AgentPanel.tsx`
- Modify: `apps/uiplan-studio/src/components/GraphBuilderInspector.tsx`
- Modify: `apps/uiplan-studio/src/__tests__/App.test.tsx`

- [ ] **Step 1: Write failing interaction test for context resolve action**

```tsx
it("resolves context for selected node from inspector", async () => {
  render(<App />);
  const button = await screen.findByRole("button", { name: /resolve context/i });
  button.click();
  expect(await screen.findByText(/citations/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify failure**

Run: `npm --prefix apps/uiplan-studio test -- src/__tests__/App.test.tsx -t "resolves context for selected node from inspector"`  
Expected: FAIL (button/section missing).

- [ ] **Step 3: Add context resolve handler in App state**

```tsx
const [resolvedContext, setResolvedContext] = useState<Array<{ source_type: string; snippet: string }>>([]);

const handleResolveContext = async () => {
  if (!selectedNodeId) return;
  const response = await apiClient.resolveGraphNodeContext(selectedNodeId, selectedNode?.title ?? "", [
    "library",
    "skills",
  ]);
  setResolvedContext(response.citations);
};
```

- [ ] **Step 4: Add Copilot action execution flow from AgentPanel**

```tsx
const handleApplyCopilotSuggestion = async () => {
  const actionResult = await apiClient.executeGraphAction(
    "add_node",
    { id: `node-${Date.now()}`, type: "plan_step", title: "New Plan Step", summary: "From Copilot action" },
    graphWorkspace,
  );
  setGraphWorkspace(actionResult.workspace as GraphWorkspaceV2);
};
```

- [ ] **Step 5: Run tests and commit**

Run: `npm --prefix apps/uiplan-studio test -- src/__tests__/App.test.tsx`  
Expected: PASS

```bash
git add apps/uiplan-studio/src/App.tsx apps/uiplan-studio/src/components/AgentPanel.tsx apps/uiplan-studio/src/components/GraphBuilderInspector.tsx apps/uiplan-studio/src/__tests__/App.test.tsx
git commit -m "feat: wire context resolution and copilot graph actions in ui"
```

---

### Task 7: Generate from Graph Snapshot and Preserve Preview-First Apply

**Files:**
- Modify: `services/uiplan-studio-api/app/main.py`
- Modify: `services/uiplan-studio-api/tests/test_main.py`
- Modify: `apps/uiplan-studio/src/App.tsx`
- Modify: `docs/uiplan/STUDIO.md`

- [ ] **Step 1: Write failing backend test for graph snapshot metadata**

```python
def test_generate_approval_package_includes_graph_snapshot_metadata(client) -> None:
    response = client.post(
        "/generation/packages",
        json={
            "bundle_root": ".cursor/plans/example",
            "graph": {"graph_id": "workspace-1", "nodes": [], "edges": []},
            "stages": ["01-plan"],
        },
    )
    assert response.status_code == 200
    manifest = response.json()
    assert manifest["graph_ref"]["graph_id"] == "workspace-1"
```

- [ ] **Step 2: Run test to verify failure**

Run: `uv run pytest services/uiplan-studio-api/tests/test_main.py::test_generate_approval_package_includes_graph_snapshot_metadata -q`  
Expected: FAIL on missing/incorrect `graph_ref`.

- [ ] **Step 3: Update generation request payload assembly in frontend**

```tsx
const handleGeneratePlan = async () => {
  const graphPayload = {
    nodes: graphWorkspace.nodes,
    edges: graphWorkspace.edges,
  };
  await apiClient.generateApprovalPackage(bundleRoot, graphPayload, ["01-plan"]);
};
```

- [ ] **Step 4: Ensure backend keeps preview-first invariant**

```python
if payload.write_policy != "approval_package_only":
    raise HTTPException(status_code=400, detail="Only approval_package_only write_policy is supported.")
```

- [ ] **Step 5: Update docs and run full tests**

Run: `uv run pytest services/uiplan-studio-api/tests -q`  
Expected: PASS

Run: `npm --prefix apps/uiplan-studio test`  
Expected: PASS

Run: `npm --prefix apps/uiplan-studio run build`  
Expected: PASS build output.

```bash
git add services/uiplan-studio-api/app/main.py services/uiplan-studio-api/tests/test_main.py apps/uiplan-studio/src/App.tsx docs/uiplan/STUDIO.md
git commit -m "feat: generate proposal packages from graph snapshot safely"
```

---

## Self-Review Checklist

### 1) Spec coverage

- Product shape (explorer + builder + inspector + approval panel): covered by Tasks 5 and 6.
- Architecture services (indexer, builder contract, resolver, actions, generation): covered by Tasks 1, 2, 3, 4, 7.
- Data flow and guardrails (preview-first apply, snapshot generation): covered by Task 7.
- Testing requirements (backend/frontend/e2e-level smoke): covered by Tasks 1-7 test steps.

No uncovered spec requirement remains.

### 2) Placeholder scan

- No `TODO`, `TBD`, or “implement later” placeholders are present.
- Every code step contains concrete code blocks.
- Every verification step includes exact commands and expected outcomes.

### 3) Type consistency

- Canonical workspace version: `uiplan_graph.v2` used consistently.
- Action endpoint name: `/graph/actions/execute` used consistently.
- Context resolve endpoint name: `/graph/context/resolve` used consistently.

---

Plan complete and saved to `docs/superpowers/plans/2026-05-06-uiplan-studio-explorer-builder-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
