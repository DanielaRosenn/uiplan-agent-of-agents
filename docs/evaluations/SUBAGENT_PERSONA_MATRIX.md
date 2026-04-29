# Subagent, persona, and document-output matrix

Use this table when adding cases to `test_cases.json` (category `Subagent Routing`) or when interpreting `[SKILL: ...]` markers in CLI transcripts.

Grounding: UiPath Academy career paths ([Automation Career Paths](https://academy.uipath.com/career-paths)) align **interactive personas** with Automation Business Analyst, Automation Solution Architect, Automation Developer, and Test Automation Engineer. **Document outputs** (PDD, SDD, ADD, TDD) are artifacts, not separate personas.

| Cohort | Id | Trigger / keywords | Expected skill markers (typical) | Forbidden / guardrails | Primary output |
| --- | --- | --- | --- | --- | --- |
| Discovery | `uipath-project-discovery-agent` | Missing/stale `.claude/rules/project-context.md`; before first `uipath-rpa` build | Skill discovery flow (read-only) | Must not write project files directly | `project-context` style summary |
| Diagnostics | `triage`, `hypothesis-*`, `scope-checker`, `presenter` | User describes Orchestrator/job/selector failures | `uipath-diagnostics` when routed | Destructive prod changes | `.investigation/*` protocol |
| Persona BA | `ba` | requirements, PDD, stakeholder, business process | `uipath-persona-ba` | Write tools in read-only Q&A | Business requirements / PDD outline |
| Persona SA | `sa` | SDD, architecture, trade-off, pattern | `uipath-persona-sa` | Deploy without approval | SDD / architecture outline |
| Persona Developer | `developer` | implement, XAML, code, CLI, bug | `uipath-persona-developer` | Production deploy | Implementation guidance |
| Persona QA | `qa` | test, validation, regression, verify | `uipath-persona-qa` | Skipping defect hygiene | Test strategy / cases |
| Document ADD | SA + **document_type ADD** | agent design document, ADD | `uipath-persona-sa` (ADD prompt body) | Treating ADD as its own persona enum | ADD markdown sections |
| Document TDD | SA + **document_type TDD** | technical design document, TDD | `uipath-persona-sa` (TDD prompt body) | Same | TDD markdown sections |
| MCP | `uipath_answer`, `uipath_intent_classify` | Tool-first audits | N/A | Destructive agent execute without review | Structured JSON |

**Evaluation harness fields** (optional per case): `skills_required`, `skills_forbidden`, `document_type_required`, `document_type_forbidden`, `routing_expected`, `no_file_creation`, `artifacts_forbidden`, `safety_forbidden_phrases`, `routing_failure_is_blocking`. See [README.md](README.md).
