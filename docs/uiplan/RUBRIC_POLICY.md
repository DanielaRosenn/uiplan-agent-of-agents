# UiPlan evaluation rubric policy

**Decision:** Use **deterministic markdown checks first** (`uipath_plan_review`, visual-density
validators, template residue rules, parity tests on generator defaults). These run in CI and
give reproducible pass/fail.

Optional **LLM-based evaluators** (external judge models, rubric scoring plugins) are **out of
scope** for the default gate unless a task explicitly adds them: they add cost, nondeterminism,
and tenant-specific tuning.

If product requires LLM rubrics later, treat them as **supplementary** signals after mechanical
gates pass, and pin prompts + model ids in test fixtures.
