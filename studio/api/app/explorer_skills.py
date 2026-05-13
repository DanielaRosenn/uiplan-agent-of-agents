"""Skill aggregation for the UiPlan Studio Explorer.

The per-node Knowledge tab answers "what helps with this node?". This module
answers the project-level version: "which skills explain this project, and
which nodes do they cover?".
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TOP_COVERAGE_PER_SKILL = 3


@dataclass(frozen=True)
class SkillMatch:
    id: str
    path: str
    reason: str
    origin: str | None
    score: int
    tags: tuple[str, ...] = ()
    triggers: tuple[str, ...] = ()


def ensure_framework_on_path(repo_root: Path) -> None:
    framework_dir = repo_root / "framework"
    if str(framework_dir) not in sys.path:
        sys.path.insert(0, str(framework_dir))


def load_registered_skills(repo_root: Path) -> list[dict[str, Any]]:
    """Load skills through the same registry used by chat and MCP surfaces."""
    ensure_framework_on_path(repo_root)
    try:
        from uipath_claude.skills.registry import SkillRegistry
    except Exception:
        return []

    try:
        registry = SkillRegistry(project_root=repo_root)
        return registry.load_skills()
    except Exception:
        return []


def read_skill_detail(repo_root: Path, skill_id: str) -> dict[str, Any] | None:
    """Return full skill metadata + markdown body for a skill id."""
    for skill in load_registered_skills(repo_root):
        if str(skill.get("name", "")) != skill_id:
            continue
        path = Path(str(skill.get("path", "")))
        body = ""
        if path.is_file():
            try:
                body = _strip_frontmatter(path.read_text(encoding="utf-8"))
            except OSError:
                body = ""
        
        # Extract enhanced metadata for visualization
        metadata = _extract_visualization_metadata(body)
        
        return {
            "id": str(skill.get("name", "")),
            "description": str(skill.get("description", "")),
            "path": str(skill.get("path", "")),
            "origin": str(skill.get("origin", "")) or None,
            "tags": _string_list(skill.get("tags")),
            "triggers": _string_list(skill.get("triggers")),
            "body": body,
            "metadata": metadata,
        }
    return None


def _extract_visualization_metadata(body: str) -> dict[str, list[str]]:
    """Extract capabilities, guardrails, outputs, and backing services from skill body."""
    metadata: dict[str, list[str]] = {
        "capabilities": [],
        "guardrails": [],
        "outputs": [],
        "backing_services": [],
    }
    
    # Look for common patterns in skill markdown
    # Capabilities: bullet lists under "Capabilities", "Features", "What it does"
    caps_match = re.search(
        r"(?:^|\n)##?\s*(?:Capabilities|Features|What it does)[^\n]*\n((?:[-*]\s+.+\n)+)",
        body,
        re.IGNORECASE | re.MULTILINE,
    )
    if caps_match:
        for line in caps_match.group(1).strip().split("\n"):
            line = line.strip().lstrip("-*").strip()
            if line:
                metadata["capabilities"].append(line[:80])
    
    # Guardrails: bullet lists under "Guardrails", "Constraints", "Rules"
    guard_match = re.search(
        r"(?:^|\n)##?\s*(?:Guardrails|Constraints|Rules)[^\n]*\n((?:[-*]\s+.+\n)+)",
        body,
        re.IGNORECASE | re.MULTILINE,
    )
    if guard_match:
        for line in guard_match.group(1).strip().split("\n"):
            line = line.strip().lstrip("-*").strip()
            if line:
                metadata["guardrails"].append(line[:80])
    
    # Outputs: Look for "Outputs", "Produces", "Generates"
    output_match = re.search(
        r"(?:^|\n)##?\s*(?:Outputs?|Produces|Generates)[^\n]*\n((?:[-*]\s+.+\n)+)",
        body,
        re.IGNORECASE | re.MULTILINE,
    )
    if output_match:
        for line in output_match.group(1).strip().split("\n"):
            line = line.strip().lstrip("-*").strip()
            if line:
                metadata["outputs"].append(line[:80])
    
    # Backing services: Look for mentions of CLIs, APIs, tools
    services_match = re.search(
        r"(?:^|\n)##?\s*(?:Backing Services|Dependencies|Tools|Requirements)[^\n]*\n((?:[-*]\s+.+\n)+)",
        body,
        re.IGNORECASE | re.MULTILINE,
    )
    if services_match:
        for line in services_match.group(1).strip().split("\n"):
            line = line.strip().lstrip("-*").strip()
            if line:
                metadata["backing_services"].append(line[:80])
    
    return metadata


def match_skills_for_query(repo_root: Path, query: str, *, top_k: int = 5) -> list[SkillMatch]:
    """Rank registered skills against a free-form query."""
    q_terms = _tokens(query)
    if not q_terms:
        return []

    scored: list[SkillMatch] = []
    for skill in load_registered_skills(repo_root):
        score = score_skill(skill, query, q_terms)
        if score <= 0:
            continue
        scored.append(_to_match(skill, score))

    scored.sort(key=lambda s: (s.score, s.id), reverse=True)
    return scored[:top_k]


def aggregate_skill_graph_context(
    repo_root: Path,
    nodes: list[dict[str, Any]],
    *,
    top_coverage_per_skill: int = TOP_COVERAGE_PER_SKILL,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Create synthetic skill nodes + top-K `covers` edges per skill.

    Returns (skill_nodes, covers_edges). Each skill node includes metadata that
    the frontend can use to build the left-rail aggregated Skills view.
    """
    project_nodes = [n for n in nodes if n.get("kind") != "skill" and n.get("layer") != "skills"]
    if not project_nodes:
        return [], []

    skills = load_registered_skills(repo_root)
    if not skills:
        return [], []

    skill_nodes: list[dict[str, Any]] = []
    covers_edges: list[dict[str, Any]] = []

    for skill in skills:
        per_node: list[tuple[int, dict[str, Any]]] = []
        for node in project_nodes:
            query = _node_context(node)
            score = score_skill(skill, query, _tokens(query))
            if score > 0:
                per_node.append((score, node))
        if not per_node:
            continue

        per_node.sort(key=lambda item: (item[0], str(item[1].get("label", ""))), reverse=True)
        top = per_node[:top_coverage_per_skill]
        skill_id = str(skill.get("name", ""))
        node_id = f"skill:{skill_id}"
        matched_node_ids = [str(node.get("id", "")) for _, node in top if node.get("id")]
        coverage_count = len(per_node)

        skill_nodes.append({
            "id": node_id,
            "label": skill_id,
            "kind": "skill",
            "layer": "skills",
            "desc": str(skill.get("description", ""))[:260],
            "status": "ok",
            "meta": {
                "skill_id": skill_id,
                "path": str(skill.get("path", "")),
                "origin": str(skill.get("origin", "")) or "",
                "coverage_count": coverage_count,
                "matched_node_ids": ",".join(matched_node_ids),
                "tags": ", ".join(_string_list(skill.get("tags"))),
                "triggers": " | ".join(_string_list(skill.get("triggers"))[:4]),
            },
        })

        for rank, (score, node) in enumerate(top, start=1):
            target_id = str(node.get("id", ""))
            covers_edges.append({
                "id": f"covers:{skill_id}:{rank}:{target_id}",
                "source": node_id,
                "target": target_id,
                "kind": "covers",
                "label": f"top {rank}",
                "desc": f"{skill_id} helps explain {node.get('label', target_id)} (score {score})",
            })

    skill_nodes.sort(key=lambda n: int(n.get("meta", {}).get("coverage_count", 0)), reverse=True)
    return skill_nodes, covers_edges


def score_skill(skill: dict[str, Any], query: str, q_terms: set[str] | None = None) -> int:
    """Heuristic relevance score between skill metadata and project context."""
    q_terms = q_terms or _tokens(query)
    if not q_terms:
        return 0

    name = str(skill.get("name", ""))
    description = str(skill.get("description", ""))
    triggers = _string_list(skill.get("triggers"))
    tags = _string_list(skill.get("tags"))
    haystack = " ".join([name, description, " ".join(triggers), " ".join(tags)]).lower()

    score = 0
    name_tokens = _tokens(name)
    desc_tokens = _tokens(description)
    trigger_tokens = _tokens(" ".join(triggers))
    tag_tokens = _tokens(" ".join(tags))

    score += len(q_terms & name_tokens) * 5
    score += len(q_terms & desc_tokens) * 2
    score += len(q_terms & trigger_tokens) * 3
    score += len(q_terms & tag_tokens) * 3

    lower_query = query.lower()
    for trig in triggers:
        trig_l = trig.lower().strip()
        if trig_l and trig_l in lower_query:
            score += 6

    # Layer/kind boosts keep canonical UiPath skills visible even when their
    # metadata does not exactly share words with a file name.
    category_boosts = {
        "rpa": ("xaml", "workflow", "activity", "queue", "orchestrator"),
        "agents": ("agent", "langgraph", "llm", "graph", "tool"),
        "maestro": ("maestro", "flow", "case", "bpmn"),
        "coded-apps": ("coded_app", "action_app", "app.config", "typescript"),
        "platform": ("orchestrator", "queue", "asset", "process", "folder", "deploy"),
        "test": ("test", "test_set", "test_case", "qa"),
        "diagnostics": ("error", "warn", "failure", "diagnose", "debug"),
    }
    for category, hints in category_boosts.items():
        if category in name.lower() and any(h in lower_query for h in hints):
            score += 5

    # Guard against high-noise generic term overlap.
    if score == 1 and not any(term in haystack for term in q_terms):
        return 0
    return score


def _to_match(skill: dict[str, Any], score: int) -> SkillMatch:
    return SkillMatch(
        id=str(skill.get("name", "")),
        path=str(skill.get("path", "")),
        reason=str(skill.get("description", ""))[:240],
        origin=str(skill.get("origin", "")) or None,
        score=score,
        tags=tuple(_string_list(skill.get("tags"))),
        triggers=tuple(_string_list(skill.get("triggers"))),
    )


def _node_context(node: dict[str, Any]) -> str:
    code = node.get("code") if isinstance(node.get("code"), dict) else {}
    meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
    return " ".join(
        str(part)
        for part in (
            node.get("id", ""),
            node.get("label", ""),
            node.get("kind", ""),
            node.get("layer", ""),
            node.get("desc", ""),
            node.get("concept", ""),
            code.get("path", ""),
            code.get("snippet", "")[:600],
            " ".join(str(v) for v in meta.values()),
        )
        if part
    )


def _tokens(text: str) -> set[str]:
    stop = {
        "the", "and", "for", "with", "from", "that", "this", "your", "into",
        "using", "use", "when", "what", "does", "file", "node", "project",
    }
    return {t for t in re.findall(r"[a-zA-Z0-9_#.-]{3,}", text.lower()) if t not in stop}


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v]
    if isinstance(value, tuple):
        return [str(v) for v in value if v]
    return [str(value)] if str(value).strip() else []


def _strip_frontmatter(body: str) -> str:
    lines = body.splitlines()
    if lines and lines[0].lstrip("\ufeff").strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                return "\n".join(lines[index + 1:]).strip()
    return body.strip()
