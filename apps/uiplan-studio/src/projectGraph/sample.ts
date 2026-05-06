import type { ProjectGraph } from "./types";

/**
 * Canonical sample graph representing a full-stack UiPath project.
 * Used as a fallback when the indexer endpoint is unavailable, and as
 * the demo content for the Project Explorer view.
 *
 * Cross-layer concepts illustrated:
 *  - UI <- HITL bridge from RPA approval activity (closes the loop)
 *  - Agent dispatch -> RPA workflow (Dev persona writes XAML, hands off)
 *  - Recursive drill-down (CheckoutForm -> validate -> ...)
 *  - HITL roles, status pips, library citations, skill references.
 */
export const sampleGraph: ProjectGraph = {
  projectType: "mixed",
  meta: {
    worktree_id: "demo",
    branch: "main",
    revision: "sample-fixture",
    indexed_at: new Date().toISOString(),
    project_type: "mixed",
  },
  overview: {
    name: "Renewal Commitment",
    summary:
      "End-to-end renewal commitment processing. A salesperson submits a commitment in the web UI, " +
      "the request is validated and routed through a coded-agent pipeline (BA → SA → Dev → QA), and a " +
      "UiPath workflow executes the back-office steps with a human approval gate before DocuSign dispatch.",
    owner: "Sales Operations",
    stakeholders: ["Sales Operations", "Finance", "Legal", "Customer Success"],
    triggers: [
      { kind: "http", description: "POST /commitments from the Checkout UI" },
      { kind: "manual", description: "Sales rep submits the renewal form" },
    ],
    actors: [
      { name: "Sales Rep", role: "submitter" },
      { name: "Approver Manager", role: "human-in-the-loop" },
      { name: "Salesforce", role: "system of record" },
      { name: "DocuSign", role: "agreement signing" },
      { name: "AWS Bedrock", role: "LLM provider" },
    ],
    kpis: [
      { label: "volume", value: "120 / day" },
      { label: "p95 SLA", value: "8 minutes" },
      { label: "auto-approval rate", value: "62%" },
      { label: "savings vs. manual", value: "~5.5 FTE / yr" },
    ],
    pdd: { doc_id: "PDD-RENEWAL-01", section: "Renewal Commitment Process", path: "docs/PDD-RENEWAL-01.md" },
  },
  nodes: [
    // ============== UI ==============
    {
      id: "fe:App",
      label: "App.tsx",
      kind: "file",
      layer: "ui",
      status: "ok",
      meta: { lines: 84, role: "root" },
      desc: "Root component. Mounts router, providers, error boundary.",
      concept:
        "The App component is the composition root for the React tree. It wires up the router, the CopilotKit provider, and the global error boundary. Nothing here owns business logic — it's structural scaffolding.",
      code: {
        path: "src/App.tsx",
        lines: "1-84",
        language: "tsx",
        snippet:
`import { CopilotKit } from "@copilotkit/react-core";
import { Router } from "./router";

export function App() {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit">
      <ErrorBoundary>
        <Router />
      </ErrorBoundary>
    </CopilotKit>
  );
}`,
      },
    },
    {
      id: "fe:CheckoutForm",
      label: "CheckoutForm.tsx",
      kind: "file",
      layer: "ui",
      status: "ok",
      meta: { lines: 212 },
      desc: "Collects renewal commitment details. Validation + submit.",
      concept:
        "User-facing form for the renewal commitment workflow. Owns local form state, runs zod validation, and POSTs to /commitments. On success, shows the inline ApprovalWidget rendered via generative UI.",
      code: {
        path: "src/components/CheckoutForm.tsx",
        lines: "44-118",
        language: "tsx",
        snippet:
`const onSubmit = async (data: FormData) => {
  const validated = commitmentSchema.parse(data);
  const result = await api.post("/commitments", validated);
  setApproval(result);
};`,
      },
      children: {
        nodes: [
          {
            id: "cf:schema", label: "commitmentSchema", kind: "module", layer: "ui",
            status: "ok",
            desc: "Zod schema describing the commitment payload shape.",
            concept: "The single source of truth for what a valid commitment looks like.",
            code: { path: "CheckoutForm.tsx", lines: "12-28",
              snippet: "const commitmentSchema = z.object({\n  customer: z.string().min(1),\n  amount:   z.number().positive(),\n  approvers: z.array(z.string().email()),\n});" },
          },
          {
            id: "cf:fields", label: "FormFields", kind: "function", layer: "ui",
            status: "ok",
            desc: "Renders the controlled input fields.",
            concept: "Pure presentational sub-component. Takes register from react-hook-form and returns the labeled inputs.",
            code: { path: "CheckoutForm.tsx", lines: "30-78",
              snippet: "function FormFields({ register, errors }) {\n  return (\n    <>\n      <input {...register(\"customer\")} />\n      <input {...register(\"amount\")} type=\"number\" />\n    </>\n  );\n}" },
          },
          {
            id: "cf:validate", label: "validate", kind: "function", layer: "ui",
            status: "ok",
            desc: "Runs zod validation on the form data.",
            concept: "Wraps schema.parse in a try/catch. Returns either parsed data or a normalized error map keyed by field.",
            code: { path: "CheckoutForm.tsx", lines: "80-92",
              snippet: "const validate = (data: unknown) => {\n  try { return { ok: true, data: schema.parse(data) }; }\n  catch (e) { return { ok: false, errors: e.flatten() }; }\n};" },
          },
          {
            id: "cf:submit", label: "onSubmit", kind: "function", layer: "ui",
            status: "ok",
            desc: "Submit handler — validates, posts, sets approval state.",
            concept: "Orchestrates the full submit flow. On success, lifts the API response to local state which causes the ApprovalWidget to render inline.",
            code: { path: "CheckoutForm.tsx", lines: "94-110",
              snippet: "const onSubmit = async (data) => {\n  const r = validate(data);\n  if (!r.ok) return setErrors(r.errors);\n  const result = await api.post(\"/commitments\", r.data);\n  setApproval(result);\n};" },
          },
        ],
        edges: [
          { id: "ce1", source: "cf:fields",   target: "cf:validate", kind: "call",       desc: "Field change handler invokes the schema validator." },
          { id: "ce2", source: "cf:validate", target: "cf:submit",   kind: "call",       desc: "Submit calls validate before issuing the POST." },
          { id: "ce3", source: "cf:schema",   target: "cf:validate", kind: "import",     desc: "Validate uses the zod schema as parser." },
        ],
      },
    },
    {
      id: "fe:ApprovalWidget", label: "ApprovalWidget.tsx", kind: "file", layer: "ui",
      status: "ok",
      meta: { lines: 96 },
      roles: ["hitl"],
      desc: "Inline approval card. Rendered via generative UI from agent action.",
      concept:
        "Pure presentational component invoked by the agent's `requestApproval` action. The render function receives args (customer, amount, approvers) and the component handles the approve/reject UX.",
      code: {
        path: "src/components/ApprovalWidget.tsx",
        lines: "12-58",
        language: "tsx",
        snippet:
`useCopilotAction({
  name: "requestApproval",
  parameters: [
    { name: "customer", type: "string" },
    { name: "amount",   type: "number" },
  ],
  render: ({ args }) => <ApprovalCard {...args} />,
});`,
      },
      citations: [
        { book_id: "uipath-docs", chapter_id: "agents", section_id: "human-in-the-loop",
          snippet: "Human-in-the-Loop nodes pause execution and surface an approval card to the operator." },
      ],
      skills: [
        { id: "uipath-human-in-the-loop", path: ".cursor/skills/uipath-human-in-the-loop/SKILL.md",
          reason: "Approval widgets render the HITL surface for tokenized resume." },
      ],
    },
    {
      id: "fe:api", label: "api/client.ts", kind: "file", layer: "ui",
      status: "ok",
      meta: { lines: 54 },
      desc: "Typed fetch wrapper. Single network surface for the FE.",
      concept:
        "Small wrapper around fetch with typed responses, JWT injection, and error normalization. Centralizing this means every component talks to the backend through one place.",
      code: {
        path: "src/api/client.ts",
        lines: "1-54",
        language: "ts",
        snippet:
`export const api = {
  post: async <T>(path: string, body: unknown): Promise<T> => {
    const res = await fetch(\`/api\${path}\`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...auth() },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new ApiError(res.status, await res.text());
    return res.json();
  },
};`,
      },
    },
    {
      id: "fe:Legacy", label: "LegacyHelpers.ts", kind: "file", layer: "ui",
      status: "warn",
      meta: { lines: 41 },
      roles: ["deprecated"],
      desc: "Unused module. No inbound imports — candidate for removal.",
      concept:
        "Dead code from a previous iteration. Kept here intentionally to demonstrate orphan detection in the graph analysis.",
      code: {
        path: "src/lib/LegacyHelpers.ts",
        lines: "1-41",
        language: "ts",
        snippet: "// no inbound imports — safe to delete",
      },
    },

    // ============== API ==============
    {
      id: "api:routes", label: "POST /commitments", kind: "endpoint", layer: "api",
      status: "ok",
      roles: ["entrypoint"],
      desc: "FastAPI route. Authenticates, validates, dispatches to agent supervisor.",
      concept:
        "The single ingress point for commitment requests. Validates the JWT, runs role-based access checks, normalizes the payload, then hands off to the LangGraph supervisor via `invoke()`.",
      code: {
        path: "backend/routes/commitments.py",
        lines: "22-58",
        language: "python",
        snippet:
`@router.post("/commitments")
async def create_commitment(
    payload: CommitmentIn,
    user: User = Depends(verify_jwt),
):
    require_role(user, "sales_ops")
    state = await supervisor.ainvoke({"input": payload.dict()})
    return state["result"]`,
      },
    },
    {
      id: "api:auth", label: "auth.py", kind: "module", layer: "api",
      status: "ok",
      meta: { lines: 130, algorithm: "HS256" },
      desc: "JWT verification + role-based access control.",
      concept:
        "Stateless JWT verification using the shared HS256 secret. Exposes `verify_jwt` as a FastAPI dependency and `require_role` as a guard.",
      code: {
        path: "backend/auth.py",
        lines: "44-78",
        language: "python",
        snippet:
`def verify_jwt(token: str = Header(...)) -> User:
    try:
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(401)
    return User(**payload)`,
      },
    },

    // ============== AGENT ==============
    {
      id: "ag:supervisor", label: "Supervisor", kind: "agent_node", layer: "agent",
      status: "ok",
      desc: "Routes work to BA / SA / Dev / QA personas based on graph state.",
      concept:
        "LangGraph node that inspects the current state and decides which persona to invoke next. Implements the conditional edges that drive the BA→SA→Dev→QA pipeline, plus the QA loopback for failed validations.",
      code: {
        path: "agent/graph.py",
        lines: "84-122",
        language: "python",
        snippet:
`def supervisor(state: AgentState) -> dict:
    if not state.get("ba_output"):     return {"next": "ba"}
    if not state.get("sa_output"):     return {"next": "sa"}
    if not state.get("dev_output"):    return {"next": "dev"}
    if not state.get("qa_passed"):     return {"next": "qa"}
    return {"next": END}`,
      },
      skills: [
        { id: "uipath-agents", path: ".cursor/skills/uipath-agents/SKILL.md",
          reason: "Supervisor orchestrates a coded-agent persona pipeline." },
      ],
      citations: [
        { book_id: "uipath-docs", chapter_id: "agents", section_id: "langgraph-supervisor",
          snippet: "Supervisor patterns inspect graph state and route to the next persona via conditional edges." },
      ],
      children: {
        nodes: [
          { id: "sup:read_state", label: "read_state", kind: "function", layer: "agent",
            status: "ok",
            desc: "Pull current AgentState from the graph runtime.",
            code: { path: "agent/graph.py", lines: "84-90",
              snippet: "def read_state(g: StateGraph) -> AgentState:\n    return g.snapshot().values" } },
          { id: "sup:check_ba", label: "check_ba_output", kind: "function", layer: "agent",
            status: "ok",
            desc: "Has the BA persona produced its requirements artifact yet?",
            code: { path: "agent/graph.py", lines: "92-95",
              snippet: "if not state.get(\"ba_output\"):\n    return {\"next\": \"ba\"}" } },
          { id: "sup:check_sa", label: "check_sa_output", kind: "function", layer: "agent",
            status: "ok",
            desc: "Has the SA persona produced its architecture spec yet?",
            code: { path: "agent/graph.py", lines: "97-100",
              snippet: "if not state.get(\"sa_output\"):\n    return {\"next\": \"sa\"}" } },
          { id: "sup:check_dev", label: "check_dev_output", kind: "function", layer: "agent",
            status: "ok",
            desc: "Has the Dev persona generated artifacts yet?",
            code: { path: "agent/graph.py", lines: "102-105",
              snippet: "if not state.get(\"dev_output\"):\n    return {\"next\": \"dev\"}" } },
          { id: "sup:check_qa", label: "check_qa_passed", kind: "function", layer: "agent",
            status: "warn",
            desc: "Did QA validate the Dev output? Loop back if not.",
            code: { path: "agent/graph.py", lines: "107-115",
              snippet: "if not state.get(\"qa_passed\"):\n    return {\"next\": \"qa\"}" } },
          { id: "sup:terminate", label: "return END", kind: "function", layer: "agent",
            status: "ok",
            desc: "All gates passed — terminate the graph successfully.",
            code: { path: "agent/graph.py", lines: "117-118",
              snippet: "return {\"next\": END}" } },
        ],
        edges: [
          { id: "se1", source: "sup:read_state", target: "sup:check_ba",  kind: "transition" },
          { id: "se2", source: "sup:check_ba",   target: "sup:check_sa",  kind: "transition", label: "ok" },
          { id: "se3", source: "sup:check_sa",   target: "sup:check_dev", kind: "transition", label: "ok" },
          { id: "se4", source: "sup:check_dev",  target: "sup:check_qa",  kind: "transition", label: "ok" },
          { id: "se5", source: "sup:check_qa",   target: "sup:terminate", kind: "transition", label: "pass" },
        ],
      },
    },
    {
      id: "ag:ba", label: "BA Persona", kind: "agent_node", layer: "agent",
      status: "ok",
      desc: "Reads PDD inputs. Drafts business requirements artifact.",
      concept:
        "Business Analyst persona — first stop in the pipeline. Reads the user's PDD/intake, produces a structured requirements document. Uses Bedrock Claude with a BA system prompt and few-shot examples.",
      code: { path: "agent/personas/ba.py", lines: "12-44", language: "python",
        snippet:
`async def ba_persona(state: AgentState) -> dict:
    response = await bedrock.ainvoke([
        SystemMessage(BA_PROMPT),
        HumanMessage(state["input"]),
    ])
    return {"ba_output": parse_ba(response)}` },
      skills: [{ id: "uipath-solution-design", path: ".cursor/skills/uipath-solution-design/SKILL.md",
        reason: "BA persona drafts the spec layer of the SDD pipeline." }],
    },
    {
      id: "ag:sa", label: "SA Persona", kind: "agent_node", layer: "agent",
      status: "ok",
      desc: "Designs solution architecture from BA output.",
      concept:
        "Solution Architect persona. Takes the BA's requirements and produces an architecture spec — components, data flow, integration points. This becomes the contract the Dev persona implements against.",
      code: { path: "agent/personas/sa.py", lines: "12-44", language: "python",
        snippet:
`async def sa_persona(state: AgentState) -> dict:
    response = await bedrock.ainvoke([
        SystemMessage(SA_PROMPT),
        HumanMessage(state["ba_output"]),
    ])
    return {"sa_output": parse_sa(response)}` },
    },
    {
      id: "ag:dev", label: "Dev Persona", kind: "agent_node", layer: "agent",
      status: "ok",
      desc: "Generates production code / XAML from SA design.",
      concept:
        "Developer persona. Reads the SA spec and produces concrete artifacts: code files, UiPath XAML, configuration. The dispatch edge to Main.xaml means a successful run hands off the generated workflow to UiPath.",
      code: { path: "agent/personas/dev.py", lines: "20-62", language: "python",
        snippet:
`async def dev_persona(state: AgentState) -> dict:
    artifacts = await generate_artifacts(state["sa_output"])
    if artifacts.kind == "xaml":
        await dispatch_to_uipath(artifacts)
    return {"dev_output": artifacts}` },
      skills: [{ id: "uipath-rpa", path: ".cursor/skills/uipath-rpa/SKILL.md",
        reason: "Dev persona emits XAML; uipath-rpa governs modern-experience authoring." }],
    },
    {
      id: "ag:qa", label: "QA Persona", kind: "agent_node", layer: "agent",
      status: "warn",
      desc: "Validates output, runs analyzer. Loops back on failure.",
      concept:
        "Quality Assurance persona. Runs structural validation, calls the UiPath Workflow Analyzer for XAML artifacts, and decides whether to accept or loop back to Dev with a fix list.",
      code: { path: "agent/personas/qa.py", lines: "12-58", language: "python",
        snippet:
`async def qa_persona(state: AgentState) -> dict:
    issues = await analyze(state["dev_output"])
    if issues:
        return {"qa_passed": False, "fix_list": issues}
    return {"qa_passed": True}` },
      citations: [{ book_id: "uipath-cli", chapter_id: "01-rpa", section_id: "analyzer",
        snippet: "Workflow Analyzer rules can be enforced via uipcli package analyze with a governance file." }],
    },

    // ============== EXTERNAL ==============
    {
      id: "ag:bedrock", label: "AWS Bedrock", kind: "tool", layer: "external",
      status: "ok",
      meta: { region: "us-east-1", model_id: "anthropic.claude-sonnet-4", auth: "iam" },
      desc: "Claude Sonnet via Bedrock. Shared LLM provider for all personas.",
      concept:
        "External LLM service. Each persona shares one Bedrock client instance, configured for streaming responses with token-level UI updates.",
      code: { path: "agent/llm.py", lines: "1-22", language: "python",
        snippet:
`bedrock = ChatBedrockConverse(
    model_id="anthropic.claude-sonnet-4",
    region_name="us-east-1",
    streaming=True,
)` },
    },
    {
      id: "up:salesforce", label: "Salesforce", kind: "tool", layer: "external",
      status: "ok",
      meta: { auth: "jwt-bearer" },
      desc: "System of record for accounts, opportunities, commitments.",
      concept:
        "External CRM. Read by GetCommitmentData, written to by SendDocuSign. Authentication is JWT-bearer flow with a connected app.",
      code: { path: "uipath/Shared/SalesforceClient.cs", lines: "1-30", language: "csharp",
        snippet:
`public class SalesforceClient {
  public Task<T[]> QueryAsync<T>(string soql) { ... }
  public Task UpdateAsync(string id, object fields) { ... }
}` },
    },

    // ============== RPA ==============
    {
      id: "up:Main", label: "Main.xaml", kind: "workflow", layer: "rpa",
      status: "ok",
      business_status: "live",
      roles: ["entrypoint"],
      pdd_anchor: { doc_id: "PDD-RENEWAL-01", section: "§3 Process Steps" },
      business_meta: {
        owner: "Sales Operations",
        volume: "120 / day",
        sla: "p95 8 min end-to-end",
        risk: "medium",
        consumers: ["Sales", "Finance"],
        value: "Removes 5.5 FTE of manual data entry; raises auto-approval rate from 20% to 62%.",
      },
      desc: "Entry workflow. Orchestrates the full renewal commitment process.",
      concept:
        "The top-level UiPath workflow. Sequences GetCommitmentData → RequestApproval (HITL) → SendDocuSign. Receives a JSON payload from the Dev persona's dispatch call.",
      code: { path: "uipath/RenewalCommitment/Main.xaml", lines: "—", language: "xml",
        snippet:
`<Sequence DisplayName="RenewalCommitment">
  <InvokeWorkflowFile WorkflowFileName="GetCommitmentData.xaml" />
  <InvokeWorkflowFile WorkflowFileName="RequestApproval.xaml" />
  <InvokeWorkflowFile WorkflowFileName="SendDocuSign.xaml" />
</Sequence>` },
      skills: [{ id: "uipath-rpa", path: ".cursor/skills/uipath-rpa/SKILL.md",
        reason: "Main.xaml is the modern-experience workflow entry — uipath-rpa governs structure and analyzer rules." }],
      citations: [
        { book_id: "uipath-docs", chapter_id: "studio", section_id: "invoke-workflow-file",
          snippet: "InvokeWorkflowFile sequences sub-workflows and propagates exceptions to the caller." },
      ],
      children: {
        nodes: [
          { id: "main:init", label: "Initialize Variables", kind: "activity", layer: "rpa", status: "ok",
            desc: "Set up workflow-scoped variables from input arguments.",
            code: { path: "Main.xaml", lines: "—",
              snippet: "<Assign To=\"oppId\" Value=\"[in_OpportunityId]\" />\n<Assign To=\"approver\" Value=\"[in_ApproverEmail]\" />" } },
          { id: "main:try", label: "Try Catch", kind: "activity", layer: "rpa", status: "ok",
            desc: "Wraps the main sequence in error handling.",
            code: { path: "Main.xaml", lines: "—",
              snippet: "<TryCatch>\n  <Try>...</Try>\n  <Catches>\n    <Catch ExceptionType=\"BusinessRuleException\">...</Catch>\n  </Catches>\n</TryCatch>" } },
          { id: "main:get", label: "GetCommitmentData", kind: "activity", layer: "rpa", status: "ok",
            desc: "Invokes the data retrieval sub-workflow.",
            code: { path: "Main.xaml", lines: "—",
              snippet: "<InvokeWorkflowFile WorkflowFileName=\"GetCommitmentData.xaml\" />" } },
          { id: "main:validate", label: "Validate Commitment", kind: "activity", layer: "rpa", status: "ok",
            desc: "Run business rules against the retrieved data.",
            code: { path: "Main.xaml", lines: "—",
              snippet: "<If Condition=\"[commitment.Discount > 0.20]\">\n  <Throw Exception=\"...DiscountExceedsThreshold\" />\n</If>" } },
          { id: "main:approve", label: "RequestApproval", kind: "activity", layer: "rpa", status: "ok",
            business_status: "live",
            roles: ["hitl", "approval"],
            pdd_anchor: { doc_id: "PDD-RENEWAL-01", section: "§3.4 Manager Approval" },
            business_meta: { owner: "Sales Operations", sla: "p95 4 min", risk: "high", value: "Catches discount overrides above policy threshold." },
            desc: "HITL pause point — wait for human approval.",
            code: { path: "Main.xaml", lines: "—",
              snippet: "<InvokeWorkflowFile WorkflowFileName=\"RequestApproval.xaml\" />" },
            children: {
              nodes: [
                { id: "appr:token",  label: "Create Approval Token", kind: "activity", layer: "rpa", status: "ok",
                  desc: "Generate a tokenized approval handle and persist it to Action Center.",
                  code: { path: "RequestApproval.xaml", lines: "—",
                    snippet: "<CreateActionCenterTask Title=\"Approve Commitment\" Token=\"[token]\" />" } },
                { id: "appr:notify", label: "Notify Approvers", kind: "activity", layer: "rpa", status: "ok",
                  roles: ["actor"],
                  desc: "Push Adaptive Card notifications to Slack and Outlook.",
                  code: { path: "RequestApproval.xaml", lines: "—",
                    snippet: "<SendSlackMessage Channel=\"approvals\" Card=\"[adaptiveCard]\" />\n<SendOutlookMail To=\"[approver]\" Card=\"[adaptiveCard]\" />" } },
                { id: "appr:wait",   label: "Wait for Decision", kind: "activity", layer: "rpa", status: "warn",
                  roles: ["hitl"],
                  desc: "Suspend the workflow until the approver hits the tokenized link.",
                  code: { path: "RequestApproval.xaml", lines: "—",
                    snippet: "<WaitForActionCompletion ActionToken=\"[token]\" />" } },
                { id: "appr:decide", label: "Branch on Decision", kind: "activity", layer: "rpa", status: "ok",
                  desc: "If approved, return the decision; if rejected, throw to the catch.",
                  code: { path: "RequestApproval.xaml", lines: "—",
                    snippet: "<If Condition=\"[decision = &quot;approved&quot;]\">\n  <OutArgument Value=\"[decision]\" />\n<Else>\n  <Throw Exception=\"new BusinessRuleException(&quot;rejected&quot;)\" />\n</Else>\n</If>" } },
                { id: "appr:audit",  label: "Audit Trail", kind: "activity", layer: "rpa", status: "ok",
                  desc: "Persist approver, timestamp, and decision to the audit log.",
                  code: { path: "RequestApproval.xaml", lines: "—",
                    snippet: "<LogMessage Level=\"Info\" Message=\"approver=[approver] decision=[decision]\" />" } },
              ],
              edges: [
                { id: "ape1", source: "appr:token",  target: "appr:notify", kind: "transition", path_class: "happy" },
                { id: "ape2", source: "appr:notify", target: "appr:wait",   kind: "transition", path_class: "happy" },
                { id: "ape3", source: "appr:wait",   target: "appr:decide", kind: "transition", path_class: "happy" },
                { id: "ape4", source: "appr:decide", target: "appr:audit",  kind: "transition", path_class: "happy", label: "approved" },
                { id: "ape5", source: "appr:decide", target: "appr:audit",  kind: "transition", path_class: "exception", label: "rejected",
                  desc: "Reject path: still write the audit, then re-raise the exception to caller." },
              ],
            },
          },
          { id: "main:docusign", label: "SendDocuSign", kind: "activity", layer: "rpa", status: "ok",
            desc: "Generate and dispatch the signed agreement.",
            code: { path: "Main.xaml", lines: "—",
              snippet: "<InvokeWorkflowFile WorkflowFileName=\"SendDocuSign.xaml\" />" } },
          { id: "main:log", label: "Log Outcome", kind: "activity", layer: "rpa", status: "ok",
            desc: "Write the run result to the audit trail.",
            code: { path: "Main.xaml", lines: "—",
              snippet: "<LogMessage Level=\"Info\" Message=\"Run completed\" />" } },
        ],
        edges: [
          { id: "me1", source: "main:init",     target: "main:try",      kind: "transition" },
          { id: "me2", source: "main:try",      target: "main:get",      kind: "transition" },
          { id: "me3", source: "main:get",      target: "main:validate", kind: "transition" },
          { id: "me4", source: "main:validate", target: "main:approve",  kind: "transition", label: "ok" },
          { id: "me5", source: "main:approve",  target: "main:docusign", kind: "transition", label: "approved",
            desc: "Resumes here when the human approver accepts the request." },
          { id: "me6", source: "main:docusign", target: "main:log",      kind: "transition" },
        ],
      },
    },
    {
      id: "up:GetData", label: "GetCommitmentData", kind: "activity", layer: "rpa",
      status: "ok",
      desc: "Pulls commitment record from Salesforce by opportunity ID.",
      concept:
        "Modern UiPath C# activity (Windows target). Authenticates to Salesforce, runs a SOQL query, and writes the result to a typed output argument.",
      code: { path: "uipath/RenewalCommitment/GetCommitmentData.xaml", lines: "—", language: "csharp",
        snippet:
`var soql = $"SELECT Id, Amount, AccountId FROM Opportunity WHERE Id = '{oppId}'";
var result = await sfClient.QueryAsync<Commitment>(soql);
return result.First();` },
    },
    {
      id: "up:Approve", label: "RequestApproval", kind: "activity", layer: "rpa",
      status: "ok",
      roles: ["hitl", "approval"],
      desc: "Calls HITL platform. Pauses workflow, waits for tokenized response.",
      concept:
        "The HITL pause point. Generates an approval token, sends Adaptive Cards to Slack and Outlook, and suspends the UiPath job until the tokenized link is hit. Resumes with the approver's decision in state.",
      code: { path: "uipath/RenewalCommitment/RequestApproval.xaml", lines: "—", language: "csharp",
        snippet:
`var token = await hitl.CreateApproval(commitment);
await hitl.NotifyApprovers(token, channels: ["slack", "email"]);
var decision = await hitl.AwaitDecision(token);  // suspends` },
      skills: [{ id: "uipath-human-in-the-loop", path: ".cursor/skills/uipath-human-in-the-loop/SKILL.md",
        reason: "Approval activity is the canonical HITL pause point." }],
      citations: [
        { book_id: "uipath-docs", chapter_id: "actions", section_id: "create-approval",
          snippet: "Action Center creates tokenized approvals, suspends the job, and resumes when the link is hit." },
      ],
    },
    {
      id: "up:DocuSign", label: "SendDocuSign", kind: "activity", layer: "rpa",
      status: "ok",
      desc: "Generates final agreement, dispatches to signer.",
      concept:
        "Terminal step. Renders the agreement PDF from a Word template, creates a DocuSign envelope, and emails the signer. Updates the Salesforce Opportunity with the envelope ID.",
      code: { path: "uipath/RenewalCommitment/SendDocuSign.xaml", lines: "—", language: "csharp",
        snippet:
`var envelope = await docusign.CreateEnvelope(pdf, signer);
await sfClient.UpdateAsync(oppId, new { DocuSignId = envelope.Id });` },
    },

    // ============== SKILLS CONTEXT ==============
    {
      id: "skill:uipath-agents",
      label: "uipath-agents",
      kind: "skill",
      layer: "skills",
      status: "ok",
      desc: "Coded agent lifecycle: LangGraph/LlamaIndex setup, run, evaluate, deploy, sync.",
      meta: {
        skill_id: "uipath-agents",
        coverage_count: 4,
        matched_node_ids: "ag:supervisor,ag:ba,ag:dev",
        origin: "project",
        path: ".cursor/skills/uipath-agents/SKILL.md",
        tags: "agent, langgraph, eval",
        triggers: "coded agent | LangGraph | evaluate agent",
      },
    },
    {
      id: "skill:uipath-rpa",
      label: "uipath-rpa",
      kind: "skill",
      layer: "skills",
      status: "ok",
      desc: "UiPath automations: coded workflows, XAML workflows, hybrid projects, build and debug loop.",
      meta: {
        skill_id: "uipath-rpa",
        coverage_count: 5,
        matched_node_ids: "up:Main,up:GetData,up:Approve",
        origin: "project",
        path: ".cursor/skills/uipath-rpa/SKILL.md",
        tags: "rpa, xaml, workflow",
        triggers: "XAML workflow | coded workflow | build RPA",
      },
    },
    {
      id: "skill:uipath-human-in-the-loop",
      label: "uipath-human-in-the-loop",
      kind: "skill",
      layer: "skills",
      status: "ok",
      desc: "Design approval gates, escalations, write-back validation, and Action Center context.",
      meta: {
        skill_id: "uipath-human-in-the-loop",
        coverage_count: 2,
        matched_node_ids: "up:Approve,fe:ApprovalWidget",
        origin: "project",
        path: ".cursor/skills/uipath-human-in-the-loop/SKILL.md",
        tags: "hitl, approval, action center",
        triggers: "approval gate | human review | escalation",
      },
    },
  ],
  edges: [
    { id: "e1",  source: "fe:App",            target: "fe:CheckoutForm",   kind: "import",     desc: "App composes the checkout route." },
    { id: "e2",  source: "fe:App",            target: "fe:ApprovalWidget", kind: "import",     desc: "App registers the approval widget for generative-UI rendering." },
    { id: "e3",  source: "fe:CheckoutForm",   target: "fe:api",            kind: "import" },
    { id: "e4",  source: "fe:ApprovalWidget", target: "fe:api",            kind: "import" },
    { id: "e5",  source: "fe:api",            target: "api:routes",        kind: "call",       label: "HTTP",     path_class: "happy",
      payload_schema: "CommitmentIn",
      desc: "POST /commitments with the validated payload." },
    { id: "e6",  source: "api:routes",        target: "api:auth",          kind: "call",       desc: "JWT verification + role guard." },
    { id: "e7",  source: "api:routes",        target: "ag:supervisor",     kind: "invokes",    path_class: "happy", desc: "Hands the request off to the LangGraph supervisor." },
    { id: "e8",  source: "ag:supervisor",     target: "ag:ba",             kind: "transition", path_class: "happy" },
    { id: "e9",  source: "ag:ba",             target: "ag:sa",             kind: "transition", path_class: "happy" },
    { id: "e10", source: "ag:sa",             target: "ag:dev",            kind: "transition", path_class: "happy" },
    { id: "e11", source: "ag:dev",            target: "ag:qa",             kind: "transition", path_class: "happy" },
    { id: "e12", source: "ag:qa",             target: "ag:supervisor",     kind: "transition", label: "loop",     path_class: "loopback",
      desc: "QA failures route back through the supervisor for re-dispatch." },
    { id: "e13", source: "ag:ba",             target: "ag:bedrock",        kind: "call" },
    { id: "e14", source: "ag:sa",             target: "ag:bedrock",        kind: "call" },
    { id: "e15", source: "ag:dev",            target: "ag:bedrock",        kind: "call" },
    { id: "e16", source: "ag:qa",             target: "ag:bedrock",        kind: "call" },
    { id: "e17", source: "ag:dev",            target: "up:Main",           kind: "bridge",     label: "dispatch", path_class: "happy",
      desc: "Dev persona writes XAML and dispatches the workflow to UiPath." },
    { id: "e18", source: "up:Main",           target: "up:GetData",        kind: "transition", path_class: "happy" },
    { id: "e19", source: "up:GetData",        target: "up:salesforce",     kind: "call",       payload_schema: "Commitment" },
    { id: "e20", source: "up:Main",           target: "up:Approve",        kind: "transition", path_class: "happy" },
    { id: "e21", source: "up:Approve",        target: "fe:ApprovalWidget", kind: "bridge",     label: "HITL",     path_class: "happy",
      desc: "Approval activity surfaces the inline ApprovalWidget for human decision." },
    { id: "e22", source: "up:Main",           target: "up:DocuSign",       kind: "transition", path_class: "happy" },
    { id: "c1",  source: "skill:uipath-agents", target: "ag:supervisor",   kind: "covers",     label: "top 1" },
    { id: "c2",  source: "skill:uipath-agents", target: "ag:ba",           kind: "covers",     label: "top 2" },
    { id: "c3",  source: "skill:uipath-agents", target: "ag:dev",          kind: "covers",     label: "top 3" },
    { id: "c4",  source: "skill:uipath-rpa",    target: "up:Main",         kind: "covers",     label: "top 1" },
    { id: "c5",  source: "skill:uipath-rpa",    target: "up:GetData",      kind: "covers",     label: "top 2" },
    { id: "c6",  source: "skill:uipath-rpa",    target: "up:Approve",      kind: "covers",     label: "top 3" },
    { id: "c7",  source: "skill:uipath-human-in-the-loop", target: "up:Approve",        kind: "covers", label: "top 1" },
    { id: "c8",  source: "skill:uipath-human-in-the-loop", target: "fe:ApprovalWidget", kind: "covers", label: "top 2" },
  ],
  errors: [
    { nodeId: "fe:Legacy", severity: "warn", message: "orphan: zero inbound edges — safe to delete" },
    { nodeId: "ag:qa",     severity: "info", message: "loops back via supervisor on validation failure" },
  ],
};
