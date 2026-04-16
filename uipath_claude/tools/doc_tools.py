"""Tools for reading and writing documentation files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.tools import tool


def _get_templates_dir() -> Path:
    """Get the templates directory path."""
    pkg_dir = Path(__file__).parent.parent
    templates_dir = pkg_dir / "templates"
    if templates_dir.exists():
        return templates_dir
    return Path.cwd() / "templates"


def _get_docs_dir(project_dir: str | None = None) -> Path:
    """Get the docs directory for a project."""
    if project_dir:
        base = Path(project_dir)
    else:
        base = Path.cwd()
    docs_dir = base / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    return docs_dir


_TEMPLATE_NAMES = {
    "pdd": "pdd.md",
    "sdd": "sdd.md",
    "add": "add.md",
    "tdd": "tdd.md",
}


def read_template(doc_type: str) -> str:
    """
    Read a documentation template.

    Args:
        doc_type: Type of document (pdd, sdd, add, tdd)

    Returns:
        Template content as string

    Raises:
        ValueError: If template type is unknown
        FileNotFoundError: If template file not found
    """
    doc_type = doc_type.lower()
    if doc_type not in _TEMPLATE_NAMES:
        raise ValueError(f"Unknown template type: {doc_type}. Valid types: {list(_TEMPLATE_NAMES.keys())}")

    template_file = _get_templates_dir() / _TEMPLATE_NAMES[doc_type]
    if not template_file.exists():
        raise FileNotFoundError(f"Template not found: {template_file}")

    return template_file.read_text(encoding="utf-8")


def write_doc(
    doc_type: str,
    content: str,
    project_dir: str | None = None,
) -> dict[str, Any]:
    """
    Write documentation to a project.

    Args:
        doc_type: Type of document (pdd, sdd, add, tdd)
        content: Document content
        project_dir: Project directory (defaults to CWD)

    Returns:
        Dict with success status and path
    """
    doc_type = doc_type.lower()
    if doc_type not in _TEMPLATE_NAMES:
        return {
            "success": False,
            "error": f"Unknown document type: {doc_type}",
        }

    docs_dir = _get_docs_dir(project_dir)
    doc_path = docs_dir / _TEMPLATE_NAMES[doc_type]

    try:
        doc_path.write_text(content, encoding="utf-8")
        return {
            "success": True,
            "path": str(doc_path),
            "bytes_written": len(content.encode("utf-8")),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def read_doc(doc_type: str, project_dir: str | None = None) -> str:
    """
    Read documentation from a project.

    Args:
        doc_type: Type of document (pdd, sdd, add, tdd)
        project_dir: Project directory (defaults to CWD)

    Returns:
        Document content

    Raises:
        FileNotFoundError: If document doesn't exist
    """
    doc_type = doc_type.lower()
    if doc_type not in _TEMPLATE_NAMES:
        raise ValueError(f"Unknown document type: {doc_type}")

    docs_dir = _get_docs_dir(project_dir)
    doc_path = docs_dir / _TEMPLATE_NAMES[doc_type]

    if not doc_path.exists():
        raise FileNotFoundError(f"Document not found: {doc_path}")

    return doc_path.read_text(encoding="utf-8")


def list_docs(project_dir: str | None = None) -> dict[str, dict[str, Any]]:
    """
    List existing documentation in a project.

    Args:
        project_dir: Project directory (defaults to CWD)

    Returns:
        Dict mapping doc type to status info
    """
    if project_dir:
        base = Path(project_dir)
    else:
        base = Path.cwd()
    docs_dir = base / "docs"

    result = {}

    for doc_type, filename in _TEMPLATE_NAMES.items():
        doc_path = docs_dir / filename
        if doc_path.exists():
            stat = doc_path.stat()
            result[doc_type] = {
                "exists": True,
                "path": str(doc_path),
                "size": stat.st_size,
                "modified": stat.st_mtime,
            }
        else:
            result[doc_type] = {
                "exists": False,
                "path": str(doc_path),
            }

    return result


@tool
def read_doc_template(doc_type: str) -> str:
    """
    Read a documentation template (PDD, SDD, ADD, or TDD).

    Use this to get the structure and placeholders for a documentation type
    before filling it out with project-specific information.

    Args:
        doc_type: Type of document - one of: pdd, sdd, add, tdd

    Returns:
        Template content with placeholders
    """
    return read_template(doc_type)


@tool
def write_documentation(doc_type: str, content: str) -> dict[str, Any]:
    """
    Write completed documentation to the project's docs folder.

    Args:
        doc_type: Type of document - one of: pdd, sdd, add, tdd
        content: The completed documentation content (markdown)

    Returns:
        Dict with success status and file path
    """
    return write_doc(doc_type, content)


@tool
def read_documentation(doc_type: str) -> str:
    """
    Read existing documentation from the project.

    Args:
        doc_type: Type of document - one of: pdd, sdd, add, tdd

    Returns:
        Document content
    """
    return read_doc(doc_type)


@tool
def list_documentation() -> dict[str, dict[str, Any]]:
    """
    List all documentation files in the current project.

    Returns:
        Dict mapping doc type to existence and path info
    """
    return list_docs()


def get_doc_tools() -> list:
    """Get all documentation tools for agent use."""
    return [
        read_doc_template,
        write_documentation,
        read_documentation,
        list_documentation,
    ]
