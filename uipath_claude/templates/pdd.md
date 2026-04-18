# Process Definition Document (PDD)

**Process Name**: {{process_name}}  
**Version**: {{version}}  
**Date**: {{date}}  
**Author**: {{author}}  
**Status**: {{status}}

---

## I. Introduction

### Purpose
<!-- Describe the purpose of this document and the automation -->
{{purpose}}

### Objectives
<!-- List the business objectives expected after automation -->
- {{objective_1}}
- {{objective_2}}

### Key Contacts
| Role | Name | Contact Details | Notes |
| --- | --- | --- | --- |
{{key_contacts}}

### Minimum Pre-requisites
<!-- List access requirements, software, or data needed before automation can run -->
1. 
2. 

---

## II. AS IS Process Description

### Process Overview
| Item | Description |
| --- | --- |
| Process Area | {{department}} |
| Short Description | {{short_description}} |
| Role(s) Required | |
| Process Schedule | |
| Number of Executions | |
| Process Execution Time | |
| Peak Period(s) | |
| Input Data | |
| Output Data | |

### Applications Used
| Application | Version | Language | Type | Access Method |
| --- | --- | --- | --- | --- |
| | | | Web/Desktop/API | |

### High Level Process Map (AS IS)
<!-- List the manual steps performed currently -->
1. 
2. 
3. 

### Process Statistics (AS IS)
| Metric | Value |
| --- | --- |
{{process_statistics}}

### Current Pain Points
{{pain_points}}

---

## III. TO BE Process Description

### Detailed TO BE Process Map
<!-- Describe the automated workflow, distinguishing between AUTO and MANUAL steps -->
1. **[AUTO]** 
2. **[AUTO]** 
3. **[DECISION]** 
4. **[MANUAL]** (Human-in-the-Loop)
5. **[AUTO]** 

### In Scope for Automation
| Action | Description | Automation Level |
| --- | --- | --- |
{{in_scope_automation}}

### Out of Scope
{{out_of_scope}}

---

## IV. Exception Handling

### Known Business Exceptions
| Exception | Description/Parameters | Robot Action |
| --- | --- | --- |
{{business_exceptions}}

### Known Application Errors
| Error | Description/Parameters | Robot Action |
| --- | --- | --- |
{{application_errors}}

---

## V. Reporting Requirements

| Report Type | Frequency | Details | Tool |
| --- | --- | --- | --- |
{{reporting_requirements}}

---

## VI. Success Metrics

### Business Value Metrics
| Metric | Current (Manual) | Target (Automated) | Business Impact |
| --- | --- | --- | --- |
{{business_value_metrics}}

### ROI Summary
| Component | Metric | Value/Impact |
| --- | --- | --- |
{{roi_summary}}

### Run Cost Estimate
<!-- Estimates only. Source values from SDD section 4.6. -->
| Cost Type | Monthly $ | Source |
| --- | --- | --- |
| UiPath platform (robots, AI Units, Agent Units) | | SDD §4.6.1 |
| Infrastructure (EC2/VM, storage, egress) | | SDD §4.6.2 |
| LLM & vector store (if agentic) | | SDD §4.6.3 |
| Support / ops allocation | | |
| **Total monthly run cost** | | |

**Net monthly benefit**: (Business value from §VI) − (Total monthly run cost) = $ {{net_monthly_benefit}}
**Payback period**: (Implementation cost) ÷ (Net monthly benefit) = {{payback_months}} months

---

## VII. Additional Documentation
- **Workflow Diagrams**: 
- **Sample Inputs/Outputs**: 
- **LLM Prompts (if applicable)**: 
