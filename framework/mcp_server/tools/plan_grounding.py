"""Build a grounding pack for UiPlan (workspace-aware, no MCP round-trip)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from uipath_claude.cli.app import _select_relevant_skills
from uipath_claude.skills.registry import SkillRegistry
from uipath_claude.tools.library_tools import search_library as _search_library

from mcp_server.tools.plan_constitution import load_constitution


def _read_text(path: Path, limit: int | None = None) -> str | None:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    if limit is not None:
        lines = text.splitlines()
        text = "\n".join(lines[:limit])
    return text


def _pdd_candidates(repo: Path, limit: int = 12) -> list[dict[str, str]]:
    docs = repo / "docs"
    if not docs.is_dir():
        return []
    hits: list[dict[str, str]] = []
    patterns = ("PDD", "SDD", "ADD", "TDD")
    for md in sorted(docs.rglob("*.md")):
        name_upper = md.name.upper()
        for tag in patterns:
            if tag in name_upper:
                try:
                    rel = str(md.relative_to(repo))
                except ValueError:
                    rel = md.name
                hits.append({"path": rel, "kind": tag, "name": md.name})
                break
        if len(hits) >= limit:
            break
    return hits


def _library_hits(topic: str, max_queries: int = 3) -> list[dict[str, str]]:
    terms = [
        w.lower()
        for w in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", topic)
    ]
    seen: set[str] = set()
    queries: list[str] = []
    for t in terms:
        if t in seen:
            continue
        seen.add(t)
        queries.append(t)
        if len(queries) >= max_queries:
            break
    out: list[dict[str, str]] = []
    for q in queries[:max_queries]:
        try:
            raw = _search_library.invoke({"query": q, "top_n": 3})
            body = raw if isinstance(raw, str) else str(raw)
        except Exception as exc:  # noqa: BLE001
            out.append({"query": q, "error": str(exc)})
            continue
        out.append({"query": q, "excerpt": (body or "")[:1200]})
    return out


def _pick_project_template(topic: str) -> str:
    t = topic.lower()
    if any(k in t for k in ("queue", "long-running", "mailbox", "event", "trigger")):
        return "templates/long-running/"
    if any(k in t for k in ("dispatcher", "performer", "reframework")):
        return "templates/dispatcher/"
    if any(k in t for k in ("transaction", "item", "batch")):
        return "templates/performer/"
    return "templates/long-running/"


def build_grounding_pack(repo: Path, topic: str) -> dict[str, Any]:
    """Collect workspace signals for UiPlan generation and review."""
    ctx_path = repo / ".claude" / "rules" / "project-context.md"
    project_context = _read_text(ctx_path, limit=400)
    claude = _read_text(repo / "CLAUDE.md", limit=200)

    reg = SkillRegistry(project_root=repo)
    reg.load_skills()
    matched = _select_relevant_skills(topic, reg.skills, max_items=5)
    skills_out = [
        {
            "name": s.get("name"),
            "origin": s.get("origin"),
            "description": (s.get("description") or "")[:400],
        }
        for s in matched
    ]

    constitution = load_constitution(repo)
    unanswered: list[str] = []
    if not project_context:
        unanswered.append(
            "Missing .claude/rules/project-context.md — run discovery / "
            "uipath_plan_build before locking scope."
        )

    return {
        "status": "ok",
        "topic": topic,
        "project_context_path": str(ctx_path.relative_to(repo)) if ctx_path.is_file() else None,
        "project_context_excerpt": project_context,
        "claude_md_excerpt": claude,
        "matched_skills": skills_out,
        "library_hits": _library_hits(topic),
        "pdd_candidates": _pdd_candidates(repo),
        "candidate_project_template": _pick_project_template(topic),
        "constitution": constitution,
        "unanswered": unanswered,
        "suggested_citations": _build_citations(skills_out, repo),
    }


def _build_citations(skills: list[dict[str, Any]], repo: Path) -> list[str]:
    cites: list[str] = []
    for s in skills:
        name = s.get("name")
        if name:
            cites.append(f"[skill:{name}]")
    cites.append(f"[repo:{repo.name}/CLAUDE.md]")
    tpl = _pick_project_template(" ".join(str(s.get("name", "")) for s in skills))
    cites.append(f"[template:{tpl}]")
    return cites
