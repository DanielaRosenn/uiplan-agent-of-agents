# Claude Code Architecture Refactoring - Design Specification

**Date:** April 9, 2026  
**Status:** Design Approved  
**Goal:** Restructure UiPath Builder Agent to match Claude Code architecture while preserving all UiPath-specific functionality

---

## Executive Summary

Refactor the project from hybrid structure (`agent/` + `cli/`) to Claude Code-aligned structure (`uipath_claude/` with `query/`, `tools/`, `skills/`, `commands/`, etc.). This fixes the namespace conflict, improves maintainability, and aligns with industry-standard AI agent architecture.

**Key Decisions:**
- ✅ Full restructure (not incremental)
- ✅ Rename `agent` → `uipath_claude` (fixes namespace conflict)
- ✅ Agents as specialized modes (BA, SA, Dev, QA inherit from base agent)
- ✅ Official UiPath/skills as primary source
- ✅ Keep custom skills for gaps (PDD, SDD, REFramework, LRW, code review, test gen)
- ✅ Add Jira/Confluence integration to all agents
- ✅ Hybrid CLI: separate commands with mode switching capability

---

## Target Structure

```
uipath_claude/                    # Renamed from 'agent' (fixes namespace conflict)
├── query/                        # Conversation engine (Claude Code: src/query/)
│   ├── conversation.py           # ConversationEngine (query.ts)
│   ├── orchestration.py          # Tool orchestration (toolOrchestration.ts)
│   ├── bootstrap.py              # Bootstrap flow orchestration
│   └── state.py                  # State management (ProjectState)
│
├── agents/                       # Specialized agent modes
│   ├── base.py                   # Base agent class with conversation loop
│   ├── conversational.py         # Default conversational agent
│   ├── ba.py                     # Business Analyst mode
│   ├── sa.py                     # Solution Architect mode
│   ├── developer.py              # Developer mode
│   └── qa.py                     # QA mode
│
├── tools/                        # Tool implementations (Claude Code: src/tools/)
│   ├── base.py                   # Base tool classes
│   ├── skill_tool.py             # Skill invocation tool
│   └── uipath/                   # UiPath-specific tools
│       ├── analyzer.py           # Workflow Analyzer
│       ├── orchestrator.py       # Orchestrator API
│       └── askai.py              # Ask AI tool
│
├── skills/                       # Skill management (Claude Code: src/skills/)
│   ├── discovery.py              # Skill discovery (loadSkillsDir.ts)
│   ├── registry.py               # Multi-source registry
│   └── loader.py                 # Skill loading with filtering
│
├── commands/                     # Slash commands (Claude Code: src/commands/)
│   ├── registry.py               # Command registry (commands.ts)
│   ├── help.py                   # /help command
│   ├── status.py                 # /status command
│   ├── skills.py                 # /skills command
│   ├── analyze.py                # /analyze command
│   └── bootstrap.py              # /bootstrap command (mode switch)
│
├── context/                      # Context detection
│   ├── project.py                # UiPath project detection
│   └── environment.py            # Environment info
│
├── memory/                       # Persistence (Claude Code: memory.md)
│   ├── loader.py                 # Memory loading
│   └── store.py                  # Memory storage
│
├── hooks/                        # Event system (Claude Code: src/utils/hooks.ts)
│   ├── manager.py                # Hook manager
│   └── config.py                 # Hook configuration
│
├── rendering/                    # Output formatting (Claude Code: src/components/)
│   ├── message.py                # Message renderer (MessageRenderer.tsx)
│   └── branding.py               # Logo & banner (LogoV2.tsx)
│
└── cli/                          # CLI interface (Claude Code: src/entrypoints/)
    ├── app.py                    # Main CLI app (cli.tsx)
    └── utils.py                  # CLI utilities

tests/                            # Mirror source structure
├── unit/
│   ├── query/
│   ├── agents/
│   ├── tools/
│   ├── skills/
│   ├── commands/
│   ├── context/
│   ├── memory/
│   ├── hooks/
│   ├── rendering/
│   └── cli/
└── integration/
    ├── test_chat_flow.py
    └── test_bootstrap_flow.py
```

---

## Agent Architecture: Modes Not Subagents

### Design Pattern

All agents share the same conversation engine, specialized via:
1. **System prompts** - Role-specific instructions
2. **Tool availability** - Filtered tool sets
3. **Skill loading** - Role-specific skills only

```python
# Base Agent (agents/base.py)
class BaseAgent:
    def __init__(self, role: str, system_prompt: str, skills: list[str]):
        self.engine = ConversationEngine()
        self.role = role
        self.system_prompt = system_prompt
        self.skills = self._load_skills(skills)
    
    async def run(self, user_input: str) -> str:
        # Load role-specific context
        # Run conversation loop
        # Return response

# BA Agent (agents/ba.py)
class BAAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            role="business_analyst",
            system_prompt="You are a Business Analyst...",
            skills=["pdd-creation", "business-flow-canvas", ...]
        )

# Similar for SA, Developer, QA agents
```

### Bootstrap Flow

```python
# query/bootstrap.py
async def run_bootstrap_flow(user_request: str):
    # Step 1: BA Agent
    ba = BAAgent()
    pdd = await ba.run(user_request)
    
    # Step 2: SA Agent (receives PDD as context)
    sa = SAAgent()
    sdd = await sa.run(f"Create SDD based on: {pdd}")
    
    # Step 3: Developer Agent (receives PDD + SDD)
    dev = DeveloperAgent()
    code = await dev.run(f"Implement based on PDD: {pdd}, SDD: {sdd}")
    
    # Step 4: QA Agent (receives all artifacts)
    qa = QAAgent()
    validation = await qa.run(f"Validate: {code}")
    
    return {
        "pdd": pdd,
        "sdd": sdd,
        "code": code,
        "validation": validation
    }
```

---

## Section 5: Skill Loading Strategy

### Multi-Source Precedence

```python
# skills/registry.py
class SkillRegistry:
    def load_skills(self, agent_role: str) -> list[Skill]:
        sources = [
            # 1. Project-local (highest priority)
            ".uipath-claude/skills/",
            
            # 2. User custom
            "~/.cursor/skills/",
            
            # 3. Official UiPath (submodule)
            "skills/skills/",
            
            # 4. Cato templates (submodule)
            "templates/",
        ]
        
        # Load and filter by agent role
        skills = []
        for source in sources:
            skills.extend(self._discover_skills(source, agent_role))
        
        # Deduplicate (first source wins)
        return self._deduplicate(skills)
```

### Agent-Specific Skill Filters

```python
AGENT_SKILLS = {
    "ba": [
        "pdd-creation",
        "business-flow-canvas",
        "uipath-confluence-connector",
        "jira-ticket-creation",
        "uipath-platform",
    ],
    "sa": [
        "solution-canvas",
        "sdd-flow-canvas",
        "uipath-flow",
        "uipath-confluence-connector",
        "jira-ticket-creation",
        "uipath-platform",
    ],
    "developer": [
        "uipath-rpa-workflows",
        "uipath-coded-workflows",
        "uipath-coded-agents",
        "uipath-reframework",
        "uipath-longrunning-workflow",
        "uipath-jira-connector",
        "uipath-platform",
    ],
    "qa": [
        "uipath-code-reviewer",
        "uipath-test-generator",
        "uipath-servo",
        "uipath-report-issue",
        "uipath-jira-connector",
        "uipath-platform",
    ],
    "conversational": [
        # All skills available
        "*"
    ]
}
```

Does this skill loading strategy look good?