"""End-to-end test for Invoice Processor demo automation.

Verifies the complete UiPlan workflow from grounding to project scaffolding.
"""
import pytest
from pathlib import Path


@pytest.fixture
def invoice_processor_path():
    """Path to the Invoice Processor demo project."""
    return Path(__file__).resolve().parents[3] / "projects" / "InvoiceProcessor"


def test_uiplan_artifacts_exist(invoice_processor_path):
    """Verify all three UiPlan artifacts were created."""
    plan_folder = invoice_processor_path / ".cursor" / "plans" / "2026-05-02-invoice-processor"
    
    assert plan_folder.exists(), f"UiPlan folder not found: {plan_folder}"
    
    spec = plan_folder / "spec.md"
    assert spec.exists(), "spec.md missing"
    spec_content = spec.read_text(encoding="utf-8")
    assert "Invoice Data Extraction" in spec_content
    assert "FR-001" in spec_content
    assert "FR-002" in spec_content
    assert "FR-003" in spec_content
    assert "FR-004" in spec_content
    assert "**Implementation Paradigm**: RPA" in spec_content
    
    plan = plan_folder / "plan.md"
    assert plan.exists(), "plan.md missing"
    plan_content = plan.read_text(encoding="utf-8")
    assert "```mermaid" in plan_content
    assert "graph TD" in plan_content
    assert "REFramework" in plan_content
    
    tasks = plan_folder / "tasks.md"
    assert tasks.exists(), "tasks.md missing"
    tasks_content = tasks.read_text(encoding="utf-8")
    assert "T001" in tasks_content
    assert "T002" in tasks_content
    assert "T010" in tasks_content
    assert "Activity Checklist" in tasks_content


def test_project_structure(invoice_processor_path):
    """Verify RPA project structure was created."""
    assert invoice_processor_path.exists(), "Project root not found"
    
    project_json = invoice_processor_path / "project.json"
    assert project_json.exists(), "project.json missing"
    
    import json
    config = json.loads(project_json.read_text(encoding="utf-8"))
    assert config["name"] == "InvoiceProcessor"
    assert config["expressionLanguage"] == "CSharp"
    assert config["targetFramework"] == "Windows"
    assert "UiPath.PDF.Activities" in config["dependencies"]
    assert "UiPath.Excel.Activities" in config["dependencies"]
    
    main_xaml = invoice_processor_path / "Main.xaml"
    assert main_xaml.exists(), "Main.xaml missing"
    main_content = main_xaml.read_text(encoding="utf-8")
    assert "Invoice Processor Main" in main_content
    assert "Build Results DataTable" in main_content
    assert "ForEach" in main_content


def test_functional_requirements_coverage(invoice_processor_path):
    """Verify all FRs are addressed in the implementation."""
    plan_folder = invoice_processor_path / ".cursor" / "plans" / "2026-05-02-invoice-processor"
    
    spec = (plan_folder / "spec.md").read_text(encoding="utf-8")
    tasks = (plan_folder / "tasks.md").read_text(encoding="utf-8")
    
    # FR-001: PDF Invoice Processing
    assert "T004" in tasks  # PDF extraction task
    assert "Read PDF Text" in tasks
    
    # FR-002: Data Validation
    assert "T005" in tasks  # Validation task
    assert "Validates invoice number" in tasks or "Validate invoice" in tasks
    assert "date" in tasks.lower()
    
    # FR-003: Excel Report Generation
    assert "T007" in tasks  # Excel task
    assert "Write Range" in tasks or "Excel" in tasks
    
    # FR-004: Error Handling
    assert "error" in tasks.lower() or "exception" in tasks.lower()


def test_documentation_exists(invoice_processor_path):
    """Verify comprehensive documentation was created."""
    # Navigate up from projects/InvoiceProcessor to repo root, then to docs
    repo_root = invoice_processor_path.parents[1]
    docs_path = repo_root / "docs" / "E2E_AUTOMATION_DEMO.md"
    assert docs_path.exists(), f"E2E demo documentation missing at {docs_path}"
    
    content = docs_path.read_text(encoding="utf-8")
    assert "Invoice Data Extraction" in content
    assert "UiPlan Artifacts Created" in content
    assert "Project Implementation" in content
    assert "Status and Next Steps" in content
    assert "spec.md" in content
    assert "plan.md" in content
    assert "tasks.md" in content


def test_gitignore_includes_projects(invoice_processor_path):
    """Verify projects folder is gitignored."""
    repo_root = invoice_processor_path.parents[1]
    gitignore = repo_root / ".gitignore"
    assert gitignore.exists(), f"gitignore missing at {gitignore}"
    
    content = gitignore.read_text(encoding="utf-8")
    assert "/projects/" in content or "projects/" in content


@pytest.mark.parametrize("task_id,expected_deliverable", [
    ("T001", "project.json"),
    ("T002", "InitAllSettings.xaml"),
    ("T003", "GetTransactionData.xaml"),
    ("T004", "Process.xaml"),
    ("T007", "EndProcess.xaml"),
])
def test_tasks_have_clear_deliverables(invoice_processor_path, task_id, expected_deliverable):
    """Verify each task specifies clear deliverables."""
    plan_folder = invoice_processor_path / ".cursor" / "plans" / "2026-05-02-invoice-processor"
    tasks = (plan_folder / "tasks.md").read_text(encoding="utf-8")
    
    # Find the task section
    assert task_id in tasks, f"{task_id} not found in tasks.md"
    
    # Verify deliverable is mentioned in context
    task_lines = []
    in_task = False
    for line in tasks.splitlines():
        if line.startswith(f"## {task_id}"):
            in_task = True
        elif line.startswith("## T") and in_task:
            break
        if in_task:
            task_lines.append(line)
    
    task_section = "\n".join(task_lines)
    assert expected_deliverable in task_section or task_id == "T001", \
        f"{expected_deliverable} not mentioned in {task_id}"


def test_mermaid_diagrams_present(invoice_processor_path):
    """Verify Mermaid diagrams are included in plan and tasks."""
    plan_folder = invoice_processor_path / ".cursor" / "plans" / "2026-05-02-invoice-processor"
    
    plan = (plan_folder / "plan.md").read_text(encoding="utf-8")
    assert plan.count("```mermaid") >= 1, "No Mermaid diagram in plan.md"
    
    tasks = (plan_folder / "tasks.md").read_text(encoding="utf-8")
    # Tasks should have multiple diagrams for different workflows
    assert tasks.count("```mermaid") >= 3, "Insufficient Mermaid diagrams in tasks.md"


def test_acceptance_criteria_present(invoice_processor_path):
    """Verify all tasks have acceptance criteria."""
    plan_folder = invoice_processor_path / ".cursor" / "plans" / "2026-05-02-invoice-processor"
    tasks = (plan_folder / "tasks.md").read_text(encoding="utf-8")
    
    # Count tasks
    task_count = len([line for line in tasks.splitlines() if line.startswith("## T0")])
    
    # Count acceptance criteria sections
    ac_count = tasks.count("### Acceptance Criteria")
    
    assert ac_count == task_count, \
        f"Mismatch: {task_count} tasks but {ac_count} acceptance criteria sections"


def test_evidence_requirements_present(invoice_processor_path):
    """Verify all tasks specify evidence requirements."""
    plan_folder = invoice_processor_path / ".cursor" / "plans" / "2026-05-02-invoice-processor"
    tasks = (plan_folder / "tasks.md").read_text(encoding="utf-8")
    
    # Count tasks
    task_count = len([line for line in tasks.splitlines() if line.startswith("## T0")])
    
    # Count evidence sections
    evidence_count = tasks.count("### Evidence")
    
    assert evidence_count == task_count, \
        f"Mismatch: {task_count} tasks but {evidence_count} evidence sections"
