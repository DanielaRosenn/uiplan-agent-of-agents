---
name: app-view-template-improver
description: Improve template view quality for UiPlan/app-facing docs while preserving generation compatibility.
paths:
  - "templates/**/*.md"
  - "docs/uiplan/**/*.md"
---

# App View Template Improver

## Use when
- The user asks to improve app view, template structure, document UX, or readability of generated planning docs.

## Inputs
- Target template files under `templates/`.
- Optional user goal (e.g., "clearer TO-BE architecture view", "better acceptance criteria section").

## Method
1. Read the target template and identify user-facing friction:
   - weak section ordering
   - duplicated headings
   - unclear AS-IS vs TO-BE
   - missing evidence/validation prompts
2. Propose minimal structural edits that keep placeholders intact.
3. Apply edits in canonical templates only.
4. If required, note follow-up sync step for generated mirrors.

## Output contract
- Changed files list.
- Why each change improves the app/template view.
- Any follow-up validation commands.
