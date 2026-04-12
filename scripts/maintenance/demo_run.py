"""
Demonstration script to show the UiPath Builder Agent running end-to-end.
This bypasses the HITL interactive pause to demonstrate automated flow.
"""

import asyncio
import uuid
from langchain_core.messages import HumanMessage
from agent.graph import graph

async def demo_bootstrap_flow():
    """Run a complete bootstrap flow demonstration."""

    print("=" * 80)
    print("  UiPath Builder Agent - End-to-End Demonstration")
    print("=" * 80)

    # Test automation request - detailed to avoid clarification
    automation_request = """
    I need an automation that processes invoices from emails.

    Process Description:
    - Read unread emails from Outlook inbox with subject containing "Invoice"
    - Extract invoice number, total amount, and invoice date from email body
    - Save extracted data to Excel file (InvoiceLog.xlsx)
    - Mark email as read after processing
    - Log all operations using LogMessage

    Trigger: Scheduled daily at 9:00 AM
    Input: Outlook inbox emails
    Output: Excel file with invoice data (columns: InvoiceNumber, Amount, Date, ProcessedTimestamp)

    Business Rules:
    - Only process emails with "Invoice" in subject
    - Skip emails already marked as read
    - If extraction fails, log error and continue with next email

    Exceptions:
    - Handle case where Outlook is not running
    - Handle case where Excel file is locked
    - Handle malformed email content

    Frequency: Daily
    Expected Volume: 10-50 emails per day
    """

    print(f"\n[USER REQUEST]\n{automation_request.strip()}")
    print("\n" + "-" * 80)

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "messages": [HumanMessage(content=automation_request)],
        "mode": "bootstrap",
        "current_phase": "ba",
        "qa_iterations": 0,
    }

    try:
        print("\n[1/5] BA PERSONA: Analyzing requirements...")

        # Run until HITL interrupt
        result = await graph.ainvoke(initial_state, config)

        # Check if stopped at HITL
        snapshot = await graph.aget_state(config)

        print(f"\n[DEBUG] Current phase: {result.get('current_phase')}")
        print(f"[DEBUG] Snapshot.next: {snapshot.next}")
        print(f"[DEBUG] Has PDD: {'pdd' in result}")
        print(f"[DEBUG] Has SDD: {'sdd' in result}")
        print(f"[DEBUG] Requires HITL: {result.get('requires_hitl')}")
        print(f"[DEBUG] Needs clarification: {result.get('needs_clarification')}")
        print(f"[DEBUG] Messages count: {len(result.get('messages', []))}")

        # Show last message
        messages = result.get("messages", [])
        if messages:
            last_msg = messages[-1]
            content = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
            print(f"[DEBUG] Last message preview: {content[:200]}...")

        if snapshot.next and "hitl" in snapshot.next:
            print("\n[2/5] SA PERSONA: Generated Solution Design Document")

            sdd = result.get("sdd", {})
            print(f"\nProject: {sdd.get('project_name', 'N/A')}")
            print(f"Namespace: {sdd.get('namespace', 'N/A')}")
            print(f"Template: {sdd.get('template_type', 'N/A')}")
            print(f"Coded Activities: {len(sdd.get('coded_activities', []))}")

            print("\n[3/5] HITL NODE: Human approval (auto-approved for demo)")

            # Auto-approve for demo
            await graph.aupdate_state(
                config,
                {"messages": [HumanMessage(content="approved")]},
            )

            # Resume execution
            print("\n[4/5] DEVELOPER NODE: Generating code artifacts...")
            result = await graph.ainvoke(None, config)

        # Display final results
        print("\n[5/5] QA NODE: Validating against HARD_CONSTRAINTS...")

        validation_errors = result.get("validation_errors", [])
        qa_report = result.get("qa_report", {})

        if qa_report.get("passed") or len(validation_errors) == 0:
            print("\n[PASSED] QA VALIDATION: All checks passed")
        else:
            print(f"\n[FAILED] QA VALIDATION: {len(validation_errors)} errors found")
            for error in validation_errors:
                print(f"  - {error}")

        # Show generated artifacts
        artifacts = result.get("artifacts", {})
        print(f"\n[ARTIFACTS GENERATED]: {len(artifacts)} files")
        for filename in sorted(artifacts.keys()):
            lines = len(artifacts[filename].splitlines())
            print(f"  - {filename} ({lines} lines)")

        # Show sample from project.json
        if "project.json" in artifacts:
            print("\n[SAMPLE: project.json excerpt]")
            import json
            project_data = json.loads(artifacts["project.json"])
            print(f"  Project Name: {project_data.get('name', 'N/A')}")
            print(f"  Target Framework: {project_data.get('projectSettings', {}).get('targetFramework', 'N/A')}")
            print(f"  Expression Language: {project_data.get('expressionLanguage', 'N/A')}")

        # Show sample from Main.cs
        if "Main.cs" in artifacts:
            print("\n[SAMPLE: Main.cs excerpt]")
            main_lines = artifacts["Main.cs"].splitlines()[:15]
            for line in main_lines:
                print(f"  {line}")
            if len(artifacts["Main.cs"].splitlines()) > 15:
                print(f"  ... ({len(artifacts['Main.cs'].splitlines()) - 15} more lines)")

        print("\n" + "=" * 80)
        print("  DEMONSTRATION COMPLETE")
        print("=" * 80)
        print("\nTo run interactively:")
        print("  python -m cli.main start-project")
        print("\nOr with description:")
        print('  python -m cli.main start-project -d "Your automation description"')
        print("\n" + "=" * 80)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    asyncio.run(demo_bootstrap_flow())
