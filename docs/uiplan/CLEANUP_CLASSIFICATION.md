# UiPlan cleanup classification (repo hygiene)

This note classifies **historical or auxiliary** artifacts touched by UiPlan work so
maintainers do not delete shared fixtures without a safety net. It is **not** permission
to delete paths listed here without human review.

| Area | Classification | Notes |
| --- | --- | --- |
| `templates/uiplan/` | **Keep** | Kit contract; changes require template + generator + visual-density tests. |
| `framework/tests/uiplan/` | **Keep** | Contract tests for generate-docs, validators, parity. |
| `framework/tests/mcp_tests/test_uiplan_*.py` | **Keep** | MCP integration coverage. |
| `ITSupportFlowDemo*/`, `OutlookSubjectLogger/`, `out/` sample trees | **Quarantine / demo** | Local experiment outputs; do not treat as CI fixtures unless a test imports them explicitly. |
| `docs/reviews/uiplan-evaluation.md` | **Keep** | Evaluation backlog reference; update when changing MCP/commands. |
| Legacy single-file plan tools (`uipath_plan_new`, refine, diff) | **Keep** | Dual-track support per evaluation doc; deprecate only with migration guide. |

When retiring a sample folder, prefer **`git rm` on a feature branch** plus a note in the PR
describing which tests/docs replaced its coverage.
