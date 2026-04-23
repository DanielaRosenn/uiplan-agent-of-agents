"""Tests for documentation tools."""

import pytest
from pathlib import Path

from uipath_claude.tools.doc_tools import (
    read_template,
    write_doc,
    read_doc,
    list_docs,
    get_doc_tools,
)


class TestDocTools:
    """Tests for documentation tools."""

    def test_read_template_pdd(self, tmp_path, monkeypatch):
        """Should read PDD template."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "pdd.md").write_text("# Process Definition Document\n\n{{process_name}}")

        monkeypatch.setattr("uipath_claude.tools.doc_tools._get_templates_dir", lambda: templates_dir)

        content = read_template("pdd")
        assert "Process Definition Document" in content
        assert "{{process_name}}" in content

    def test_read_template_invalid(self, tmp_path, monkeypatch):
        """Should raise error for invalid template."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        monkeypatch.setattr("uipath_claude.tools.doc_tools._get_templates_dir", lambda: templates_dir)

        with pytest.raises(ValueError, match="Unknown template"):
            read_template("invalid")

    def test_write_and_read_doc(self, tmp_path):
        """Should write and read documentation."""
        doc_content = "# Test PDD\n\nThis is a test."

        result = write_doc(
            doc_type="pdd",
            content=doc_content,
            project_dir=str(tmp_path),
        )
        assert result["success"] is True
        assert "pdd.md" in result["path"]

        read_content = read_doc("pdd", project_dir=str(tmp_path))
        assert read_content == doc_content

    def test_list_docs(self, tmp_path):
        """Should list existing documentation."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "pdd.md").write_text("# PDD")
        (docs_dir / "sdd.md").write_text("# SDD")

        docs = list_docs(project_dir=str(tmp_path))
        assert "pdd" in docs
        assert "sdd" in docs
        assert docs["pdd"]["exists"] is True
        assert docs["sdd"]["exists"] is True

    def test_get_doc_tools_returns_tools(self):
        """Should return list of documentation tools."""
        tools = get_doc_tools()
        tool_names = [t.name for t in tools]
        assert "read_doc_template" in tool_names
        assert "write_documentation" in tool_names
        assert "read_documentation" in tool_names
        assert "list_documentation" in tool_names
