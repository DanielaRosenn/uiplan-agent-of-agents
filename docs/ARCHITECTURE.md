# Architecture

UiPath Claude Code follows the Claude Code architecture pattern, adapted for UiPath automation.

## Directory Structure

```
uipath_claude/
├── query/          # Conversation engine (Claude Code: src/query/)
├── agents/         # Specialized agent modes
├── tools/          # Tool implementations
├── skills/         # Skill discovery and management
├── commands/       # Slash command system
├── context/        # Project and environment detection
├── memory/         # Memory persistence
├── hooks/          # Event hooks
├── rendering/      # Output formatting
└── cli/            # CLI interface
```

## Agent Modes

All agents share the same conversation engine, specialized via:

1. **System Prompts** - Role-specific instructions
2. **Tool Availability** - Filtered tool sets
3. **Skill Loading** - Role-specific skills

### Available Agents

- **Conversational** (default): All skills, general assistance
- **BA**: PDD creation, business process design
- **SA**: SDD creation, solution architecture
- **Developer**: Workflow implementation, coding
- **QA**: Code review, testing, validation

## Skill Loading

Skills are loaded from multiple sources with precedence:

1. Project-local (`.uipath-claude/skills/`)
2. User custom (`~/.cursor/skills/`)
3. Official UiPath (`skills/skills/` submodule)
4. Cato templates (`templates/` submodule)

## Bootstrap Flow

```
User Request
    ↓
BA Agent (PDD)
    ↓
SA Agent (SDD)
    ↓
Developer Agent (Code)
    ↓
QA Agent (Validation)
    ↓
Complete
```

## Comparison with Claude Code

| Claude Code | UiPath Claude Code |
|-------------|-------------------|
| `src/query/` | `uipath_claude/query/` |
| `src/tools/` | `uipath_claude/tools/` |
| `src/skills/` | `uipath_claude/skills/` |
| `src/commands/` | `uipath_claude/commands/` |
| `src/components/` | `uipath_claude/rendering/` |
| `src/utils/hooks.ts` | `uipath_claude/hooks/` |
| `memory.md` | `uipath_claude/memory/` |
| TypeScript/React | Python/LangGraph |
