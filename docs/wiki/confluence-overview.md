# UiPath Claude Code - Overview

An AI agent that builds, validates, and runs UiPath RPA workflows.

## What it is

UiPath Claude Code is a conversational agent for UiPath automation. You describe the automation in plain English; the agent scaffolds the project, writes the XAML, runs the UiPath validator, and fixes what it breaks - only stopping to ask when a human decision matters. It runs from a CLI, from inside Cursor, and as a full BA to SA to Dev to QA pipeline that turns a one-paragraph brief into a validated UiPath project.

## Who should care

- **RPA developers.** Skip the scaffolding and validator-chasing. The agent goes from a one-sentence description to a validated workflow that actually runs.
- **Delivery managers.** Faster turnarounds on new automations; fewer round-trips between analysts and developers; a consistent PDD -> SDD -> Code -> QA artifact trail for every project.
- **Solution architects.** A repeatable pipeline with explicit human-in-the-loop approval points at BA, SA, Dev, and QA. Plans are saved and auditable.
- **Platform / CoE leads.** Team-specific knowledge lives as versioned skills in the repo. The agent learns from team usage via a library learning loop.

## What problem it solves

RPA developers spend hours on the mechanical parts of automation: project scaffolding, XAML by hand, interpreting validator errors, re-running, fixing, re-validating. UiPath Claude Code does that loop for you. Human attention moves to the decisions that actually matter - requirements, design, edge cases, QA - instead of syntax and structure.

## How it fits with existing UiPath tooling

- Uses the official UiPath CLI (`uip`) for project operations and validation.
- Integrates with UiPath Studio Desktop 26.2+ for `--use-studio` validation.
- Talks to Orchestrator via its REST API for queues, assets, and processes.
- Uses the UiPath Integration Service for connectors (including publishing this page).
- Nothing proprietary on the UiPath side - standard artifacts, standard activities, standard deployment paths.

## Where to go next

- Repo: `<link to Azure DevOps repo>`
- Quickstart for developers: linked under this page.
- Architecture and how it works: `<link to repo docs/ARCHITECTURE.md>`
- Contact: RPA CoE.
