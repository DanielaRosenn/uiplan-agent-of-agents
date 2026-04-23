#!/usr/bin/env python3
"""
Validate UiPath project structure and files.

This script performs comprehensive validation of UiPath projects:
1. Project structure validation (required files)
2. project.json schema validation
3. XAML file validation (well-formed XML, required elements)
4. Dependency verification
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


class ValidationResult:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.passed = True
        self.checks: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def add_check(self, name: str, passed: bool, details: str = ""):
        self.checks.append({"name": name, "passed": passed, "details": details})
        if not passed:
            self.passed = False
            self.errors.append(f"{name}: {details}")

    def add_warning(self, message: str):
        self.warnings.append(message)

    def print_report(self):
        print(f"\n{'='*60}")
        print(f"PROJECT VALIDATION: {self.project_path}")
        print(f"{'='*60}")
        
        for check in self.checks:
            status = "PASS" if check["passed"] else "FAIL"
            print(f"[{status}] {check['name']}")
            if check["details"] and not check["passed"]:
                print(f"       {check['details']}")
        
        if self.warnings:
            print(f"\nWarnings:")
            for w in self.warnings:
                print(f"  - {w}")
        
        print(f"\nResult: {'PASSED' if self.passed else 'FAILED'}")
        return self.passed


def validate_project_structure(project_path: Path, result: ValidationResult):
    """Validate required project files exist."""
    required_files = [
        ("project.json", "Project manifest"),
        ("Main.xaml", "Main workflow entry point"),
    ]
    
    optional_files = [
        ("project.uiproj", "Visual Studio project file"),
        ("entry-points.json", "Entry points configuration"),
    ]
    
    for filename, description in required_files:
        exists = (project_path / filename).exists()
        result.add_check(
            f"Required: {filename}",
            exists,
            f"{description} not found" if not exists else ""
        )
    
    for filename, description in optional_files:
        if not (project_path / filename).exists():
            result.add_warning(f"Optional file missing: {filename} ({description})")


def validate_project_json(project_path: Path, result: ValidationResult):
    """Validate project.json structure and content."""
    project_json_path = project_path / "project.json"
    
    if not project_json_path.exists():
        result.add_check("project.json readable", False, "File not found")
        return None
    
    try:
        content = project_json_path.read_text(encoding="utf-8")
        data = json.loads(content)
        result.add_check("project.json valid JSON", True)
    except json.JSONDecodeError as e:
        result.add_check("project.json valid JSON", False, str(e))
        return None
    except Exception as e:
        result.add_check("project.json readable", False, str(e))
        return None
    
    required_fields = ["name", "main", "dependencies"]
    for field in required_fields:
        has_field = field in data
        result.add_check(
            f"project.json has '{field}'",
            has_field,
            f"Missing required field" if not has_field else ""
        )
    
    if "main" in data:
        main_file = project_path / data["main"]
        main_exists = main_file.exists()
        result.add_check(
            f"Main entry point exists ({data['main']})",
            main_exists,
            f"File not found: {data['main']}" if not main_exists else ""
        )
    
    if "dependencies" in data:
        deps = data["dependencies"]
        result.add_check(
            "Has dependencies defined",
            len(deps) > 0,
            "No dependencies defined" if len(deps) == 0 else ""
        )
        
        core_packages = ["UiPath.System.Activities"]
        for pkg in core_packages:
            has_pkg = pkg in deps
            if not has_pkg:
                result.add_warning(f"Missing common package: {pkg}")
    
    if "expressionLanguage" in data:
        lang = data["expressionLanguage"]
        valid_langs = ["VisualBasic", "CSharp"]
        result.add_check(
            f"Expression language valid ({lang})",
            lang in valid_langs,
            f"Unknown language: {lang}" if lang not in valid_langs else ""
        )
    
    if "targetFramework" in data:
        framework = data["targetFramework"]
        valid_frameworks = ["Windows", "Portable", "Legacy"]
        result.add_check(
            f"Target framework valid ({framework})",
            framework in valid_frameworks,
            f"Unknown framework: {framework}" if framework not in valid_frameworks else ""
        )
    
    return data


def validate_xaml_file(xaml_path: Path, result: ValidationResult):
    """Validate a single XAML workflow file."""
    try:
        content = xaml_path.read_text(encoding="utf-8")
        
        tree = ET.parse(str(xaml_path))
        root = tree.getroot()
        result.add_check(f"XAML valid XML: {xaml_path.name}", True)
        
        has_activity = "Activity" in root.tag or root.tag.endswith("}Activity")
        result.add_check(
            f"XAML has Activity root: {xaml_path.name}",
            has_activity,
            "Root element is not Activity" if not has_activity else ""
        )
        
        has_class = False
        for key in root.attrib:
            if key.endswith("}Class") or key == "Class":
                has_class = True
                break
        
        if not has_class and 'x:Class=' in content:
            has_class = True
        
        result.add_check(
            f"XAML has x:Class: {xaml_path.name}",
            has_class,
            "Missing x:Class attribute" if not has_class else ""
        )
        
        return True
        
    except ET.ParseError as e:
        result.add_check(f"XAML valid XML: {xaml_path.name}", False, str(e))
        return False
    except Exception as e:
        result.add_check(f"XAML readable: {xaml_path.name}", False, str(e))
        return False


def validate_all_xaml_files(project_path: Path, result: ValidationResult):
    """Validate all XAML files in the project."""
    xaml_files = list(project_path.rglob("*.xaml"))
    
    excluded_dirs = {".local", ".objects", ".settings", ".storage"}
    xaml_files = [
        f for f in xaml_files 
        if not any(excluded in f.parts for excluded in excluded_dirs)
    ]
    
    result.add_check(
        f"XAML files found",
        len(xaml_files) > 0,
        "No XAML workflow files found" if len(xaml_files) == 0 else f"Found {len(xaml_files)} files"
    )
    
    valid_count = 0
    for xaml_file in xaml_files:
        if validate_xaml_file(xaml_file, result):
            valid_count += 1
    
    if xaml_files:
        all_valid = valid_count == len(xaml_files)
        result.add_check(
            f"All XAML files valid",
            all_valid,
            f"{valid_count}/{len(xaml_files)} valid" if not all_valid else ""
        )


def validate_project(project_path: str) -> ValidationResult:
    """Run full validation on a UiPath project."""
    path = Path(project_path).resolve()
    result = ValidationResult(str(path))
    
    if not path.exists():
        result.add_check("Project path exists", False, "Directory not found")
        return result
    
    result.add_check("Project path exists", True)
    
    validate_project_structure(path, result)
    validate_project_json(path, result)
    validate_all_xaml_files(path, result)
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Validate UiPath project")
    parser.add_argument("project_path", help="Path to UiPath project directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    result = validate_project(args.project_path)
    
    if args.json:
        output = {
            "project_path": result.project_path,
            "passed": result.passed,
            "checks": result.checks,
            "errors": result.errors,
            "warnings": result.warnings,
        }
        print(json.dumps(output, indent=2))
    else:
        result.print_report()
    
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
