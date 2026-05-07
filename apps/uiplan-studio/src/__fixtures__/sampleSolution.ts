import type { ProjectGraph } from "./types";

/**
 * Multi-product Solution fixture exercising layers a single-product graph
 * does not: Maestro Flow, Coded App, Orchestrator (queue, asset, process),
 * Test Manager. Demonstrates the full surface a "uipath solution" repo
 * can produce, mapped against CLAUDE.md §1 project types.
 */
export const sampleSolutionGraph: ProjectGraph = {
  projectType: "solution",
  meta: {
    worktree_id: "solution",
    branch: "feat/q3-solution",
    revision: "sol-fixture-1",
    indexed_at: new Date().toISOString(),
    project_type: "solution",
  },
  overview: {
    name: "Order-to-Cash Solution",
    summary:
      "Multi-project UiPath Solution. The Service Desk Action App lets agents kick off the order-to-cash flow; " +
      "a Maestro Flow orchestrates Salesforce → invoice generation → Action Center approval → SAP posting; " +
      "underlying RPA workflows handle the SAP screens; Test Manager covers the regression suite.",
    owner: "Finance Operations",
    stakeholders: ["Finance Ops", "Customer Service", "Compliance"],
    triggers: [
      { kind: "manual",     description: "Agent submits an order in the Coded App" },
      { kind: "queue",      description: "Bulk uploads land in the SAPInbound queue" },
      { kind: "scheduled",  description: "Nightly close runs the reconciliation flow" },
    ],
    actors: [
      { name: "Service Desk Agent", role: "submitter" },
      { name: "Finance Manager",    role: "human-in-the-loop" },
      { name: "Salesforce",         role: "system of record" },
      { name: "SAP S/4HANA",        role: "system of execution" },
      { name: "OpenAI",             role: "LLM provider via Integration Service" },
    ],
    kpis: [
      { label: "volume",       value: "2,400 / day" },
      { label: "p95 SLA",      value: "12 minutes" },
      { label: "STP rate",     value: "78%" },
      { label: "savings",      value: "~12 FTE / yr" },
    ],
    pdd: { doc_id: "PDD-O2C-02", section: "Order-to-Cash", path: "docs/PDD-O2C-02.md" },
  },
  nodes: [
    // ---- APP ----
    { id: "app:ServiceDesk", label: "ServiceDesk.app", kind: "coded_app", layer: "app",
      status: "ok", business_status: "live",
      roles: ["entrypoint", "actor"],
      desc: "Coded Web App. Agents submit and triage orders.",
      concept:
        "Built with @uipath/uipath-typescript SDK. Surfaces a list of pending orders and an order-detail screen, " +
        "and exposes a Coded Action App entry that kicks off the Maestro flow.",
      code: { path: "apps/service-desk/app.config.json", lines: "1-40", language: "json",
        snippet: "{\n  \"entry\": \"src/main.tsx\",\n  \"actions\": [\n    {\"id\": \"submitOrder\", \"schema\": \"action-schema.json\"}\n  ]\n}" },
      business_meta: { owner: "Customer Service", volume: "2,400 / day", sla: "page-load < 1.2s" },
      pdd_anchor: { doc_id: "PDD-O2C-02", section: "§2 Service Desk UI" },
      skills: [{ id: "uipath-coded-apps", path: ".cursor/skills/uipath-coded-apps/SKILL.md", reason: "Coded App authoring + packaging." }],
    },
    { id: "app:submitAction", label: "submitOrder", kind: "action_app", layer: "app",
      status: "ok", business_status: "live",
      desc: "Coded Action App. Schema-driven entry into the Maestro flow.",
      code: { path: "apps/service-desk/action-schema.json", lines: "1-30",
        snippet: "{\n  \"input\":  {\"orderId\":\"string\",\"amount\":\"number\"},\n  \"output\": {\"caseId\":\"string\"}\n}" } },

    // ---- MAESTRO ----
    { id: "ma:orderFlow", label: "OrderToCash.flow", kind: "flow", layer: "maestro",
      status: "ok", business_status: "live",
      roles: ["entrypoint"],
      desc: "Maestro Flow. Orchestrates the full O2C pipeline.",
      concept:
        "Studio Web Flow (.flow). Sequences validation → invoice generation → human approval → SAP posting. " +
        "Each step is a typed task; failures route to the exception lane.",
      code: { path: "maestro/OrderToCash.flow", lines: "—",
        snippet: "tasks:\n  - id: validate\n    type: GenAI.Classify\n  - id: generate\n    type: ProcessMining.InvokeProcess\n  - id: approve\n    type: ActionCenter.Approval\n  - id: post\n    type: ProcessMining.InvokeProcess" },
      business_meta: { owner: "Finance Operations", sla: "p95 12 min", risk: "high" },
      pdd_anchor: { doc_id: "PDD-O2C-02", section: "§3 Maestro Orchestration" },
      skills: [{ id: "uipath-maestro-flow", path: ".cursor/skills/uipath-maestro-flow/SKILL.md", reason: "Maestro Flow authoring + lifecycle." }],
      citations: [
        { book_id: "uipath-docs", chapter_id: "maestro", section_id: "flow-overview",
          snippet: "Flows orchestrate typed tasks across personas, using a serverless runtime." },
      ],
    },
    { id: "ma:validate", label: "Validate Order", kind: "activity", layer: "maestro",
      status: "ok", desc: "GenAI classifier. Splits into auto-approvable and review-required.",
      code: { path: "OrderToCash.flow", lines: "—",
        snippet: "type: GenAI.Classify\ninput:  ${order}\nlabels: [auto, review, reject]" } },
    { id: "ma:generate", label: "Generate Invoice", kind: "activity", layer: "maestro",
      status: "ok", desc: "Calls the SAP invoice-generation RPA workflow.",
      code: { path: "OrderToCash.flow", lines: "—",
        snippet: "type: ProcessMining.InvokeProcess\nprocess: GenerateInvoice\ninput:  ${order}" } },
    { id: "ma:approve", label: "Approval Gate", kind: "activity", layer: "maestro",
      status: "ok", roles: ["hitl", "approval"],
      desc: "Action Center HITL. Finance Manager approves or rejects.",
      code: { path: "OrderToCash.flow", lines: "—",
        snippet: "type: ActionCenter.Approval\nassignee: ${approverGroup}\ntimeout: PT4H" },
      skills: [{ id: "uipath-human-in-the-loop", path: ".cursor/skills/uipath-human-in-the-loop/SKILL.md", reason: "Approval gate." }] },
    { id: "ma:post", label: "Post to SAP", kind: "activity", layer: "maestro",
      status: "ok", desc: "Invokes the SAP posting RPA workflow.",
      code: { path: "OrderToCash.flow", lines: "—",
        snippet: "type: ProcessMining.InvokeProcess\nprocess: PostToSAP\ninput:  ${invoice}" } },

    // ---- RPA ----
    { id: "rpa:GenerateInvoice", label: "GenerateInvoice.xaml", kind: "workflow", layer: "rpa",
      status: "ok", business_status: "live",
      desc: "Modern XAML workflow. Renders the invoice PDF and uploads to the bucket.",
      code: { path: "rpa/GenerateInvoice/Main.xaml", lines: "—",
        snippet: "<Sequence>\n  <ReadTemplate Path=\"templates/invoice.docx\" />\n  <RenderPDF />\n  <UploadToBucket Bucket=\"invoices\" />\n</Sequence>" },
      skills: [{ id: "uipath-rpa", path: ".cursor/skills/uipath-rpa/SKILL.md", reason: "Modern-experience XAML." }],
    },
    { id: "rpa:PostToSAP", label: "PostToSAP.xaml", kind: "workflow", layer: "rpa",
      status: "warn", business_status: "in-build",
      desc: "Posts the approved invoice to SAP via the SAP UI automation activities.",
      code: { path: "rpa/PostToSAP/Main.xaml", lines: "—",
        snippet: "<UseApplication Path=\"saplogon.exe\">\n  <Click Selector=\"...\" />\n  <Type Text=\"[invoiceId]\" />\n</UseApplication>" } },

    // ---- ORCHESTRATOR ----
    { id: "orch:queue", label: "SAPInbound", kind: "queue", layer: "orchestrator",
      status: "ok", desc: "Bulk-upload queue. Process each item via the order flow.",
      code: { path: "orchestrator/queues/SAPInbound.json", lines: "1-20",
        snippet: "{\n  \"name\": \"SAPInbound\",\n  \"folder\": \"Finance/Prod\",\n  \"slaInMinutes\": 30\n}" } },
    { id: "orch:asset", label: "SAP_Credentials", kind: "asset", layer: "orchestrator",
      status: "ok", desc: "Encrypted credential asset. Read by PostToSAP at runtime.",
      code: { path: "orchestrator/assets/SAP_Credentials.json", lines: "1-12",
        snippet: "{\n  \"name\": \"SAP_Credentials\",\n  \"type\": \"Credential\",\n  \"folder\": \"Finance/Prod\"\n}" } },
    { id: "orch:process", label: "OrderToCashProcess", kind: "process", layer: "orchestrator",
      status: "ok", desc: "Deployed Maestro process bound to the Finance/Prod folder.",
      code: { path: "orchestrator/processes/OrderToCashProcess.json", lines: "1-15",
        snippet: "{\n  \"name\": \"OrderToCashProcess\",\n  \"package\": \"OrderToCash\",\n  \"folder\": \"Finance/Prod\"\n}" } },

    // ---- TEST ----
    { id: "test:o2c", label: "OrderToCash.testset", kind: "test_set", layer: "test",
      status: "ok", desc: "Regression suite. Run on every release.",
      code: { path: "tests/OrderToCash.testset.json", lines: "1-12",
        snippet: "{\n  \"cases\": [\"happy-path\", \"reject-flow\", \"sap-timeout\", \"queue-bulk-load\"]\n}" },
      skills: [{ id: "uipath-test", path: ".cursor/skills/uipath-test/SKILL.md", reason: "Test Manager test sets." }] },
    { id: "test:happy", label: "happy-path", kind: "test_case", layer: "test",
      status: "ok", desc: "End-to-end happy path with auto-approval." },
    { id: "test:reject", label: "reject-flow", kind: "test_case", layer: "test",
      status: "warn", desc: "Manager rejects → exception lane → audit log present." },
    { id: "test:sap", label: "sap-timeout", kind: "test_case", layer: "test",
      status: "error", desc: "SAP screen times out — currently failing intermittently in CI." },

    // ---- EXTERNAL ----
    { id: "ext:sf",  label: "Salesforce", kind: "tool", layer: "external",
      status: "ok", desc: "System of record for orders and customers." },
    { id: "ext:sap", label: "SAP S/4HANA", kind: "tool", layer: "external",
      status: "ok", desc: "System of execution. Posts invoices and clears AR." },
    { id: "ext:openai", label: "OpenAI (via Integration Service)", kind: "tool", layer: "external",
      status: "ok", desc: "Used by the Maestro classifier task." },
  ],
  edges: [
    // App → Maestro
    { id: "s1",  source: "app:ServiceDesk",   target: "app:submitAction", kind: "import" },
    { id: "s2",  source: "app:submitAction",  target: "ma:orderFlow",     kind: "invokes",    label: "submit",   path_class: "happy",
      desc: "Action App boots the Maestro flow with the typed input schema." },
    // Maestro internal
    { id: "s3",  source: "ma:orderFlow",      target: "ma:validate",      kind: "transition", path_class: "happy" },
    { id: "s4",  source: "ma:validate",       target: "ext:openai",       kind: "call",       desc: "GenAI classify call." },
    { id: "s5",  source: "ma:validate",       target: "ma:generate",      kind: "transition", path_class: "happy", label: "auto" },
    { id: "s6",  source: "ma:validate",       target: "ma:approve",       kind: "transition", path_class: "alt",   label: "review" },
    { id: "s7",  source: "ma:approve",        target: "ma:generate",      kind: "transition", path_class: "happy", label: "approved" },
    { id: "s8",  source: "ma:approve",        target: "ma:orderFlow",     kind: "transition", path_class: "exception", label: "rejected",
      desc: "Reject path: bubble up to the flow root for the exception handler." },
    { id: "s9",  source: "ma:generate",       target: "rpa:GenerateInvoice", kind: "invokes", path_class: "happy" },
    { id: "s10", source: "ma:generate",       target: "ma:post",          kind: "transition", path_class: "happy" },
    { id: "s11", source: "ma:post",           target: "rpa:PostToSAP",    kind: "invokes",    path_class: "happy" },
    // RPA → External
    { id: "s12", source: "rpa:GenerateInvoice", target: "ext:sf",        kind: "call",       desc: "Reads order line items." },
    { id: "s13", source: "rpa:PostToSAP",     target: "ext:sap",          kind: "call",       desc: "Posts invoice to SAP." },
    { id: "s14", source: "rpa:PostToSAP",     target: "orch:asset",       kind: "data",       desc: "Reads SAP credentials at runtime." },
    // Orchestrator wiring
    { id: "s15", source: "orch:queue",        target: "ma:orderFlow",     kind: "queue",      label: "dequeue",  path_class: "happy",
      desc: "Bulk-upload trigger: each item starts the flow." },
    { id: "s16", source: "orch:process",      target: "ma:orderFlow",     kind: "publish",    desc: "Deployed process binding." },
    // Tests
    { id: "s17", source: "test:o2c",  target: "test:happy",  kind: "import" },
    { id: "s18", source: "test:o2c",  target: "test:reject", kind: "import" },
    { id: "s19", source: "test:o2c",  target: "test:sap",    kind: "import" },
    { id: "s20", source: "test:happy", target: "ma:orderFlow", kind: "call", desc: "Happy-path test asserts the flow's full traversal." },
    { id: "s21", source: "test:sap",  target: "rpa:PostToSAP", kind: "call", desc: "Targets the SAP posting workflow directly." },
  ],
  errors: [
    { nodeId: "rpa:PostToSAP", severity: "warn",  message: "in-build: SAP screen automation is fragile, see uipath-diagnostics" },
    { nodeId: "test:sap",      severity: "error", message: "intermittent CI failure on sap-timeout test" },
  ],
};

export const sampleEmptyGraph: ProjectGraph = {
  projectType: "empty",
  meta: { worktree_id: "empty", branch: "—", revision: "—", indexed_at: new Date().toISOString(), project_type: "—" },
  overview: {
    name: "(empty worktree)",
    summary: "This fixture has no nodes — used to exercise the empty-state UI.",
  },
  nodes: [],
  edges: [],
  errors: [],
};
