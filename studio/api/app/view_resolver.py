"""Resolve AS-IS and TO-BE views from YAML config, markdown, and indexed graph.

Builds AsIsView and ToBeView datastructures that the frontend renders as
stakeholder-facing process canvases.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .explorer_config import (
    AsIsSpec,
    ToBeSpec,
    ViewsSpec,
    load_config,
    ActorSpec,
)
from .mermaid_parser import extract_mermaid_block, MermaidNode, MermaidEdge


@dataclass(frozen=True)
class SourceLink:
    """A reference back to the source document."""
    path: str
    anchor: str | None = None
    line: int | None = None


@dataclass(frozen=True)
class PainPoint:
    """A pain point in the AS-IS process."""
    label: str
    description: str
    related_handoff_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Handoff:
    """A handoff in the AS-IS swim-lane view."""
    id: str
    from_actor: str
    to_actor: str
    channel: str  # email | phone | excel | paper | meeting
    artifact: str
    sla: str
    pain: str
    sequence: int  # 1-based ordering
    docs_path: str | None = None


@dataclass(frozen=True)
class AsIsView:
    """AS-IS manual process view — swim-lanes + handoffs + pain points."""
    swimlanes: tuple[str, ...]  # Ordered actor names
    handoffs: tuple[Handoff, ...]
    pain_points: tuple[PainPoint, ...]
    sources: tuple[SourceLink, ...]
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "swimlanes": list(self.swimlanes),
            "handoffs": [
                {
                    "id": h.id,
                    "from_actor": h.from_actor,
                    "to_actor": h.to_actor,
                    "channel": h.channel,
                    "artifact": h.artifact,
                    "sla": h.sla,
                    "pain": h.pain,
                    "sequence": h.sequence,
                    "docs_path": h.docs_path,
                }
                for h in self.handoffs
            ],
            "pain_points": [
                {
                    "label": p.label,
                    "description": p.description,
                    "related_handoff_ids": list(p.related_handoff_ids),
                }
                for p in self.pain_points
            ],
            "sources": [
                {"path": s.path, "anchor": s.anchor, "line": s.line}
                for s in self.sources
            ],
        }


@dataclass(frozen=True)
class ToBeWorkflow:
    """A workflow in the TO-BE solution."""
    id: str
    label: str
    path: str
    bucket: str  # intake | processing | review | evidence
    internal_steps: tuple[dict[str, Any], ...]  # Mermaid nodes from plan/tasks
    drill_docs_path: str | None = None


@dataclass(frozen=True)
class ToBeIntegration:
    """An external integration in the TO-BE solution."""
    id: str
    label: str  # Salesforce | Slack | HTTP API | Email
    system: str
    used_by_workflow_ids: tuple[str, ...]
    drill_docs_path: str | None = None


@dataclass(frozen=True)
class ToBeOrchResource:
    """An Orchestrator resource in the TO-BE solution."""
    id: str
    label: str  # Queue | Asset | Action Center | Storage Bucket
    resource_type: str
    used_by_workflow_ids: tuple[str, ...]
    drill_docs_path: str | None = None


@dataclass(frozen=True)
class ToBeHitl:
    """A HITL surface in the TO-BE solution."""
    id: str
    label: str
    channel: str  # Action Center | Maestro | Slack | Custom
    actor: str
    callback_contract: str
    drill_docs_path: str | None = None


@dataclass(frozen=True)
class ToBeBucket:
    """A logical grouping bucket in the TO-BE architecture."""
    id: str
    label: str
    bucket_type: str  # triggers | intake | processing | integrations | hitl | evidence
    node_ids: tuple[str, ...]  # References to workflows, integrations, orch resources


@dataclass(frozen=True)
class SequenceStep:
    """A step in the runtime sequence diagram."""
    from_participant: str
    to_participant: str
    label: str
    sequence: int
    is_return: bool = False  # Dashed arrow


@dataclass(frozen=True)
class ToBeView:
    """TO-BE automated solution view — architecture buckets + workflows + integrations."""
    buckets: tuple[ToBeBucket, ...]
    workflows: tuple[ToBeWorkflow, ...]
    integrations: tuple[ToBeIntegration, ...]
    orchestrator: tuple[ToBeOrchResource, ...]
    hitl: tuple[ToBeHitl, ...]
    runtime_sequence: tuple[SequenceStep, ...]
    sources: tuple[SourceLink, ...]
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "buckets": [
                {
                    "id": b.id,
                    "label": b.label,
                    "bucket_type": b.bucket_type,
                    "node_ids": list(b.node_ids),
                }
                for b in self.buckets
            ],
            "workflows": [
                {
                    "id": w.id,
                    "label": w.label,
                    "path": w.path,
                    "bucket": w.bucket,
                    "internal_steps": list(w.internal_steps),
                    "drill_docs_path": w.drill_docs_path,
                }
                for w in self.workflows
            ],
            "integrations": [
                {
                    "id": i.id,
                    "label": i.label,
                    "system": i.system,
                    "used_by_workflow_ids": list(i.used_by_workflow_ids),
                    "drill_docs_path": i.drill_docs_path,
                }
                for i in self.integrations
            ],
            "orchestrator": [
                {
                    "id": o.id,
                    "label": o.label,
                    "resource_type": o.resource_type,
                    "used_by_workflow_ids": list(o.used_by_workflow_ids),
                    "drill_docs_path": o.drill_docs_path,
                }
                for o in self.orchestrator
            ],
            "hitl": [
                {
                    "id": h.id,
                    "label": h.label,
                    "channel": h.channel,
                    "actor": h.actor,
                    "callback_contract": h.callback_contract,
                    "drill_docs_path": h.drill_docs_path,
                }
                for h in self.hitl
            ],
            "runtime_sequence": [
                {
                    "from_participant": s.from_participant,
                    "to_participant": s.to_participant,
                    "label": s.label,
                    "sequence": s.sequence,
                    "is_return": s.is_return,
                }
                for s in self.runtime_sequence
            ],
            "sources": [
                {"path": s.path, "anchor": s.anchor, "line": s.line}
                for s in self.sources
            ],
        }


def load_views_config(project_root: Path) -> ViewsSpec:
    """Load views configuration from .uiplan/explorer.yaml."""
    config = load_config(project_root)
    return config.views


def resolve_as_is(
    project_root: Path,
    views_spec: ViewsSpec,
    overview_actors: list[ActorSpec],
) -> AsIsView:
    """Build AS-IS view from YAML config + optional markdown diagrams."""
    as_is = views_spec.as_is
    sources: list[SourceLink] = []
    
    # Resolve actors/swimlanes
    swimlanes: list[str] = []
    if as_is.actors_from == "explorer.actors":
        swimlanes = [actor.name for actor in overview_actors]
    elif as_is.swimlanes:
        swimlanes = list(as_is.swimlanes)
    
    # Resolve handoffs
    handoffs: list[Handoff] = []
    if as_is.diagram_from:
        # Try to extract from Mermaid diagram
        parts = as_is.diagram_from.split("#", 1)
        file_rel = parts[0]
        anchor = parts[1] if len(parts) > 1 else None
        file_path = project_root / file_rel
        
        mermaid_block = extract_mermaid_block(file_path, anchor)
        if mermaid_block:
            handoffs = _extract_handoffs_from_mermaid(mermaid_block)
            sources.append(SourceLink(path=file_rel, anchor=anchor))
    
    # Fallback to explicit handoffs from YAML
    if not handoffs and as_is.handoffs:
        for idx, h_spec in enumerate(as_is.handoffs, start=1):
            handoffs.append(Handoff(
                id=f"handoff-{idx}",
                from_actor=h_spec.from_actor,
                to_actor=h_spec.to_actor,
                channel=h_spec.channel,
                artifact=h_spec.artifact,
                sla=h_spec.sla,
                pain=h_spec.pain,
                sequence=idx,
                docs_path=h_spec.docs,
            ))
    
    # Resolve pain points
    pain_points: list[PainPoint] = []
    if as_is.pain_points:
        pain_file = project_root / as_is.pain_points
        if pain_file.exists():
            pain_points = _extract_pain_points(pain_file)
            sources.append(SourceLink(path=as_is.pain_points))
    
    return AsIsView(
        swimlanes=tuple(swimlanes),
        handoffs=tuple(handoffs),
        pain_points=tuple(pain_points),
        sources=tuple(sources),
    )


def resolve_to_be(
    project_root: Path,
    views_spec: ViewsSpec,
    indexed_graph: dict[str, Any],
) -> ToBeView:
    """Build TO-BE view from YAML config + indexed graph."""
    to_be = views_spec.to_be
    sources: list[SourceLink] = []
    
    # Resolve architecture diagram
    architecture_nodes: list[MermaidNode] = []
    architecture_edges: list[MermaidEdge] = []
    
    for arch_ref in to_be.architecture_from:
        parts = arch_ref.split("#", 1)
        file_rel = parts[0]
        anchor = parts[1] if len(parts) > 1 else None
        file_path = project_root / file_rel
        
        mermaid_block = extract_mermaid_block(file_path, anchor)
        if mermaid_block:
            architecture_nodes = mermaid_block.nodes
            architecture_edges = mermaid_block.edges
            sources.append(SourceLink(path=file_rel, anchor=anchor))
            break  # Use first found
    
    # Build buckets from architecture
    buckets = _build_buckets_from_architecture(architecture_nodes, architecture_edges)
    
    # Extract workflows from indexed graph
    workflows = _extract_workflows_from_graph(indexed_graph, to_be, project_root)
    
    # Extract integrations from indexed graph
    integrations = _extract_integrations_from_graph(indexed_graph, to_be)
    
    # Extract Orchestrator resources from indexed graph
    orch_resources = _extract_orch_resources_from_graph(indexed_graph, to_be)
    
    # Extract HITL surfaces
    hitl = _extract_hitl_from_graph(indexed_graph, to_be)
    
    # Resolve runtime sequence
    sequence_steps: list[SequenceStep] = []
    if to_be.runtime_sequence_from:
        parts = to_be.runtime_sequence_from.split("#", 1)
        file_rel = parts[0]
        anchor = parts[1] if len(parts) > 1 else None
        file_path = project_root / file_rel
        
        mermaid_block = extract_mermaid_block(file_path, anchor)
        if mermaid_block:
            sequence_steps = _extract_sequence_from_mermaid(mermaid_block)
            sources.append(SourceLink(path=file_rel, anchor=anchor))
    
    return ToBeView(
        buckets=tuple(buckets),
        workflows=tuple(workflows),
        integrations=tuple(integrations),
        orchestrator=tuple(orch_resources),
        hitl=tuple(hitl),
        runtime_sequence=tuple(sequence_steps),
        sources=tuple(sources),
    )


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _extract_handoffs_from_mermaid(mermaid_block: Any) -> list[Handoff]:
    """Extract handoffs from a Mermaid flowchart or sequence diagram."""
    handoffs: list[Handoff] = []
    
    for idx, edge in enumerate(mermaid_block.edges, start=1):
        handoffs.append(Handoff(
            id=f"handoff-{idx}",
            from_actor=edge.source,
            to_actor=edge.target,
            channel="",  # Not extractable from Mermaid
            artifact=edge.label or "",
            sla="",
            pain="",
            sequence=idx,
        ))
    
    return handoffs


def _extract_pain_points(pain_file: Path) -> list[PainPoint]:
    """Extract pain points from a markdown file (bullet list)."""
    try:
        content = pain_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    
    pain_points: list[PainPoint] = []
    for line in content.splitlines():
        line = line.strip()
        if line.startswith(("-", "*", "+")):
            label = line.lstrip("-*+ ").strip()
            if label:
                pain_points.append(PainPoint(
                    label=label,
                    description=label,
                ))
    
    return pain_points


def _build_buckets_from_architecture(
    nodes: list[MermaidNode],
    edges: list[MermaidEdge],
) -> list[ToBeBucket]:
    """Build logical buckets from architecture diagram nodes."""
    # Group nodes by their class_name or infer from labels
    bucket_map: dict[str, list[str]] = {
        "triggers": [],
        "intake": [],
        "processing": [],
        "integrations": [],
        "hitl": [],
        "evidence": [],
    }
    
    for node in nodes:
        bucket_type = _infer_bucket_type(node)
        bucket_map[bucket_type].append(node.id)
    
    buckets: list[ToBeBucket] = []
    for bucket_type, node_ids in bucket_map.items():
        if node_ids:
            buckets.append(ToBeBucket(
                id=f"bucket-{bucket_type}",
                label=bucket_type.title(),
                bucket_type=bucket_type,
                node_ids=tuple(node_ids),
            ))
    
    return buckets


def _infer_bucket_type(node: MermaidNode) -> str:
    """Infer bucket type from node class or label."""
    if node.class_name:
        class_lower = node.class_name.lower()
        if "trigger" in class_lower or "entry" in class_lower:
            return "triggers"
        if "intake" in class_lower or "orchestr" in class_lower:
            return "intake"
        if "process" in class_lower or "worker" in class_lower:
            return "processing"
        if "external" in class_lower or "integration" in class_lower:
            return "integrations"
        if "human" in class_lower or "hitl" in class_lower or "review" in class_lower:
            return "hitl"
        if "evidence" in class_lower or "audit" in class_lower or "data" in class_lower:
            return "evidence"
    
    # Fallback to label-based inference
    label_lower = node.label.lower()
    if any(word in label_lower for word in ("trigger", "entry", "input")):
        return "triggers"
    if any(word in label_lower for word in ("intake", "orchestr", "dispatcher")):
        return "intake"
    if any(word in label_lower for word in ("worker", "processor", "agent")):
        return "processing"
    if any(word in label_lower for word in ("external", "api", "connector", "salesforce", "slack")):
        return "integrations"
    if any(word in label_lower for word in ("human", "review", "approval", "hitl")):
        return "hitl"
    if any(word in label_lower for word in ("audit", "evidence", "log", "queue")):
        return "evidence"
    
    return "processing"  # Default


def _extract_workflows_from_graph(
    indexed_graph: dict[str, Any],
    to_be: ToBeSpec,
    project_root: Path,
) -> list[ToBeWorkflow]:
    """Extract workflows from the indexed project graph."""
    workflows: list[ToBeWorkflow] = []
    
    for node in indexed_graph.get("nodes", []):
        if node.get("kind") in ("workflow", "xaml_workflow", "flow"):
            workflow_id = node["id"]
            label = node.get("label", "Unnamed Workflow")
            path = node.get("code", {}).get("path", "")
            
            # Infer bucket from node metadata or layer
            bucket = "processing"  # Default
            if node.get("roles") and "entrypoint" in node["roles"]:
                bucket = "intake"
            
            # Try to load internal steps from drill_docs
            internal_steps: list[dict[str, Any]] = []
            drill_docs_path = to_be.drill_docs.get(label) or to_be.drill_docs.get(path)
            if drill_docs_path:
                drill_file = project_root / drill_docs_path
                if drill_file.exists():
                    mermaid_block = extract_mermaid_block(drill_file)
                    if mermaid_block:
                        internal_steps = [
                            {"id": n.id, "label": n.label, "shape": n.shape}
                            for n in mermaid_block.nodes
                        ]
            
            workflows.append(ToBeWorkflow(
                id=workflow_id,
                label=label,
                path=path,
                bucket=bucket,
                internal_steps=tuple(internal_steps),
                drill_docs_path=drill_docs_path,
            ))
    
    return workflows


def _extract_integrations_from_graph(
    indexed_graph: dict[str, Any],
    to_be: ToBeSpec,
) -> list[ToBeIntegration]:
    """Extract external integrations from the indexed project graph."""
    integrations: list[ToBeIntegration] = []
    
    for node in indexed_graph.get("nodes", []):
        if node.get("kind") == "external":
            integration_id = node["id"]
            label = node.get("label", "Unknown Integration")
            system = label  # e.g. "Salesforce", "Slack", "HTTP API"
            
            # Find workflows that use this integration
            used_by: list[str] = []
            for edge in indexed_graph.get("edges", []):
                if edge.get("target") == integration_id and edge.get("kind") == "uses":
                    used_by.append(edge["source"])
            
            drill_docs_path = to_be.drill_docs.get(label)
            
            integrations.append(ToBeIntegration(
                id=integration_id,
                label=label,
                system=system,
                used_by_workflow_ids=tuple(used_by),
                drill_docs_path=drill_docs_path,
            ))
    
    return integrations


def _extract_orch_resources_from_graph(
    indexed_graph: dict[str, Any],
    to_be: ToBeSpec,
) -> list[ToBeOrchResource]:
    """Extract Orchestrator resources from the indexed project graph."""
    resources: list[ToBeOrchResource] = []
    
    for node in indexed_graph.get("nodes", []):
        if node.get("kind") == "orchestrator_resource":
            resource_id = node["id"]
            label = node.get("label", "Unknown Resource")
            resource_type = label  # e.g. "Queue", "Asset", "Action Center"
            
            # Find workflows that use this resource
            used_by: list[str] = []
            for edge in indexed_graph.get("edges", []):
                if edge.get("target") == resource_id and edge.get("kind") == "uses":
                    used_by.append(edge["source"])
            
            drill_docs_path = to_be.drill_docs.get(label)
            
            resources.append(ToBeOrchResource(
                id=resource_id,
                label=label,
                resource_type=resource_type,
                used_by_workflow_ids=tuple(used_by),
                drill_docs_path=drill_docs_path,
            ))
    
    return resources


def _extract_hitl_from_graph(
    indexed_graph: dict[str, Any],
    to_be: ToBeSpec,
) -> list[ToBeHitl]:
    """Extract HITL surfaces from the indexed project graph."""
    hitl_surfaces: list[ToBeHitl] = []
    
    for node in indexed_graph.get("nodes", []):
        if node.get("roles") and "hitl" in node["roles"]:
            hitl_id = node["id"]
            label = node.get("label", "Unknown HITL")
            channel = node.get("meta", {}).get("hitl_channel", "Action Center")
            actor = node.get("meta", {}).get("hitl_actor", "Reviewer")
            callback_contract = node.get("meta", {}).get("callback_contract", "")
            drill_docs_path = to_be.drill_docs.get(label)
            
            hitl_surfaces.append(ToBeHitl(
                id=hitl_id,
                label=label,
                channel=channel,
                actor=actor,
                callback_contract=callback_contract,
                drill_docs_path=drill_docs_path,
            ))
    
    return hitl_surfaces


def _extract_sequence_from_mermaid(mermaid_block: Any) -> list[SequenceStep]:
    """Extract runtime sequence steps from a Mermaid sequence diagram."""
    steps: list[SequenceStep] = []
    
    for idx, edge in enumerate(mermaid_block.edges, start=1):
        steps.append(SequenceStep(
            from_participant=edge.source,
            to_participant=edge.target,
            label=edge.label or "",
            sequence=idx,
            is_return=edge.style == "dashed",
        ))
    
    return steps
