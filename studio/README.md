# UiPlan Studio

Local-first visual builder for exploring and planning UiPath automation projects.

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 18+ with npm
- Git submodules initialized

### 1. Initialize Submodules (from repo root)

```bash
git submodule update --init
```

### 2. Install Dependencies

```bash
# Backend (from studio/api/)
cd studio/api
uv sync

# Frontend (from studio/web/)
cd ../web
npm install
```

### 3. Run

**Option A: CLI Launcher (recommended)**

From repo root:

```bash
uipath-claude explore
```

This boots both servers and opens the browser automatically.

**Option B: Manual Start**

Terminal 1 (backend):

```bash
cd studio/api
uv run uvicorn app.main:app --reload --port 8000
```

Terminal 2 (frontend):

```bash
cd studio/web
npm run dev
```

Open http://localhost:5173 in your browser.

## Starting the Application

### First-time Setup

1. **Clone and initialize**:
   ```bash
   git clone <repo-url>
   cd uipath-builder-agent
   git submodule update --init
   ```

2. **Install dependencies**:
   ```bash
   cd studio/api && uv sync
   cd ../web && npm install
   ```

3. **Start the application**:
   ```bash
   cd ../..  # back to repo root
   uipath-claude explore
   ```

   The browser opens automatically at `http://localhost:5173/?worktree=<your-project-path>`

### Manual Startup (for development)

Run these in separate terminals:

```bash
# Terminal 1: Backend API
cd studio/api
uv run python -m uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend UI
cd studio/web
npm run dev
```

Then open http://localhost:5173 and use the project picker to select a folder.

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_UIPLAN_API_URL` | `http://localhost:8000` | Backend API URL for frontend |
| `UIPLAN_REPO_ROOT` | Auto-detected | Override repo root for skill/library lookups |

## Loading UiPlan Files

UiPlan Studio automatically discovers and displays planning documents (spec.md, plan.md, tasks.md) from multiple locations.

### Where UiPlan Bundles Are Found

| Location | Description |
|----------|-------------|
| `<project>/spec.md`, `plan.md`, `tasks.md` | Root-level bundle |
| `<project>/.cursor/plans/<slug>/` | Draft bundles (per-user, gitignored) |
| `<project>/docs/plans/<slug>/` | Published bundles (git-tracked) |
| Any folder with `.meta.yaml` + bundle files | Nested bundles |

### Loading a Project

1. **Via CLI** (recommended):
   ```bash
   uipath-claude explore --project-dir /path/to/your/project
   ```

2. **Via URL parameter**:
   ```
   http://localhost:5173/?worktree=/absolute/path/to/project
   ```

3. **Via UI picker**:
   - Open the app without a worktree parameter
   - Use the project source picker in the top-left
   - Enter or browse to your project folder
   - Click "MAP" to index the project

### Viewing UiPlan Bundles in the UI

Once a project is loaded:

1. **Left Rail**: UiPlan bundles appear under the "uiplan" layer with a teal color
2. **Click a bundle**: Opens it in the Inspector panel on the right
3. **Bundle contents**:
   - `spec.md` - Specification (what is being built)
   - `plan.md` - Implementation plan (how to build it)
   - `tasks.md` - Task checklist with progress tracking

### Task Progress Tracking

The `tasks.md` file supports checkbox syntax:

```markdown
- [ ] Pending task
- [x] Completed task
- [-] Cancelled task
- [ ] Task **IN_PROGRESS**
```

Progress is aggregated and shown on the bundle node in the canvas.

### Creating New UiPlan Bundles

UiPlan bundles are typically created through Cursor or the CLI:

```bash
# Via Cursor slash command
/uiplan-full "Feature title"

# Via CLI
uipath-claude plan uiplan full "Feature title"

# Via MCP tools
uipath_plan_uiplan_new(title="Feature title", intent="...")
```

New bundles are created under `.cursor/plans/<YYYY-MM-DD-slug>/`.

## Project Structure

```
studio/
├── api/                 # FastAPI backend
│   ├── app/             # Application code
│   │   ├── main.py      # App composition root
│   │   ├── explorer.py  # Project graph indexer
│   │   ├── routers/     # API endpoints
│   │   └── ...
│   ├── tests/           # Backend tests
│   └── pyproject.toml   # Python dependencies
│
└── web/                 # React + Vite frontend
    ├── src/
    │   ├── App.tsx      # Main app component
    │   ├── components/  # UI components
    │   └── ...
    ├── tests/           # Frontend tests
    └── package.json     # Node dependencies
```

## Features

- **Project Graph Visualization**: Interactive canvas showing files, skills, and UiPlan bundles
- **Layer-based Filtering**: UI / API / Agent / RPA / Maestro / App / Orchestrator / Test / External
- **UiPlan Bundle Tracking**: View spec.md, plan.md, tasks.md with progress indicators
- **Skills Discovery**: Browse skills catalog with metadata and project node matching
- **Knowledge Panel**: Live skills + library citations per node

## View Modes

- **FOCUS Mode** (default): Hierarchical view starting from entry points. Double-click to expand.
- **FULL Mode**: Shows all indexed nodes. Best for small projects.

## Configuration

Projects can include `.uiplan/explorer.yaml` for customization:

```yaml
project:
  name: "My Project"
  type: mixed  # rpa | coded-agent | langgraph | maestro | solution | mixed

indexing:
  scan:
    rpa: ["**/*.xaml"]
    agent: ["agent/**/*.py"]
  exclude:
    - ".venv/**"
    - "node_modules/**"
```

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health check |
| GET | `/explorer/graph?worktree=<path>` | Project graph |
| GET | `/explorer/skills/<id>` | Skill details |
| POST | `/mapping/map-folder` | Copilot-first project mapping |

## Testing

```bash
# Backend tests
cd studio/api
uv run pytest tests/ -q

# Frontend tests
cd studio/web
npm test

# E2E tests
npm run test:e2e
```

## Documentation

- [STUDIO.md](../docs/uiplan/STUDIO.md) - Full user guide
- [EXPLORER.md](../docs/uiplan/EXPLORER.md) - Explorer overview
- [EXPLORER_NEW_PROJECT.md](../docs/uiplan/EXPLORER_NEW_PROJECT.md) - Adopting in new projects
- [INTEGRATIONS.md](../docs/uiplan/INTEGRATIONS.md) - Integration detection
- [VIEW_MODES.md](../docs/uiplan/VIEW_MODES.md) - Focus vs Full mode

## Constraints

- **Local-only**: Both servers bind to `127.0.0.1` with no authentication
- **Read-only explorer**: Generation and editing features are preview-first
- **No deploy**: Publish/deploy remain external, user-approved operations
