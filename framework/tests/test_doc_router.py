"""Tests for documentation router."""

import pytest
from unittest.mock import patch

from uipath_claude.query.doc_router import (
    route_to_doc_agent,
    DocRouteDecision,
)


class TestDocRouter:
    """Tests for documentation router."""

    @pytest.mark.asyncio
    async def test_routes_to_ba_for_pdd(self):
        """Should route to BA agent for PDD creation."""
        decision = await route_to_doc_agent(
            user_input="Create a PDD for invoice processing",
            recommended_docs=["pdd"],
        )
        assert decision.agent == "ba"
        assert decision.doc_type == "pdd"

    @pytest.mark.asyncio
    async def test_routes_to_sa_for_sdd(self):
        """Should route to SA agent for SDD creation."""
        decision = await route_to_doc_agent(
            user_input="Create an SDD for the integration layer",
            recommended_docs=["sdd"],
        )
        assert decision.agent == "sa"
        assert decision.doc_type == "sdd"

    @pytest.mark.asyncio
    async def test_routes_to_sa_for_add(self):
        """Should route to SA agent for ADD creation."""
        decision = await route_to_doc_agent(
            user_input="Create an Agent Design Document",
            recommended_docs=["add"],
        )
        assert decision.agent == "sa"
        assert decision.doc_type == "add"

    @pytest.mark.asyncio
    async def test_pdd_first_when_multiple_docs(self):
        """Should prioritize PDD when multiple docs needed."""
        decision = await route_to_doc_agent(
            user_input="I need full documentation for this enterprise project",
            recommended_docs=["pdd", "sdd", "tdd"],
        )
        assert decision.agent == "ba"
        assert decision.doc_type == "pdd"
        assert "sdd" in decision.next_docs
        assert "tdd" in decision.next_docs

    @pytest.mark.asyncio
    async def test_skips_pdd_if_exists(self, tmp_path):
        """Should skip PDD if it already exists."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "pdd.md").write_text("# Existing PDD")
        
        decision = await route_to_doc_agent(
            user_input="Create documentation",
            recommended_docs=["pdd", "sdd"],
            project_dir=str(tmp_path),
        )
        assert decision.agent == "sa"
        assert decision.doc_type == "sdd"

    @pytest.mark.asyncio
    async def test_returns_none_when_all_docs_exist(self, tmp_path):
        """Should return none when all recommended docs exist."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "pdd.md").write_text("# PDD")
        (docs_dir / "sdd.md").write_text("# SDD")
        
        decision = await route_to_doc_agent(
            user_input="Create documentation",
            recommended_docs=["pdd", "sdd"],
            project_dir=str(tmp_path),
        )
        assert decision.agent == "none"
        assert decision.doc_type is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_docs_recommended(self):
        """Should return none when no docs recommended."""
        decision = await route_to_doc_agent(
            user_input="Simple request",
            recommended_docs=[],
        )
        assert decision.agent == "none"
