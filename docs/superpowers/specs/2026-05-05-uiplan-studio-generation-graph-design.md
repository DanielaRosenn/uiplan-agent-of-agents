# UiPlan Studio Generation Graph Design

**Date:** 2026-05-05
**Status:** Approved brainstorming design, revised for contract-first implementation planning
**Owner:** Daniela + Agent collaboration
**Scope:** Define UiPlan Studio's next direction as a planning-to-code workbench built around a typed generation graph, staged approval packages, grounded context, and preview-first generation.

## 1) Problem and product goal

UiPlan Studio currently helps visualize a UiPlan bundle, inspect context, request generated previews, and review readiness. The next direction is to turn that foundation into a planning-to-code workbench where the diagram is the source model for generation, not only a visual aid.

The product goal is to let a user describe and organize a UiPath solution visually, attach trusted context, choose one or more project types per node, and generate an approval package that can be reviewed stage by stage before any files are applied. The workbench should support mixed UiPath delivery shapes: RPA workflows, coded automations, coded agents, Maestro flows, coded apps, assets, queues, tests, docs, tools, skills, and deployment gates.

The core decision is that generation never writes implementation files directly. It produces reviewable artifacts, diffs, validation findings, citations, and stage readiness. A human then drills into each file proposal and explicitly applies approved previews.

## 2) Core model

### Typed graph

The diagram becomes a typed generation graph stored as structured data. Every node and edge carries enough metadata for generation, validation, and UI review.

Each graph has:

- `graph_id`, `schema_version`, `bundle_root`, and `created_from` metadata.
- `nodes`, each representing something generation can reason about.
- `edges`, each representing a typed relationship between nodes.
- `context_attachments`, shared and node-specific grounding references.
- `approval_state`, tracking progress through generation stages.
- `generation_profile`, capturing selected defaults such as target workspace, package naming assumptions, and allowed project types.

The first implementation should version the schema explicitly as `generation_graph.v1`. Schema upgrades are allowed later, but v1 should be treated as a stable local contract once implementation begins. Phase 0 defines the schema files, approval state machine, storage layout, path allowlist, and command registry before any generation stage is implemented.

### Node types

Nodes are mixed by design. A node must declare both its role in the graph and the type of output it can produce.

Recommended v1 node roles:

- `process_step`: business or automation step in an end-to-end flow.
- `project_component`: buildable UiPath component such as RPA, coded agent, Flow, coded app, library, or API workflow.
- `generated_artifact`: file or package proposal such as `Main.xaml`, `main.py`, `project.json`, `agent.json`, `plan.md`, or `README.md`.
- `test`: unit, integration, eval, smoke, or UiPath Test Manager coverage.
- `tool`: CLI, MCP tool, SDK, or local command needed by a generated stage.
- `asset`: Orchestrator asset, storage bucket, credential reference, or configuration value.
- `queue`: Orchestrator queue, queue item schema, retry policy, or transaction boundary.
- `docs_context`: PDD, SDD, ADD, README, library book section, or product documentation reference.
- `skill`: Cursor or UiPath skill that constrains implementation.
- `deployment_gate`: restore, analyze, test, pack, publish, deploy, activation, or smoke gate.
- `review_gate`: human approval, security review, governance review, or readiness check.

Recommended v1 output types:

- `none`: context-only or decision-only node.
- `document`: markdown, JSON, YAML, or design artifact.
- `project_scaffold`: project directory or manifest proposal.
- `source_file`: implementation file proposal.
- `test_file`: automated test proposal.
- `config`: non-secret configuration proposal.
- `orchestrator_resource`: asset, queue, process, package, bucket, or folder proposal.
- `validation_report`: readiness, lint, analyze, test, or governance output.
- `approval_gate`: structured approval requirement.

Each node may select multiple project types. For example, a "Customer Intake" process step can map to `maestro-flow` and `coded-agent`, while a "Download invoice" component can map to `rpa` and `coded-automation`. Project type selection is a list, not a single enum, because one business node can generate coordinated artifacts across multiple project boundaries.

Recommended v1 project type values:

- `rpa`
- `coded-automation`
- `coded-agent`
- `maestro-flow`
- `coded-app`
- `coded-action-app`
- `api-workflow`
- `solution`
- `library`
- `test`
- `docs`
- `platform-resource`

### Edges

Edges must also be typed. The graph should not infer all semantics from layout.

Recommended v1 edge types:

- `drives`: source node defines requirements for target node.
- `generates`: source node creates or updates target artifact.
- `depends_on`: source node needs target node first.
- `uses_context`: source node is grounded by target context.
- `uses_skill`: source node is constrained by target skill.
- `validates`: source test or gate validates target node.
- `blocks`: source gate must pass before target stage advances.
- `deploys`: source package or component is released through target gate.
- `observes`: source monitoring or smoke node checks target runtime behavior.
- `documents`: source documentation describes target component.

Cycles are allowed only for refinement loops, such as `test validates component` and `component drives test update`. Stage progression edges must remain acyclic so readiness can be computed deterministically.

### Context attachments

Context can attach to the whole graph, to a node, to an edge, or to a generated file proposal. It comes from:

- repository docs such as PDD, SDD, ADD, README, existing plans, and local architecture notes,
- UiPath library books and product docs accessed through library lookup/search services,
- curated skills and skill metadata,
- MCP tool descriptors and runtime tool capability summaries,
- existing source files, tests, and project manifests,
- user-provided notes captured in the approval package.

Each context attachment has:

- `source_kind`: `repo_doc`, `library_book`, `skill`, `tool`, `source_file`, `user_note`, or `validation_output`.
- `source_id`: stable identifier or relative path.
- `citation`: required reference for strict contexts.
- `scope`: `graph`, `node`, `edge`, `file`, or `stage`.
- `policy`: `strict` or `advisory`.
- `summary`: short explanation of why the context is relevant.

The context policy is mixed. Production, deployment, runtime, security, credentials, Orchestrator resources, and validation nodes use strict context. Exploratory planning, early decomposition, brainstorming, and UI sketch nodes can use advisory context. Strict context requires citations in the approval package and blocks apply when required citations are missing. Advisory context may influence suggestions but must be labelled as non-authoritative.

### Approval state

Approval state is stored separately from graph content so users can iterate on the model without losing review history.

The state tracks:

- current stage,
- per-stage status,
- per-node readiness,
- per-file approval status,
- blocking findings,
- applied preview identifiers,
- superseded preview identifiers,
- reviewer notes,
- validation command summaries when available.

Allowed status values are `not_started`, `ready_for_review`, `changes_requested`, `approved`, `blocked`, `applied`, and `superseded`.

## 3) Phase 0 contract

Phase 0 is a required contract phase before Phase 1 implementation. It does not generate user-facing plans, scaffolds, code, tests, or validation packages. Its output is the durable local contract that later stages must use.

Phase 0 must define these contracts before Plan or Scaffold generation ships:

- schema file locations and versioning rules for the typed generation graph and approval packages,
- the approval state machine and durable approval metadata,
- package and proposal storage layout under a UiPlan bundle,
- path allowlist rules for proposed and applied files,
- command registry rules for validation and future tool-backed generation steps.

### Schema files and versioning

The initial contract should use explicit v1 schema ids and stable local file names:

- `generation-graph.v1.schema.json`: graph metadata, nodes, edges, context attachments, generation profile, and approval-state reference.
- `approval-package.v1.schema.json`: package manifest, graph snapshot reference, context manifest reference, stage manifests, findings, proposal references, and safety policy.
- `approval-state.v1.schema.json`: stage status, per-proposal review status, apply status, reviewer notes, supersession, and audit timestamps.
- `file-proposal.v1.schema.json`: target path, file kind, owning node ids, project type ids, content hashes, base hash, diff reference, citations, findings, and apply eligibility.
- `command-registry.v1.schema.json`: command ids, stage scope, allowed execution mode, required confirmation, external mutation classification, output summary policy, and credential requirements.

Every persisted package records the schema ids and versions it was created with. Schema evolution must be additive within v1. Breaking changes require a new schema id and an explicit migration path that leaves old approval packages readable as history.

### Approval state machine

Approval state is durable metadata, not UI-only state. The state machine applies to stages and individual file proposals.

Allowed transitions:

- `not_started` -> `ready_for_review` when a package or proposal is generated.
- `ready_for_review` -> `changes_requested` when the reviewer asks for revision.
- `changes_requested` -> `ready_for_review` when a superseding proposal is generated.
- `ready_for_review` -> `approved` when the reviewer approves the stage or proposal.
- `approved` -> `applied` only after preview/apply succeeds with matching hashes.
- Any non-applied state -> `blocked` when a required contract, citation, path, or validation condition fails.
- Any non-applied proposal -> `superseded` when a newer proposal replaces it.

Approval metadata must record reviewer identity when available, timestamp, source graph hash, context manifest hash, proposal hash, base file hash when applicable, and the reason for any blocked or superseded state.

### Package and proposal storage layout

Approval packages are stored inside the selected UiPlan bundle, separate from target repository files. The first implementation only emits Plan and Scaffold stages; Code, Tests, and Validation folders are reserved for future stages and must not be emitted until their generators use the same contract.

Recommended v1 layout:

```text
.uiplan/
  generation/
    schemas/
      generation-graph.v1.schema.json
      approval-package.v1.schema.json
      approval-state.v1.schema.json
      file-proposal.v1.schema.json
      command-registry.v1.schema.json
    packages/
      <package-id>/
        manifest.json
        graph.snapshot.json
        context.manifest.json
        approval-state.json
        stages/
          01-plan/
            stage.manifest.json
            proposals/
            diffs/
            findings.json
            reviewer-notes.md
          02-scaffold/
            stage.manifest.json
            proposals/
            diffs/
            findings.json
            reviewer-notes.md
```

`manifest.json` records graph id, package id, schema versions, bundle root, generated stages, creation time, generator version, and safety policy. `graph.snapshot.json` freezes the exact graph used for the package. `context.manifest.json` records every strict and advisory context attachment used during generation. `approval-state.json` is updated as the user reviews, approves, applies, blocks, or supersedes proposals.

### Path allowlist rules

Generated proposals can only target relative paths inside an allowlisted bundle or repository root. The path contract must reject:

- absolute paths,
- paths containing `..` traversal,
- paths outside the selected root after normalization,
- `.env`, secret, credential, token, private key, and machine-local config files,
- files inside `skills/`, `node_modules/`, build output, package caches, generated dependency folders, and `.git/`,
- destructive renames or deletes unless a future contract explicitly supports them with separate approval.

The first implementation should allow Plan proposals under documentation paths and Scaffold proposals under explicit new project or manifest paths selected by the graph. Existing file modifications require a base hash and preview diff before apply.

### Command registry contract

Commands are registry entries, not arbitrary generated shell strings. Each command entry records:

- stable `command_id`,
- human-readable purpose,
- owning stage,
- executable and fixed arguments or argument schema,
- working-directory rules,
- allowed path inputs,
- whether it is read-only, local-write, or external-mutation,
- whether user confirmation is required,
- credential and environment requirements,
- output capture and redaction policy,
- summary fields to persist in findings.

The first implementation may record recommended commands for Plan and Scaffold readiness, but it should not run external-mutation commands. Code, Tests, and Validation generation must not be enabled until their command usage is represented through this registry and preview/apply has generalized file proposal support.

## 4) Generation stages and approval package structure

Generation is staged:

1. **Plan**: Convert the graph into solution intent, architecture, assumptions, risks, and implementation sequence.
2. **Scaffold**: Propose project structure, manifests, package names, dependencies already permitted by the repo, and non-secret config.
3. **Code**: Propose implementation files and integration glue. Deferred until the Phase 0 contracts exist and preview/apply is generalized across file proposals.
4. **Tests**: Propose unit, integration, eval, smoke, and UiPath validation coverage. Deferred on the same contract and generalized preview/apply boundary.
5. **Validation**: Run or summarize applicable static checks, readiness checks, analyzers, tests, and policy gates. Deferred for generated validation packages until commands are represented in the command registry.

Each stage produces an approval package, not direct files. The package is persisted under the selected UiPlan bundle and can be reopened by the UI.

The first implementation scope is intentionally narrow: generate Plan and Scaffold approval packages with durable approval metadata. Code, Tests, and Validation stay behind the same package contract until preview/apply is generalized and the command registry is in place.

Within a `.uiplan/generation/packages/<package-id>/` directory, the future all-stage structure is:

```text
<package-id>/
  manifest.json
  graph.snapshot.json
  context.manifest.json
  approval-state.json
  stages/
    01-plan/
      stage.manifest.json
      proposed-files/
      diffs/
      findings.json
      reviewer-notes.md
    02-scaffold/
      stage.manifest.json
      proposed-files/
      diffs/
      findings.json
      reviewer-notes.md
    03-code/
      stage.manifest.json
      proposed-files/
      diffs/
      findings.json
      reviewer-notes.md
    04-tests/
      stage.manifest.json
      proposed-files/
      diffs/
      findings.json
      reviewer-notes.md
    05-validation/
      stage.manifest.json
      validation-results/
      findings.json
      reviewer-notes.md
```

`manifest.json` records graph id, schema version, bundle root, generated stages, creation time, generator version, and safety policy. `graph.snapshot.json` freezes the exact graph used for the package. `context.manifest.json` records every strict and advisory context attachment used during generation. `approval-state.json` records durable per-stage and per-proposal approval metadata.

Each `stage.manifest.json` records:

- stage id and stage status,
- input graph hash,
- input context hashes,
- generated files,
- file ownership classification,
- required approvals,
- blocking findings,
- validation commands that were run or intentionally skipped,
- apply eligibility.

Each proposed file has:

- target path,
- file kind,
- owning node ids,
- project type ids,
- before hash when modifying an existing file,
- proposed content hash,
- unified diff when applicable,
- cited context references,
- reviewer status,
- apply status.

File drilldown is mandatory. A stage cannot be approved only at a summary level when it contains file changes. The user must be able to inspect each proposed file, see its source graph nodes, citations, diff, findings, and apply eligibility.

## 5) UI and workflow design

### Layout

The UI keeps the four-zone Studio layout and sharpens each zone around generation work.

**Left rail: Graph builder and source palette**

The left rail lists node templates, project type filters, context sources, and graph outline. Users can add process steps, project components, artifacts, tests, tools, assets, queues, docs context, skills, and gates. It also shows unresolved graph issues such as missing output type, missing project type, or strict context gaps.

**Center graph: Typed generation graph**

The center remains the canvas. Nodes display role, selected project types, output type, readiness, and approval status. Edges display relationship type. The canvas supports grouping by stage or project type without changing the underlying graph.

**Right rail: Node inspector**

The right rail edits the selected node or edge. For nodes, it shows role, description, project types, output type, context attachments, generation settings, strict/advisory policy, readiness, and linked file proposals. For edges, it shows edge type, direction, stage impact, and validation rules.

**Bottom panel: Approval package**

The bottom panel is the generation review surface. It contains stage tabs for Plan and Scaffold in the first implementation, plus disabled or future-labelled tabs for Code, Tests, and Validation. It also contains a file tree, diff viewer, citations, findings, reviewer notes, durable approval metadata, and apply controls. The default view is the current stage summary, but the user can drill down to every proposed file.

### Typical workflow

1. User creates or loads a UiPlan bundle.
2. User builds a typed graph using node templates and project type selections.
3. User attaches context from docs, library books, skills, tools, and source files.
4. Studio runs graph readiness checks and highlights missing required fields.
5. User selects **Generate Plan Package**.
6. Studio creates a Plan approval package with citations, proposed docs, and findings.
7. User reviews file drilldowns, requests changes, or approves the Plan stage.
8. After Plan approval, user generates Scaffold.
9. Each stage can use prior approved stages as strict context.
10. User applies only selected approved previews. Apply never publishes, deploys, or invokes live jobs.

The workflow is intentionally incremental. The first implementation stops at Plan and Scaffold packages. Code, Tests, and Validation generation are future stages that use the same contracts after preview/apply is generalized.

## 6) Backend and services design

### Graph service

The graph service owns schema validation, graph persistence, graph snapshots, typed edges, project type selections, and readiness calculations that do not require generation. It should expose load/save endpoints for `generation_graph.v1` and keep compatibility with existing diagram bundles through an upgrade path that maps current diagram nodes into typed graph nodes.

Primary responsibilities:

- validate node role, output type, and project type combinations,
- validate edge endpoints and edge types,
- compute stage ordering and stage eligibility,
- create immutable graph snapshots for approval packages,
- preserve older diagram data through explicit migration.

### Context service

The context service resolves context sources and labels them strict or advisory. It should use repository docs, library lookup/search services, curated skills, and tool descriptors through supported APIs rather than raw storage assumptions.

Primary responsibilities:

- list available context categories,
- attach context to graph, node, edge, file, or stage,
- resolve citations for strict context,
- detect unavailable or stale context,
- produce `context.manifest.json`,
- block strict-context generation when required citations are missing.

### Readiness service

The readiness service tells the UI whether a graph or stage is ready to generate.

Primary responsibilities:

- detect incomplete nodes,
- detect invalid project type combinations,
- detect missing strict context,
- detect stage dependency violations,
- detect unsupported output types for the selected project type,
- return findings grouped by graph, stage, node, edge, and file.

Readiness is advisory before generation and blocking for stage apply. A graph can be saved with readiness issues, but generation and apply must respect blockers.

### Generation service

The generation service creates approval packages. It does not write target implementation files. The first implementation routes only Plan and Scaffold generation.

Primary responsibilities:

- consume a graph snapshot and context manifest,
- route generation by stage and project type,
- generate proposed files and diffs,
- include citations for strict context,
- classify findings,
- record skipped commands or validation steps with reasons,
- produce a deterministic package manifest.

Generation should be deterministic for the same graph snapshot, context manifest, and generator version wherever practical. If model-assisted generation is used, the package records prompt inputs, selected context ids, and output hashes.

### Preview/apply service

The preview/apply service remains the only path from generated proposals to repository files.

Primary responsibilities:

- create hash-guarded previews,
- show unified diffs,
- apply only approved file proposals,
- refuse apply when the source file changed since preview,
- create backups for modified files,
- record apply results in approval state.

Apply is local file application only. It does not publish, deploy, invoke, queue, or mutate external UiPath resources.

### Validation service

The validation service runs or records checks appropriate to the stage and project type.

Primary responsibilities:

- run markdown/spec checks for Plan,
- validate project manifests and scaffold consistency for Scaffold,
- run type/lint/unit checks for Code where available,
- run test commands for Tests where available,
- summarize UiPath restore/analyze/test/pack readiness for Validation without deploying,
- classify findings as errors, warnings, or notes,
- preserve command output summaries without dumping large logs into the UI.

Validation should distinguish commands that were run from commands that are recommended but require user confirmation or external credentials. In the first implementation, validation behavior is limited to readiness findings and recorded recommended commands for Plan and Scaffold. Generated Validation packages are deferred until the command registry contract is implemented.

## 7) Safety and invariants

The first implementation must preserve these invariants:

- Generation creates approval packages, not direct implementation writes.
- Direct document or source writes are not part of generation.
- Preview/apply is the only route for local file changes.
- Apply requires an approved file proposal and a matching base hash.
- Plan and Scaffold are the only generated stages in the first implementation.
- Code, Tests, and Validation generation remain disabled until they use the same schema, storage, approval-state, path allowlist, and command-registry contracts.
- Strict citations are required for production, deployment, runtime, security, credential, Orchestrator resource, and validation nodes.
- Advisory context must be labelled and cannot satisfy strict citation requirements.
- No automatic deploy, publish, invoke, job run, package upload, asset creation, queue creation, or external resource mutation.
- Deployment and publish nodes can generate plans, commands, manifests, and validation checklists only.
- Secrets are never generated into files. Secret references can be proposed as asset names, environment variable names, or binding references.
- Existing user files are never overwritten without a preview, diff, approval, and hash check.
- Graph layout changes do not silently change generation semantics; semantics come from typed fields and edges.
- A stage can only use approved prior-stage outputs as strict context.
- Validation errors block apply for affected files unless the user explicitly marks a non-production exploratory exception. Runtime, deploy, security, and production-scoped nodes do not allow that exception.

## 8) Testing and verification strategy

Testing should cover the graph model, service behavior, UI workflow, and safety gates.

### Unit tests

- Schema validation for node roles, output types, project type lists, and edge types.
- Readiness checks for missing required fields and missing strict citations.
- Context manifest generation and citation enforcement.
- Approval state transitions for Plan and Scaffold packages, with contract coverage proving Code, Tests, and Validation remain disabled until enabled explicitly.
- Preview/apply hash checks and superseded preview handling.
- Migration from existing diagram data to `generation_graph.v1`.

### Service tests

- Graph load/save/snapshot endpoints.
- Context source listing and context attachment behavior.
- Stage package generation for Plan and Scaffold on a small mixed graph.
- Strict context blocking for deploy/runtime nodes.
- Advisory context allowed for exploratory planning nodes.
- File proposal manifests with target path, diff, citations, and ownership metadata.
- Validation findings grouped by graph, stage, node, edge, and file.

### UI tests

- Add mixed node types from the left rail.
- Select multiple project types on one node.
- Edit node role, output type, context policy, and context attachments in the right rail.
- Generate a Plan approval package and review it in the bottom panel.
- Drill into a proposed file, inspect citations and diff, approve it, and apply through preview/apply.
- Show blockers when strict citations are missing.
- Ensure deploy/publish nodes never expose automatic deploy or publish actions.

### End-to-end smoke tests

- Create a graph with a process step, coded agent component, RPA component, test node, skill node, library context node, queue node, and deployment gate.
- Generate Plan and Scaffold packages with durable approval metadata.
- Verify no target source files change before apply.
- Apply one approved documentation preview.
- Confirm validation state records the apply and leaves deploy/publish as manual guarded steps.

## 9) Explicit non-goals for first implementation

- No automatic generation directly into target source files.
- No Code, Tests, or generated Validation packages in the first implementation.
- No automatic publish, deploy, invoke, job run, queue creation, asset creation, or package upload.
- No full visual BPMN or Studio Web replacement.
- No multi-user real-time collaboration.
- No remote approval workflow outside the local Studio approval package.
- No schema for every possible UiPath product surface; v1 supports a practical typed model and can grow.
- No guarantee that generated code is production-ready without human review and validation.
- No replacement for specialist skills or UiPath CLIs; Studio orchestrates and records their guidance.
- No secret material generation or credential storage.
- No broad repository refactor as part of the first implementation.

## 10) Open risks and mitigations

**Risk: The graph model becomes too broad to implement in one pass.**

Mitigation: Implement `generation_graph.v1` with the listed roles and output types, but ship the first UI around the most common path: process steps, project components, docs context, skills, Plan artifacts, Scaffold artifacts, and gates. Keep less common roles such as queues and assets supported in schema first, then add richer UI affordances.

**Risk: Multiple project types per node complicate generation routing.**

Mitigation: Treat project types as explicit routing hints and generate per-project proposals inside the approval package. A node can own multiple file proposals, each tagged with one project type and target project boundary.

**Risk: Strict citation rules slow exploratory work.**

Mitigation: Use mixed context policy. Exploratory and planning nodes can use advisory context, while production, runtime, deploy, security, Orchestrator resource, and validation nodes require strict citations.

**Risk: Users confuse approval with apply.**

Mitigation: Keep approval state and apply state visually separate. Approval means a proposal is accepted for application. Apply means a specific preview was written locally after a base-hash check.

**Risk: Generated packages drift from the current graph.**

Mitigation: Store immutable graph snapshots and input hashes in each package. When the graph changes, mark older stage outputs as reviewable history but not current apply candidates.

**Risk: Validation requires tools or credentials that are not available locally.**

Mitigation: Validation records unavailable checks as structured findings with clear reasons. It can recommend commands without running deploy, publish, invoke, or external mutation steps.

**Risk: Existing preview/apply APIs are too document-focused for source generation.**

Mitigation: Extend preview/apply around generic file proposals while preserving the current hash-guarded behavior. The old document preview path can become a specialized case of the broader file proposal model.

**Risk: Phase 0 becomes an implementation project instead of a contract.**

Mitigation: Keep Phase 0 scoped to schema files, state transitions, storage layout, path allowlist, and command registry definitions. It should not generate Plan, Scaffold, Code, Tests, or Validation content.

**Risk: Context from tools, skills, and books becomes stale.**

Mitigation: Store context ids, citations, and resolution timestamps in the context manifest. Strict context is revalidated before apply for production, runtime, deploy, and validation-scoped proposals.

## Implementation planning boundary

This design is intentionally sized for one follow-on implementation plan with phases:

0. Phase 0 contract: schema files, approval state machine, package/proposal storage, path allowlist, and command registry.
1. Graph schema and migration against the Phase 0 contract.
2. Context and readiness services for Plan and Scaffold eligibility.
3. Approval package generation for Plan and Scaffold only, including durable approval metadata.
4. UI rails and bottom approval package review for Plan and Scaffold.
5. Generic file proposal preview/apply for approved Plan and Scaffold proposals.
6. Future Code, Tests, and Validation stages after the same contracts and generalized preview/apply are proven.

The phases can ship incrementally, but they share one product direction: UiPlan Studio becomes a typed, grounded, approval-first planning-to-code workbench.

## Implementation Notes

- Phase 0 implementation standardizes package stage file proposal directories as `proposals/` in manifests and API payloads. Existing prose that mentions `proposed-files/` is treated as historical wording for the same concept.
