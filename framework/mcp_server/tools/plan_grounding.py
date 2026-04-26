"""Build a grounding pack for UiPlan (workspace-aware, no MCP round-trip)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from uipath_claude.cli.app import _select_relevant_skills
from uipath_claude.skills.loader import load_skill_content
from uipath_claude.skills.registry import SkillRegistry
from uipath_claude.tools.knowledge_tools import lookup_uipath_knowledge as _lookup_knowledge
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


def _read_text_safe(path: Path, limit: int | None = None) -> tuple[str | None, str | None]:
    try:
        return _read_text(path, limit=limit), None
    except UnicodeDecodeError:
        try:
            text = path.read_text(encoding="utf-8-sig")
            if limit is not None:
                text = "\n".join(text.splitlines()[:limit])
            return text, None
        except Exception as exc:  # noqa: BLE001
            return None, str(exc)
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def _clip(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 14].rstrip() + " ... (truncated)"


def _topic_terms(topic: str, max_terms: int = 5) -> list[str]:
    terms = [
        w.lower()
        for w in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", topic)
    ]
    seen: set[str] = set()
    out: list[str] = []
    for term in terms:
        if term in seen:
            continue
        seen.add(term)
        out.append(term)
        if len(out) >= max_terms:
            break
    return out


def _strip_frontmatter(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].lstrip("\ufeff").strip() != "---":
        return text
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[index + 1 :]).strip()
    return text


def _skill_excerpt(skill: dict[str, Any], *, limit: int = 1800) -> str | None:
    path = str(skill.get("path") or "")
    if not path:
        return None
    content = _strip_frontmatter(load_skill_content(path))
    if not content.strip():
        return None
    return _clip(content, limit)


def _skill_record(skill: dict[str, Any], *, include_excerpt: bool = True) -> dict[str, Any]:
    record: dict[str, Any] = {
        "name": skill.get("name"),
        "origin": skill.get("origin"),
        "description": (skill.get("description") or "")[:400],
    }
    if include_excerpt:
        excerpt = _skill_excerpt(skill)
        if excerpt:
            record["excerpt"] = excerpt
    return record


def _agent_record(repo: Path, rel_path: str, *, limit: int = 1800) -> dict[str, Any] | None:
    path = repo / rel_path
    text = _read_text(path, limit=80)
    if not text:
        return None
    return {
        "name": path.stem,
        "path": rel_path,
        "description": (
            "Project discovery persona that identifies project type, entry points, "
            "dependencies, and build gates."
        ),
        "excerpt": _clip(_strip_frontmatter(text), limit),
    }


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


def _referenced_markdown_paths(repo: Path, topic: str, limit: int = 5) -> list[Path]:
    """Extract user-provided markdown paths from a UiPlan topic string."""
    candidates: list[Path] = []
    patterns = [
        r"[A-Za-z]:\\[^\n\r\"'<>|]+?\.md",
        r"(?:\.{1,2}[\\/])?[A-Za-z0-9_. \-\\/]+?\.md",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, topic):
            raw = match.group(0).strip().rstrip(".,;)")
            if not raw:
                continue
            path = Path(raw).expanduser()
            if not path.is_absolute():
                path = repo / path
            try:
                resolved = path.resolve()
            except OSError:
                resolved = path
            if resolved not in candidates:
                candidates.append(resolved)
            if len(candidates) >= limit:
                return candidates
    return candidates


def _source_documents(repo: Path, topic: str) -> list[dict[str, str]]:
    docs: list[dict[str, str]] = []
    for path in _referenced_markdown_paths(repo, topic):
        text, error = _read_text_safe(path, limit=220)
        kind = "PDD" if "pdd" in path.name.lower() else "markdown"
        try:
            display = str(path.relative_to(repo))
        except ValueError:
            display = str(path)
        item = {"path": display, "name": path.name, "kind": kind}
        if text:
            item["excerpt"] = _clip(_strip_frontmatter(text), 5000)
        if error:
            item["error"] = error
        docs.append(item)
    return docs


def _library_hits(topic: str, max_queries: int = 3) -> list[dict[str, str]]:
    queries = _topic_terms(topic, max_terms=max_queries)
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


def _source_line(body: str) -> str | None:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("SOURCE:"):
            return stripped
    return None


def _knowledge_lookups(topic: str, max_queries: int = 2) -> list[dict[str, str]]:
    terms = _topic_terms(topic, max_terms=3)
    queries = [topic.strip()]
    if terms:
        queries.append("UiPath implementation guidance for " + " ".join(terms))

    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for query in queries:
        query = query.strip()
        if not query or query.lower() in seen:
            continue
        seen.add(query.lower())
        try:
            raw = _lookup_knowledge.invoke({"question": query, "allow_network": False})
            body = raw if isinstance(raw, str) else str(raw)
        except Exception as exc:  # noqa: BLE001
            out.append({"query": query, "error": str(exc)})
            continue
        item = {"query": query, "excerpt": _clip(body, 1400)}
        source = _source_line(body)
        if source:
            item["source"] = source
        out.append(item)
        if len(out) >= max_queries:
            break
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
    skills_out = [_skill_record(s) for s in matched]
    planner = reg.get_skill("uipath-planner")
    planner_context = _skill_record(planner) if planner else None
    discovery_agent = _agent_record(
        repo,
        "skills/agents/uipath-project-discovery-agent.md",
    )

    constitution = load_constitution(repo)
    unanswered: list[str] = []
    if not project_context:
        unanswered.append(
            "Missing .claude/rules/project-context.md — run the "
            "uipath-project-discovery-agent before locking scope or build tasks."
        )

    source_docs = _source_documents(repo, topic)
    citations = _build_citations(skills_out, repo, source_docs)
    if planner_context and planner_context.get("name"):
        citations.insert(0, f"[skill:{planner_context['name']}]")
    if discovery_agent:
        citations.insert(1, f"[agent:{discovery_agent['name']}]")
    return {
        "status": "ok",
        "topic": topic,
        "source_documents": source_docs,
        "project_context_path": str(ctx_path.relative_to(repo)) if ctx_path.is_file() else None,
        "project_context_excerpt": project_context,
        "claude_md_excerpt": claude,
        "planning_skill": planner_context,
        "project_discovery_agent": discovery_agent,
        "planner_route": [
            "uipath-planner",
            "uipath-project-discovery-agent",
            "matched specialist skills",
            "UiPath library / AskAI-style lookup",
            "implementation skill or subagent execution",
        ],
        "matched_skills": skills_out,
        "library_hits": _library_hits(topic),
        "knowledge_lookups": _knowledge_lookups(topic),
        "pdd_candidates": _pdd_candidates(repo),
        "candidate_project_template": _pick_project_template(topic),
        "constitution": constitution,
        "unanswered": unanswered,
        "suggested_citations": citations,
    }


def _build_citations(
    skills: list[dict[str, Any]], repo: Path, source_docs: list[dict[str, str]] | None = None
) -> list[str]:
    cites: list[str] = []
    for s in skills:
        name = s.get("name")
        if name:
            cites.append(f"[skill:{name}]")
    for doc in source_docs or []:
        name = doc.get("name")
        if name:
            cites.append(f"[source:{name}]")
    cites.append(f"[repo:{repo.name}/CLAUDE.md]")
    tpl = _pick_project_template(" ".join(str(s.get("name", "")) for s in skills))
    cites.append(f"[template:{tpl}]")
    return cites
