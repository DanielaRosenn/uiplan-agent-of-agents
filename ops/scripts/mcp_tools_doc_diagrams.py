"""Per-tool Mermaid flowchart bodies for docs/MCP_TOOLS.md (no fences).

Each value is the inner flowchart (direction + nodes + edges + class lines
only). ``generate_mcp_tools_doc.py`` wraps with ``%%{init}%%``, shared
``classDef`` / ``linkStyle``, and closing fence.

Node ids are unique per diagram block; reuse simple ids inside each chart.
"""
from __future__ import annotations

_TOOL_DIAGRAMS: dict[str, str] = {
    # --- workflow (dispatch in mcp_server/tools/workflow_tools.py) ---
    "uipath_workflow_read_file": """flowchart LR
  FP[file_path]:::process --> RF[LangChain read_file]:::service
  RF --> TXT[File UTF-8 text]:::data""",
    "uipath_workflow_write_file": """flowchart TD
  IN[file_path + content]:::process --> DG{Design approved for project?}:::decision
  DG -->|No| BL1[/Return BLOCKED/]:::error
  DG -->|Yes| WR[LangChain write_file]:::mutate
  WR --> CHK{Write OK and gated ext?}:::decision
  CHK -->|Yes| DY[mark_dirty for project]:::stage
  CHK -->|No| RS[Return write result]:::data
  DY --> RS""",
    "uipath_workflow_list_directory": """flowchart LR
  DP[directory_path + pattern]:::process --> LS[LangChain list_directory]:::service
  LS --> LST[Listing text]:::data""",
    "uipath_workflow_read_project": """flowchart LR
  PD[project_dir]:::process --> RJ[read project.json]:::service
  RJ --> OUT[OK + JSON summary string]:::data""",
    "uipath_workflow_install_package": """flowchart TD
  IN[project_dir + package_id]:::process --> DG{Design gate}:::decision
  DG -->|Blocked| B1[/BLOCKED/]:::error
  DG -->|Open| SG{Session verified?}:::decision
  SG -->|Blocked| B2[/BLOCKED/]:::error
  SG -->|OK| INS[LangChain install_package]:::mutate
  INS --> CHK{Result starts OK?}:::decision
  CHK -->|Yes| MD[mark_dirty install marker]:::stage
  CHK -->|No| R[Return CLI result]:::data
  MD --> R""",
    "uipath_workflow_validate": """flowchart LR
  PF[project_dir + file_path]:::process --> VF[LangChain validate_file uip rpa get-errors]:::service
  VF --> REP[Validation report string]:::data""",
    "uipath_workflow_validate_loop": """flowchart LR
  PF[project_dir + file_path + max_attempts]:::process --> VL[LangChain validate_and_fix_loop]:::mutate
  VL --> LOG[Loop log string]:::data""",
    "uipath_workflow_build_and_verify": """flowchart TD
  PD[project_dir + options]:::process --> BV[LangChain build_and_verify_workflow]:::mutate
  BV --> PASS{verdict pass in output?}:::decision
  PASS -->|Yes| MV[session_gate mark_verified]:::endOk
  PASS -->|No| OUT[Return build output]:::data
  MV --> OUT""",
    "uipath_workflow_environment_probe": """flowchart LR
  PD[Optional project_dir]:::process --> EP[LangChain environment_probe]:::service
  EP --> JS[JSON probe result]:::data""",
    "uipath_workflow_create_project": """flowchart LR
  IN[project_dir + project_name + type]:::process --> CP[LangChain create_project uip rpa]:::mutate
  CP --> OUT[Scaffold result string]:::data""",
    "uipath_workflow_run": """flowchart TD
  IN[project_dir + file_path + inputs]:::process --> SG{Session gate}:::decision
  SG -->|Blocked| BL[/BLOCKED/]:::error
  SG -->|OK| RUN[LangChain run_workflow uip rpa run-file]:::mutate
  RUN --> OUT[Run output]:::data""",
    "uipath_workflow_debug": """flowchart TD
  IN[project_dir + file_path]:::process --> SG{Session gate}:::decision
  SG -->|Blocked| BL[/BLOCKED/]:::error
  SG -->|OK| DB[LangChain debug_workflow StartDebugging]:::mutate
  DB --> OUT[Debug session output]:::data""",
    "uipath_workflow_ensure_project": """flowchart TD
  IN[project_dir optional project_name]:::process --> MK[mkdir parents if name set]:::process
  MK --> EN[LangChain ensure_project_structure]:::service
  EN --> OUT[Structure message]:::data""",
    "uipath_workflow_run_command": """flowchart TD
  IN[command + args + optional project_dir]:::process --> SG{Session gate}:::decision
  SG -->|Blocked| BL[/BLOCKED/]:::error
  SG -->|OK| UIP[LangChain run_uip_command]:::mutate
  UIP --> OUT[uip stdout or error]:::data""",
    "uipath_workflow_deploy": """flowchart TD
  IN[project_path + orchestrator + tenant + options]:::process --> SG{Session gate}:::decision
  SG -->|Blocked| BL[/BLOCKED/]:::error
  SG -->|OK| DEP[deploy_to_orchestrator]:::mutate
  DEP --> JSON[JSON deploy result]:::data""",
    "uipath_workflow_publish": """flowchart TD
  IN[project_dir + project_type]:::process --> SG{Session gate}:::decision
  SG -->|Blocked| BL[/BLOCKED/]:::error
  SG -->|OK| PUB[publish_project pack to feed]:::mutate
  PUB --> JSON[JSON publish result]:::data""",
    "uipath_workflow_session_status": """flowchart TD
  PD{project_dir provided?}:::decision
  PD -->|Yes| ONE[detect OOB + status one project]:::service
  PD -->|No| ALL[Snapshot every tracked project]:::service
  ONE --> JS[JSON status]:::data
  ALL --> JS""",
    # --- skill ---
    "uipath_skill_list": """flowchart LR
  R[Optional agent_role filter]:::process --> REG[SkillRegistry filter]:::service
  REG --> LST[List of skill metadata dicts]:::data""",
    "uipath_skill_get": """flowchart TD
  N[skill_name]:::process --> G[Registry get_skill]:::service
  G --> F{Found?}:::decision
  F -->|No| MISS[String skill not found]:::error
  F -->|Yes| LD[load_skill_content markdown]:::service
  LD --> MD[Full SKILL body]:::data""",
    "uipath_skill_match": """flowchart LR
  UI[user_input + top_k]:::process --> H[CLI heuristic _select_relevant_skills]:::service
  H --> RK[Ranked skill list]:::data""",
    "uipath_skill_insights_query": """flowchart LR
  SN[skill_name]:::process --> ST[SkillInsightsTool query]:::service
  ST --> INS[Insights dict or summary]:::data""",
    "uipath_skill_insights_add": """flowchart LR
  IN[skill_name type content layer]:::process --> ST[SkillInsightsTool add]:::stage
  ST --> RES[Success or duplicate error dict]:::data""",
    "uipath_skill_manifest": """flowchart LR
  REG[Registry generate_manifest]:::service
  REG --> MAN[JSON manifest paths origins]:::data""",
    "uipath_skill_check_updates": """flowchart LR
  CH[check_for_updates git submodule]:::service
  CH --> D[has_updates message commits dict]:::data""",
    "uipath_skill_update": """flowchart LR
  F[force flag]:::process --> EF[ensure_fresh submodule reset]:::mutate
  EF --> INFO[get_skills_info commit count]:::data""",
    "uipath_skill_lessons_list": """flowchart LR
  SN[skill_name + limit]:::process --> LF[load_for_skill lessons]:::service
  LF --> D[lessons array dict]:::data""",
    "uipath_skill_lessons_approve": """flowchart LR
  IN[skill_name + content]:::process --> AP[SkillInsightsStore append FAILURE_PATTERN]:::mutate
  AP --> OK[ok content_hash dict]:::data""",
    # --- agent ---
    "uipath_agent_bootstrap": """flowchart LR
  UR[user_request + output_dir]:::process --> BS[run_bootstrap_flow async]:::mutate
  BS --> PV[paths + text previews dict]:::data""",
    "uipath_agent_plan": """flowchart LR
  UR[user_request + project_context]:::process --> PL[run_planner_agent Bedrock]:::mutate
  PL --> RES[success response iterations tool_calls]:::data""",
    "uipath_agent_execute": """flowchart TD
  TK[task + skill_name]:::process --> SK[Load skill markdown from registry]:::service
  SK --> EX[AgenticExecutor ReAct + skill tools]:::mutate
  EX --> RES[success files_written validation_status]:::data""",
    "uipath_agent_ba": """flowchart LR
  REQ[requirements]:::process --> LLM[BAAgent + invoke_agent_llm Bedrock]:::mutate
  LLM --> PDD[pdd text dict]:::data""",
    "uipath_agent_sa": """flowchart LR
  PDD[pdd text]:::process --> LLM[SAAgent + invoke_agent_llm Bedrock]:::mutate
  LLM --> SDD[sdd text dict]:::data""",
    # --- doc ---
    "uipath_doc_list_packages": """flowchart LR
  IDX[list_available_packages activity-docs dirs]:::service
  IDX --> PKG[Sorted package id list]:::data""",
    "uipath_doc_list_activities": """flowchart LR
  PID[package_id + optional version]:::process --> LA[list_activities]:::service
  LA --> NAMES[Activity name list]:::data""",
    "uipath_doc_get_activity": """flowchart LR
  IN[package_id activity_name version]:::process --> GD[get_activity_doc md]:::service
  GD --> MD[Markdown or not found string]:::data""",
    "uipath_doc_get_package_overview": """flowchart LR
  PID[package_id + version]:::process --> GO[get_package_overview]:::service
  GO --> MD[Overview md or empty]:::data""",
    "uipath_doc_search": """flowchart LR
  Q[query substring]:::process --> SA[search_activities all packages]:::service
  SA --> HITS[Match list]:::data""",
    "uipath_doc_find_activity": """flowchart LR
  Q[query + optional project_dir]:::process --> FA[find_activity_info bundled then local then uip CLI]:::service
  FA --> RES[Resolution payload]:::data""",
    "query_uipath_docs": """flowchart LR
  Q[question]:::process --> ASK[query_uipath_docs Ask AI SDK or HTTP]:::service
  ASK --> ANS[Answer text]:::data""",
    "uipath_doc_read_template": """flowchart LR
  DT[doc_type enum]:::process --> TM[read_template bundled md]:::service
  TM --> MD[Placeholder template string]:::data""",
    "uipath_doc_list_docs": """flowchart LR
  PD[optional project_dir]:::process --> LD[list_docs exists sizes mtimes]:::service
  LD --> MAP[Per doc_type dict]:::data""",
    "uipath_doc_read_doc": """flowchart LR
  DT[doc_type + project_dir]:::process --> RD[read_doc from docs folder]:::service
  RD --> MD[Markdown body]:::data""",
    "uipath_doc_write_doc": """flowchart LR
  IN[doc_type + content + project_dir]:::process --> WR[write_doc overwrite path]:::mutate
  WR --> D[success path bytes dict]:::data""",
    # --- memory ---
    "uipath_memory_load": """flowchart TD
  PP{project_path?}:::decision
  PP -->|No| G[Read global memory md only]:::service
  PP -->|Yes| B[Merge global + project memory md]:::service
  G --> T[Combined text]:::data
  B --> T""",
    "uipath_memory_save": """flowchart LR
  IN[content + optional project_path]:::process --> SV[save_memory overwrite layer file]:::mutate
  SV --> MSG[Memory saved]:::endOk""",
    "uipath_memory_append": """flowchart LR
  IN[content + optional project_path]:::process --> LD[load_memory existing]:::service
  LD --> MRG[Merge with blank separator]:::process
  MRG --> SV[save_memory]:::mutate
  SV --> MSG[Memory appended]:::endOk""",
    # --- library ---
    "uipath_library_list": """flowchart LR
  LB[list_library_books invoke]:::service
  LB --> CAT[Books metadata string or structure]:::data""",
    "uipath_library_toc": """flowchart LR
  B[book_id]:::process --> TOC[browse_book_toc invoke]:::service
  TOC --> TREE[Chapter section hierarchy]:::data""",
    "uipath_library_read_section": """flowchart LR
  T[book_id chapter_id section_id]:::process --> RS[read_section invoke]:::service
  RS --> MD[Markdown + citation line]:::data""",
    "uipath_library_search": """flowchart LR
  Q[query + optional top_n]:::process --> SR[search_library ranked]:::service
  SR --> HITS[Top matches with ids]:::data""",
    "uipath_library_lookup": """flowchart LR
  Q[question + allow_network]:::process --> LK[lookup_uipath_knowledge]:::service
  LK --> ANS[Answer with SOURCE routing]:::data""",
    "uipath_library_propose_section": """flowchart LR
  IN[book chapter section title content keywords]:::process --> PR[propose_library_update queue]:::stage
  PR --> ACK[Queued proposal message]:::data""",
    "uipath_library_propose_chapter": """flowchart LR
  IN[book chapter title order sections json]:::process --> PR[propose_library_chapter queue]:::stage
  PR --> ACK[Queued proposal message]:::data""",
    "uipath_library_list_proposals": """flowchart LR
  ST[ProposalStore list_pending]:::service
  ST --> TXT[Lines or no pending message]:::data""",
    "uipath_library_approve_proposal": """flowchart LR
  PID[proposal_id]:::process --> AP[apply_proposal writes data library]:::mutate
  AP --> MSG[Applied message]:::data""",
    "uipath_library_reject_proposal": """flowchart LR
  PID[proposal_id]:::process --> RJ[reject_proposal drop queue]:::mutate
  RJ --> MSG[Result message]:::data""",
    # --- design ---
    "uipath_design_propose": """flowchart LR
  IN[project_dir title summary body citations resolutions]:::process --> PR[design_store.propose]:::stage
  PR --> OUT[STAGED design_id JSON write locked]:::data""",
    "uipath_design_approve": """flowchart TD
  ID[design_id + note actor]:::process --> AP[design_store.approve]:::mutate
  AP --> OK{Found?}:::decision
  OK -->|No| ERR[ERR KeyError string]:::error
  OK -->|Yes| MSG[OK approved JSON]:::endOk""",
    "uipath_design_reject": """flowchart TD
  ID[design_id + note]:::process --> RJ[design_store.reject]:::mutate
  RJ --> OK{Found?}:::decision
  OK -->|No| ERR[ERR string]:::error
  OK -->|Yes| MSG[OK rejected JSON]:::endOk""",
    "uipath_design_list": """flowchart LR
  F[Optional project_dir status_filter]:::process --> LS[design_store.list_proposals]:::service
  LS --> JSON[JSON array or no match message]:::data""",
    "uipath_design_status": """flowchart LR
  PD[project_dir]:::process --> ST[has_approved latest pending resolutions snapshot]:::service
  ST --> JSON[JSON status blob]:::data""",
    # --- intent plan answer ---
    "uipath_intent_classify": """flowchart LR
  TX[text + optional project_root]:::process --> CL[classify intent + hints]:::service
  CL --> PAY[Structured routing payload dict]:::data""",
    "uipath_plan_build": """flowchart TD
  UR[user_request]:::process --> GD{Submodule guard}:::decision
  GD -->|Fail| BL[Blocked message dict]:::error
  GD -->|OK| DC[Discovery agent project context md]:::human
  DC --> PL[run_planner_agent_with_discovery]:::service
  PL --> OUT[Planner result dict]:::data""",
    "uipath_plan_save": """flowchart TD
  C[content plus optional filename]:::process --> V[Validate front matter and mermaid]:::decision
  V -->|Fail| E[ValueError]:::error
  V -->|OK| W[Write docs/plans file]:::mutate
  W --> I[Regenerate plan index script]:::service
  I --> R[ok path relative index_regen]:::data""",
    "uipath_plan_list": """flowchart LR
  R[project_root optional]:::process --> D[Scan docs/plans md]:::service
  D --> P[Parse front matter per file]:::process
  P --> J[JSON plans array]:::data""",
    "uipath_plan_read": """flowchart LR
  F[filename or slug]:::process --> L[Resolve path under docs/plans]:::service
  L --> T[Read full markdown]:::data""",
    "uipath_plan_status_set": """flowchart TD
  NS[new_status]:::process --> P[Load plan by filename or slug]:::service
  P --> D{new_status is done?}:::decision
  D -->|Yes| G{design_store.has_approved}:::decision
  G -->|No| B[blocked design_not_approved]:::error
  G -->|Yes| U[Rewrite front matter status]:::mutate
  D -->|No| U
  U --> IDX[Regenerate index]:::service""",
    "uipath_plan_render_mermaid": """flowchart LR
  F[filename or slug]:::process --> RD[Read plan body]:::service
  RD --> EX[Regex extract mermaid fences]:::process
  EX --> BL[blocks plus count JSON]:::data""",
    "uipath_plan_ground": """flowchart LR
  T[topic]:::process --> PC[read project-context excerpt]:::service
  T --> SK[uipath_skill_match ranked skills]:::service
  T --> LB[uipath_library_search snippets]:::service
  T --> PD[scan docs for PDD SDD ADD]:::service
  PC --> PACK[grounding pack JSON]:::data
  SK --> PACK
  LB --> PACK
  PD --> PACK""",
    "uipath_plan_spec_new": """flowchart TD
  IN[title intent optional grounding_pack]:::process --> G[build_grounding_pack if needed]:::service
  G --> MK[mkdir date-slug folder]:::mutate
  MK --> META[write .meta.yaml plan_kind uiplan]:::mutate
  META --> SP[write spec.md from template]:::mutate
  SP --> OUT[ok path slug]:::data""",
    "uipath_plan_plan_new": """flowchart LR
  SL[slug]:::process --> RES[resolve UiPlan folder]:::service
  RES --> PL[fill plan.md template]:::mutate
  PL --> CON[constitution checklist from gates]:::process
  CON --> OUT[ok path]:::data""",
    "uipath_plan_tasks_new": """flowchart LR
  SL[slug]:::process --> RD[read spec.md plan.md]:::service
  RD --> TK[write tasks.md phases USn]:::mutate
  TK --> OUT[ok path]:::data""",
    "uipath_plan_review": """flowchart TD
  SL[slug stage]:::process --> LD[load spec plan tasks]:::service
  LD --> R1{spec rules}:::decision
  LD --> R2{plan rules}:::decision
  LD --> R3{tasks rules}:::decision
  LD --> R4{cross doc citations}:::decision
  R1 --> SUM[findings plus ok flag]:::data
  R2 --> SUM
  R3 --> SUM
  R4 --> SUM""",
    "uipath_plan_uiplan_new": """flowchart LR
  TI[title intent]:::process --> GR[uipath_plan_ground]:::service
  GR --> SP[uipath_plan_spec_new]:::mutate
  SP --> PL[uipath_plan_plan_new]:::mutate
  PL --> TS[uipath_plan_tasks_new]:::mutate
  TS --> RV[uipath_plan_review all]:::service
  RV --> OUT[bundle paths plus review]:::data""",
    "uipath_answer": """flowchart LR
  Q[question + optional persona]:::process --> RT[persona_router answer_question]:::service
  RT --> ANS[Markdown answer read-only tool belt]:::data""",
}


def diagram_body_for_tool(tool_name: str) -> str:
    """Return inner mermaid source for ``tool_name``, or a sensible default."""
    if tool_name in _TOOL_DIAGRAMS:
        return _TOOL_DIAGRAMS[tool_name]
    return f"""flowchart LR
  ARGS[MCP arguments]:::process --> T["{_safe(tool_name)}"]:::service
  T --> RES[Tool-specific result]:::data"""


def _safe(s: str) -> str:
    return s.replace('"', "'")


def extra_classdefs_block() -> str:
    """Gateway / terminal styles (always emitted after base palette)."""
    return "\n".join(
        [
            "  classDef decision fill:#FFFBEB,stroke:#F59E0B,color:#92400E,stroke-width:1.5px",
            "  classDef error fill:#FEF2F2,stroke:#EF4444,color:#991B1B,stroke-width:1.5px",
            "  classDef endOk fill:#ECFDF5,stroke:#10B981,color:#065F46,stroke-width:1.25px",
            "  classDef human fill:#F5F3FF,stroke:#8B5CF6,color:#5B21B6,stroke-width:1.25px",
        ]
    )
