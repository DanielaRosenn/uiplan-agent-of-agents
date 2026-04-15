# Shared Skill Insights

This folder contains **curated, team-shared learnings** about skills.

## What Goes Here

- Insights that have been reviewed and approved via PR
- Learnings that benefit the entire team
- Well-tested gotchas and patterns

## What Does NOT Go Here

- Raw auto-captured insights (those go in `.uipath-claude/skill-insights/`)
- Personal preferences (those go in `~/.cursor/skill-insights/`)
- Unverified learnings

## File Format

Each skill has its own JSON file: `<skill-name>.json`

```json
{
  "skill_name": "uipath-cli-git",
  "insights": [
    {
      "type": "gotcha",
      "content": "Close Studio before running CLI commands",
      "created_at": "2026-04-15T10:30:00Z",
      "source": "curated"
    }
  ],
  "stats": {
    "total_uses": 50,
    "success_rate": 0.92
  }
}
```

## Curation Process

1. Agent proposes insight via `skill_insights(action="propose", ...)`
2. Proposal lands in `proposals/` subdirectory
3. Human reviews, edits if needed
4. Approved insights are moved to this folder via PR
5. Now visible to all team members

## Proposals

The `proposals/` subdirectory contains pending insight proposals awaiting review.
Use `uipath skills proposals list` to see pending items.
