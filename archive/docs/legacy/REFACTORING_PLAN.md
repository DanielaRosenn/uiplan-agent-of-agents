# Project Structure Refactoring Plan

## Goal
Align the project structure with Claude Code architecture while preserving UiPath-specific functionality.

## Current vs Target Structure

### Current Structure (Mixed Concerns)
```
agent/
├── nodes/                    # UiPath personas (BA, SA, Dev, QA)
├── tools/                    # Tools
├── conversation_engine.py    # NEW - Claude Code inspired
├── context/                  # NEW - Project detection
├── hooks/                    # NEW - Event system
├── memory/                   # NEW - Persistence
├── rendering/                # NEW - Output formatting
├── graph.py                  # LangGraph orchestration
├── state.py                  # State management
└── skill_discovery.py        # Skill loading

cli/
├── commands/                 # NEW - Slash commands
├── branding.py              # NEW - Welcome banner
└── main.py                  # Entry point
```

### Target Structure (Claude Code Aligned)
```
uipath_claude/              # Renamed from 'agent' to avoid conflicts
├── core/                   # Core engine (query/orchestration)
│   ├── conversation.py     # ConversationEngine (query.ts)
│   ├── orchestrator.py     # Tool orchestration
│   └── state.py           # State management
│
├── tools/                  # Tool implementations
│   ├── base.py            # Base tool classes
│   ├── skill_tool.py      # Skill invocation
│   ├── uipath/            # UiPath-specific tools
│   │   ├── analyzer.py    # Workflow Analyzer
│   │   ├── orchestrator.py # Orchestrator API
│   │   └── askai.py       # Ask AI
│   └── system/            # System tools
│       ├── file.py
│       └── shell.py
│
├── skills/                 # Skill management
│   ├── discovery.py       # Skill discovery
│   ├── registry.py        # Multi-source registry
│   └── loader.py          # Skill loading
│
├── commands/              # Slash commands
│   ├── registry.py        # Command registry
│   ├── help.py
│   ├── status.py
│   ├── skills.py
│   └── analyze.py
│
├── context/               # Context detection
│   ├── project.py         # UiPath project detection
│   └── environment.py     # Environment info
│
├── memory/                # Persistence
│   ├── loader.py          # Memory loading
│   └── store.py           # Memory storage
│
├── hooks/                 # Event system
│   ├── manager.py         # Hook manager
│   └── config.py          # Hook configuration
│
├── rendering/             # Output formatting
│   ├── message.py         # Message renderer
│   └── branding.py        # Logo & banner
│
├── personas/              # UiPath-specific personas
│   ├── ba.py             # Business Analyst
│   ├── sa.py             # Solution Architect
│   ├── developer.py      # Developer
│   ├── qa.py             # QA
│   └── hitl.py           # Human-in-the-loop
│
├── workflows/             # UiPath workflow orchestration
│   ├── bootstrap.py      # Bootstrap flow
│   └── graph.py          # LangGraph definitions
│
└── cli/                   # CLI interface
    ├── app.py            # Main CLI app
    └── utils.py          # CLI utilities

tests/
├── unit/
│   ├── core/
│   ├── tools/
│   ├── skills/
│   ├── commands/
│   ├── context/
│   ├── memory/
│   ├── hooks/
│   ├── rendering/
│   ├── personas/
│   └── workflows/
└── integration/
    ├── test_chat_flow.py
    └── test_bootstrap_flow.py
```

## Migration Steps

### Phase 1: Rename Root Package (Fixes Namespace Conflict)
**Goal:** Eliminate conflict with `uipath-agent-cli`

1. Rename `agent/` → `uipath_claude/`
2. Update all imports across the codebase
3. Update `pyproject.toml` package discovery
4. Update CLI entry point
5. Run tests to verify no breakage

**Benefits:**
- Fixes the global `uipath-claude` command issue
- Clearer package naming
- No more namespace conflicts

### Phase 2: Reorganize Core Components
**Goal:** Separate concerns clearly

1. Create `uipath_claude/core/` directory
2. Move `conversation_engine.py` → `core/conversation.py`
3. Move `state.py` → `core/state.py`
4. Create `core/orchestrator.py` for tool orchestration logic
5. Update imports

### Phase 3: Consolidate Tools
**Goal:** Better tool organization

1. Create `uipath_claude/tools/uipath/` for UiPath-specific tools
2. Move existing tools to appropriate subdirectories
3. Create base tool classes in `tools/base.py`
4. Add new UiPath tools (analyzer, orchestrator API, Ask AI)

### Phase 4: Reorganize Skills
**Goal:** Cleaner skill management

1. Create `uipath_claude/skills/` directory
2. Move `skill_discovery.py` → `skills/discovery.py`
3. Create `skills/registry.py` for multi-source management
4. Create `skills/loader.py` for skill loading logic

### Phase 5: Move Commands
**Goal:** Flatten command structure

1. Move `cli/commands/` → `uipath_claude/commands/`
2. Keep CLI layer thin (just entry point)
3. Commands become part of the core package

### Phase 6: Reorganize UiPath-Specific Code
**Goal:** Separate UiPath domain logic

1. Create `uipath_claude/personas/` directory
2. Move `nodes/ba_persona.py` → `personas/ba.py`
3. Move `nodes/sa_persona.py` → `personas/sa.py`
4. Move `nodes/developer_node.py` → `personas/developer.py`
5. Move `nodes/qa_node.py` → `personas/qa.py`
6. Move `nodes/hitl_node.py` → `personas/hitl.py`

7. Create `uipath_claude/workflows/` directory
8. Move `graph.py` → `workflows/graph.py`
9. Create `workflows/bootstrap.py` for bootstrap flow logic

### Phase 7: Flatten CLI
**Goal:** Thin CLI layer

1. Move `cli/branding.py` → `uipath_claude/rendering/branding.py`
2. Keep only `cli/app.py` as entry point
3. CLI just calls into `uipath_claude` package

### Phase 8: Update Tests
**Goal:** Mirror new structure

1. Reorganize `tests/unit/` to match new structure
2. Update all test imports
3. Ensure 100% test pass rate

### Phase 9: Update Documentation
**Goal:** Reflect new structure

1. Update all documentation with new paths
2. Update architecture diagrams
3. Update import examples

## Implementation Strategy

### Option A: Big Bang (Recommended for Clean State)
- Do all phases in one session
- Create new structure alongside old
- Switch over atomically
- Less risk of partial migration bugs

### Option B: Incremental (Safer but Longer)
- One phase per session
- Keep tests passing after each phase
- More commits, easier to review
- Can pause and resume

## Benefits of Refactoring

1. **Namespace Conflict Resolved** - `uipath_claude` vs `agent`
2. **Clear Separation** - Core, tools, skills, commands, personas, workflows
3. **Claude Code Alignment** - Easier to understand for developers familiar with Claude Code
4. **Scalability** - Easy to add new tools, commands, personas
5. **Testability** - Each component isolated and testable
6. **Maintainability** - Clear where to find and modify code

## Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing functionality | Comprehensive test suite (129 tests) |
| Import errors | Automated search/replace + verification |
| Lost work | Git branch for refactoring |
| Time investment | ~2-3 hours for full refactor |

## Post-Refactoring Verification

- [ ] All 129 tests pass
- [ ] CLI works: `uipath-claude chat`
- [ ] Global command works (namespace conflict fixed)
- [ ] All slash commands work
- [ ] Project detection works
- [ ] Memory loading works
- [ ] Hooks system works
- [ ] No import errors
- [ ] Documentation updated

## Recommendation

**Do the refactoring now** before adding more features. The longer you wait, the more painful it becomes. With 129 passing tests, you have good coverage to catch any breakage.

**Suggested approach:** Option A (Big Bang) - one clean refactoring session.
