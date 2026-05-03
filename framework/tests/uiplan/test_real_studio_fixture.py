"""Regression tests for the UiPlan runtime reliability fixture."""

from __future__ import annotations

import csv
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = REPO_ROOT / "framework" / "tests" / "fixtures" / "uiplan_runtime_reliability"
PROJECT_ROOT = FIXTURE_ROOT / "InvoiceProcessor"
OUT_DIR = FIXTURE_ROOT / "out"


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_failed_invoice_processor_demo_was_removed():
    assert not (REPO_ROOT / "projects" / "InvoiceProcessor").exists()


def test_fixture_was_scaffolded_from_template():
    scaffold = _read_json(FIXTURE_ROOT / "evidence" / "scaffold.json")
    project = _read_json(PROJECT_ROOT / "project.json")

    assert "uip rpa create-project" in scaffold["command"]
    assert scaffold["template_id"] == "BlankTemplate"
    assert project["name"] == "InvoiceProcessor"
    assert project["expressionLanguage"] == "CSharp"
    assert project["targetFramework"] == "Windows"
    assert project["dependencies"]["UiPath.System.Activities"] == "[26.2.4]"


def test_fixture_uses_prebuilt_activities_without_invoke_code():
    xaml = (PROJECT_ROOT / "Main.xaml").read_text(encoding="utf-8")

    assert "UiPath.Studio.Plugin.Workflow.Presentation.UnresolvedActivity" not in xaml
    assert "<ui:InvokeCode" not in xaml
    assert "<ui:ReadTextFile" in xaml
    assert "<ui:WriteTextFile" in xaml
    assert "<ui:CreateDirectory" in xaml
    assert "<ui:ForEach" in xaml
    assert xaml.count("<Assign ") >= 8
    assert "CSharpValue" in xaml
    assert "VisualBasicValue" not in xaml


def test_activity_grounding_evidence_exists():
    expected = [
        "default-create-directory.json",
        "default-read-text-file.json",
        "default-write-text-file.json",
    ]

    for name in expected:
        evidence = _read_json(FIXTURE_ROOT / "evidence" / name)
        assert evidence["result"] == "Success"
        assert evidence["package"] == "UiPath.System.Activities"
        assert evidence["version"] == "26.2.4"


def test_local_validation_evidence_exists():
    get_errors = _read_json(OUT_DIR / "get-errors.json")
    build = _read_json(OUT_DIR / "build.json")
    local_run = _read_json(OUT_DIR / "local-run.json")

    assert get_errors["data"]["message"] == "No diagnostics found."
    assert build["data"]["Success"] is True
    assert local_run["result"] == "Success"
    assert local_run["errors"] == []
    assert "Invoice Processor fixture started" in local_run["log_markers"]
    assert "Invoice Processor fixture completed" in local_run["log_markers"]


def test_analyzer_has_only_known_tenant_governance_blocker():
    analyze = _read_json(OUT_DIR / "analyze.json")
    error_codes = {
        item["ErrorCode"]
        for item in analyze
        if item.get("ErrorSeverity") == 1
    }

    assert error_codes == {"ST-USG-034"}
    blocker = _read_json(OUT_DIR / "tenant-blocker.json")
    assert blocker["blocker_class"] == "missing_tenant_auth_or_folder_permission"
    assert "analyze" in blocker["safe_local_evidence"]


def test_local_run_outputs_expected_invoice_results():
    report_path = PROJECT_ROOT / "Data" / "Output" / "invoice-report.csv"
    smoke_path = PROJECT_ROOT / "Data" / "Output" / "smoke-result.json"

    assert report_path.exists()
    assert smoke_path.exists()

    rows = list(csv.DictReader(report_path.open(encoding="utf-8")))
    by_file = {row["FileName"]: row for row in rows}

    assert by_file["valid-invoice.txt"]["InvoiceNumber"] == "INV-1001"
    assert by_file["valid-invoice.txt"]["Status"] == "Valid"
    assert by_file["invalid-invoice.txt"]["Status"] == "Invalid"
    assert "missing invoice number" in by_file["invalid-invoice.txt"]["ValidationErrors"]
    assert "invalid invoice date" in by_file["invalid-invoice.txt"]["ValidationErrors"]
    assert "invalid total amount" in by_file["invalid-invoice.txt"]["ValidationErrors"]

    smoke = _read_json(smoke_path)
    assert smoke == {"processed": 2, "report": "invoice-report.csv"}
