#!/usr/bin/env python3
"""Seed the documentation library with UiPath docs content.

This script populates the library by fetching content from the UiPath Ask AI API
and organizing it into the book/chapter/section structure.

Usage:
    python ops/scripts/seed_uipath_docs.py
"""
import argparse
import sys
from pathlib import Path

import yaml

# Add runtime root to path
_REPO = Path(__file__).resolve().parents[2]
_FW = _REPO / "framework"
sys.path.insert(0, str(_FW if (_FW / "uipath_claude").is_dir() else _REPO))

from uipath_claude.library.catalog import LibraryCatalog

SEED_STRUCTURE = {
    "01-activities": {
        "title": "Activities Reference",
        "sections": {
            "workflow": {
                "title": "Workflow Activities",
                "keywords": ["foreach", "if", "while", "switch", "sequence", "flowchart"],
                "topics": [
                    "ForEach activity usage and properties",
                    "If activity conditions and branches",
                    "While loop activity",
                    "Switch activity for multiple conditions",
                    "Sequence vs Flowchart",
                ],
            },
            "mail": {
                "title": "Mail Activities",
                "keywords": ["outlook", "email", "smtp", "imap", "exchange"],
                "topics": [
                    "Get Outlook Mail Messages activity",
                    "Send Outlook Mail Message activity",
                    "Save Mail Attachments activity",
                ],
            },
            "excel": {
                "title": "Excel Activities",
                "keywords": ["readrange", "writerange", "workbook", "spreadsheet"],
                "topics": [
                    "Read Range activity for Excel",
                    "Write Range activity for Excel",
                    "Excel Application Scope vs Workbook activities",
                ],
            },
            "ui-automation": {
                "title": "UI Automation Activities",
                "keywords": ["click", "typeinto", "gettext", "selector", "browser"],
                "topics": [
                    "Click activity and selectors",
                    "Type Into activity",
                    "Get Text activity",
                    "Use Application/Browser scope",
                ],
            },
        },
    },
    "02-orchestrator": {
        "title": "Orchestrator Guide",
        "sections": {
            "queues": {
                "title": "Queue Operations",
                "keywords": ["queue", "transaction", "getqueueitems", "addqueueitem"],
                "topics": [
                    "Get Queue Items activity",
                    "Add Queue Item activity",
                    "Set Transaction Status activity",
                    "Queue item retry logic",
                ],
            },
            "assets": {
                "title": "Asset Management",
                "keywords": ["asset", "credential", "getasset", "setasset"],
                "topics": [
                    "Get Asset activity",
                    "Get Credential activity",
                    "Asset types and per-robot assets",
                ],
            },
            "jobs": {
                "title": "Job Management",
                "keywords": ["job", "robot", "trigger", "schedule"],
                "topics": [
                    "Start Job activity",
                    "Get Jobs activity",
                    "Job triggers and schedules",
                ],
            },
        },
    },
    "03-studio": {
        "title": "Studio User Guide",
        "sections": {
            "reframework": {
                "title": "REFramework",
                "keywords": ["reframework", "transactional", "init", "process", "end"],
                "topics": [
                    "REFramework architecture overview",
                    "Init state and Config.xlsx",
                    "GetTransactionData state",
                    "Process Transaction state",
                    "BusinessRuleException vs SystemException",
                ],
            },
            "selectors": {
                "title": "Selectors",
                "keywords": ["selector", "uiexplorer", "wildcard", "dynamic"],
                "topics": [
                    "Selector strategies and best practices",
                    "Dynamic selectors with wildcards",
                    "UI Explorer usage",
                    "Anchor-based selectors",
                ],
            },
            "variables": {
                "title": "Variables and Arguments",
                "keywords": ["variable", "argument", "datatable", "scope"],
                "topics": [
                    "Variable types and scopes",
                    "Arguments for workflow inputs/outputs",
                    "DataTable operations",
                ],
            },
        },
    },
    "04-best-practices": {
        "title": "Best Practices",
        "sections": {
            "error-handling": {
                "title": "Error Handling",
                "keywords": ["trycatch", "exception", "retry", "logging"],
                "topics": [
                    "Try Catch patterns in UiPath",
                    "Global Exception Handler",
                    "Retry Scope usage",
                    "Logging best practices",
                ],
            },
            "naming-conventions": {
                "title": "Naming Conventions",
                "keywords": ["naming", "convention", "standard", "style"],
                "topics": [
                    "Variable naming conventions",
                    "Workflow naming conventions",
                    "Project structure best practices",
                ],
            },
        },
    },
}


def fetch_from_ask_ai(topics: list[str]) -> str:
    """Fetch content from Ask AI for given topics."""
    # For now, return placeholder content
    # In production, this would call the actual Ask AI API
    content_lines = []
    for topic in topics:
        content_lines.append(f"## {topic}\n")
        content_lines.append(f"[Content for: {topic}]\n")
        content_lines.append("")
    return "\n".join(content_lines)


def create_library_structure(target: Path | None = None) -> None:
    """Create the library directory structure and seed content."""
    library_path = target or LibraryCatalog.get_library_path()

    catalog_file = library_path / "catalog.yaml"
    if catalog_file.exists():
        print(f"Warning: Library already exists at {library_path}")
        print("Existing content will be overwritten.")
        print()

    print(f"Creating library at: {library_path}")

    # Create catalog.yaml
    catalog_data = {
        "version": 1,
        "books": [
            {
                "id": "uipath-docs",
                "title": "UiPath Documentation",
                "path": "books/uipath-docs",
                "description": "Official UiPath product documentation",
            }
        ],
    }
    library_path.mkdir(parents=True, exist_ok=True)
    catalog_file = library_path / "catalog.yaml"
    with open(catalog_file, "w", encoding="utf-8") as f:
        yaml.dump(catalog_data, f, default_flow_style=False)
    print(f"Created: {catalog_file}")

    # Create book structure
    book_path = library_path / "books" / "uipath-docs"
    book_path.mkdir(parents=True, exist_ok=True)

    # Create book.yaml
    book_data = {
        "id": "uipath-docs",
        "title": "UiPath Documentation",
        "version": "2024.10",
        "source": "docs.uipath.com",
        "chapters": [],
    }

    for chapter_folder, chapter_info in SEED_STRUCTURE.items():
        chapter_id = chapter_folder.split("-", 1)[1]
        book_data["chapters"].append({
            "id": chapter_id,
            "title": chapter_info["title"],
            "path": f"chapters/{chapter_folder}",
            "order": int(chapter_folder.split("-")[0]),
        })

        # Create chapter directory
        chapter_path = book_path / "chapters" / chapter_folder
        chapter_path.mkdir(parents=True, exist_ok=True)

        # Create chapter.yaml
        chapter_data = {
            "id": chapter_id,
            "title": chapter_info["title"],
            "sections": [],
        }

        for section_id, section_info in chapter_info["sections"].items():
            chapter_data["sections"].append({
                "id": section_id,
                "title": section_info["title"],
                "file": f"{section_id}.md",
                "keywords": section_info["keywords"],
            })

            # Create section content
            content = fetch_from_ask_ai(section_info["topics"])
            section_file = chapter_path / f"{section_id}.md"
            header = f"""---
id: {section_id}
title: {section_info["title"]}
---

# {section_info["title"]}

"""
            section_file.write_text(header + content, encoding="utf-8")
            print(f"Created: {section_file}")

        chapter_yaml = chapter_path / "chapter.yaml"
        with open(chapter_yaml, "w", encoding="utf-8") as f:
            yaml.dump(chapter_data, f, default_flow_style=False)
        print(f"Created: {chapter_yaml}")

    # Save book.yaml
    book_yaml = book_path / "book.yaml"
    with open(book_yaml, "w", encoding="utf-8") as f:
        yaml.dump(book_data, f, default_flow_style=False)
    print(f"Created: {book_yaml}")

    print("\nLibrary seeded successfully!")
    print(f"Total chapters: {len(SEED_STRUCTURE)}")
    total_sections = sum(len(ch["sections"]) for ch in SEED_STRUCTURE.values())
    print(f"Total sections: {total_sections}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        type=Path,
        default=None,
        help="Target library directory (overrides UIPATH_CLAUDE_LIBRARY and default)",
    )
    args = parser.parse_args()
    create_library_structure(target=args.target)
