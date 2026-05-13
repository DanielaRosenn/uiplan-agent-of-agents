from __future__ import annotations

import difflib
import hashlib
import json
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from app.generation_contracts.command_registry import get_command_registry
from app.generation_contracts.constants import DEFERRED_STAGE_IDS
from app.generation_contracts.models import (
    ApprovalPackageManifest,
    FileProposal,
    FindingRecord,
    GenerationContextAttachment,
    GenerationGraph,
    GenerationGraphNode,
    StageManifest,
)
from app.generation_contracts.path_allowlist import validate_target_path
from app.generation_contracts.storage import create_package_layout, list_packages, read_package_state


def _stable_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(path.parent),
        delete=False,
        newline="\n",
    ) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def _write_json_atomic(path: Path, payload: Any) -> None:
    _write_text_atomic(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _stage_command_ids(stage_id: str) -> list[str]:
    registry = get_command_registry()
    return [command.command_id for command in registry.commands if command.owning_stage == stage_id]


def _build_context_manifest(graph: GenerationGraph, graph_hash: str) -> dict[str, Any]:
    attachments = [attachment.model_dump(mode="json") for attachment in graph.context_attachments]
    strict_count = sum(1 for attachment in graph.context_attachments if attachment.policy == "strict")
    advisory_count = sum(1 for attachment in graph.context_attachments if attachment.policy == "advisory")
    context_manifest = {
        "attachments": attachments,
        "strict_attachment_count": strict_count,
        "advisory_attachment_count": advisory_count,
        "source_graph_hash": graph_hash,
    }
    context_manifest["context_manifest_hash"] = _sha256(_stable_json(context_manifest))
    return context_manifest


def _node_requires_strict_citation(node: GenerationGraphNode) -> bool:
    text = f"{node.title} {node.description} {node.role} {node.output_type} {' '.join(node.project_types)}".lower()
    if node.role in {"deployment_gate", "asset", "queue"}:
        return True
    if node.output_type in {"orchestrator_resource", "validation_report"}:
        return True
    required_fragments = (
        "runtime",
        "security",
        "credential",
        "deploy",
        "production",
    )
    return any(fragment in text for fragment in required_fragments)


def _normalize_ref(value: str | None) -> str:
    return (value or "").strip().lower()


def _strict_attachments_for_node(
    node: GenerationGraphNode,
    strict_attachments: list[GenerationContextAttachment],
) -> list[GenerationContextAttachment]:
    node_refs = {_normalize_ref(ref) for ref in node.context_attachment_ids if _normalize_ref(ref)}
    if not node_refs:
        return []
    matched: list[GenerationContextAttachment] = []
    for attachment in strict_attachments:
        source_ref = _normalize_ref(attachment.source_id)
        citation_ref = _normalize_ref(attachment.citation)
        if source_ref in node_refs or citation_ref in node_refs:
            matched.append(attachment)
    return matched


def _build_blocking_findings(
    graph: GenerationGraph,
    strict_attachments: list[GenerationContextAttachment],
) -> list[FindingRecord]:
    findings: list[FindingRecord] = []
    for node in graph.nodes:
        if _node_requires_strict_citation(node) and not _strict_attachments_for_node(
            node, strict_attachments
        ):
            findings.append(
                FindingRecord(
                    severity="error",
                    message=(
                        f"Node '{node.title}' requires a node-linked strict citation before apply is allowed."
                    ),
                    scope="node",
                    target_id=node.id,
                    blocks_apply=True,
                )
            )
    return findings


def _render_plan_proposal(
    graph: GenerationGraph,
    citations: list[str],
) -> str:
    nodes_block = "\n".join(
        f"- {node.title} ({node.role}, {node.output_type})"
        for node in graph.nodes
    ) or "- No graph nodes captured."
    citations_block = "\n".join(f"- {citation}" for citation in citations) or "- No citations attached."
    stages_block = "\n".join(
        [
            "1. Generate and review Plan package proposal.",
            "2. Approve Stage 01 proposal after findings review.",
            "3. Keep apply and deploy actions out of this generation step.",
        ]
    )
    return (
        "# UiPlan Generation Plan\n\n"
        "## Solution Intent\n\n"
        f"Graph `{graph.graph_id}` captures the scoped generation intent for this bundle.\n\n"
        "## Architecture\n\n"
        "The package stores proposal artifacts under `.uiplan/generation/packages/<package-id>/` "
        "with preview/apply separation.\n\n"
        "## Graph Nodes\n\n"
        f"{nodes_block}\n\n"
        "## Context And Citations\n\n"
        f"{citations_block}\n\n"
        "## Safety Policy\n\n"
        "- No direct target-file writes are performed during package generation.\n"
        "- No deploy, publish, invoke, or external mutation command is executed.\n\n"
        "## Implementation Sequence\n\n"
        f"{stages_block}\n"
    )


def _title_to_slug(title: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", title.strip().lower())
    return cleaned.strip("-") or "node"


def _title_to_pascal(title: str) -> str:
    words = re.split(r"[^A-Za-z0-9]+", title.strip())
    parts = [word for word in words if word]
    if not parts:
        return "Node"
    return "".join(part[:1].upper() + part[1:] for part in parts)


def _render_scaffold_manifest(node: GenerationGraphNode, pascal_title: str) -> dict[str, Any]:
    return {
        "package_name": f"UiPlan.{pascal_title}",
        "node_id": node.id,
        "project_types": node.project_types,
        "recommended_files": [
            f"projects/{pascal_title}/README.md",
            f"projects/{pascal_title}/project.manifest.json",
        ],
        "non_secret_config": {
            "secret_storage": "Use Orchestrator assets or environment variable references only"
        },
        "direct_write": False,
        "external_mutation": False,
    }


def _has_approved_prior_plan_for_graph(
    *,
    bundle_root: Path,
    graph: GenerationGraph,
    graph_hash: str,
) -> bool:
    for manifest in list_packages(bundle_root):
        if "01-plan" not in manifest.generated_stages:
            continue
        if manifest.graph_id != graph.graph_id:
            continue
        package_root = bundle_root / ".uiplan" / "generation" / "packages" / manifest.package_id
        state_path = package_root / "approval-state.json"
        if not state_path.exists():
            continue
        state = read_package_state(package_root)
        if state.stage_statuses.get("01-plan") != "approved":
            continue
        context_manifest_path = package_root / "context.manifest.json"
        if context_manifest_path.exists():
            payload = json.loads(context_manifest_path.read_text(encoding="utf-8"))
            if payload.get("source_graph_hash") == graph_hash:
                return True
        for proposal_state in state.proposals.values():
            if proposal_state.stage_id == "01-plan" and proposal_state.source_graph_hash == graph_hash:
                return True
    return False


def generate_approval_package(
    *,
    bundle_root: Path,
    graph: GenerationGraph,
    requested_stages: list[str],
    reviewer: str | None = None,
) -> ApprovalPackageManifest:
    _ = reviewer
    graph_payload = graph.model_dump(mode="json")
    graph_hash = _sha256(_stable_json(graph_payload))
    requested_stage_set = set(requested_stages)
    if "02-scaffold" in requested_stage_set and "01-plan" not in requested_stage_set:
        if not _has_approved_prior_plan_for_graph(
            bundle_root=bundle_root,
            graph=graph,
            graph_hash=graph_hash,
        ):
            raise ValueError(
                "02-scaffold requires 01-plan in the request or an approved prior Plan package with matching graph lineage"
            )
    for stage in requested_stages:
        if stage in DEFERRED_STAGE_IDS:
            raise ValueError(f"stage generation is deferred: {stage}")
        if stage not in {"01-plan", "02-scaffold"}:
            raise ValueError(f"unsupported stage id: {stage}")

    package_seed = _stable_json({"graph": graph_payload, "requested_stages": requested_stages})
    package_id = f"pkg-{_sha256(package_seed)[:12]}"

    context_manifest = _build_context_manifest(graph, graph_hash)
    strict_attachments = [a for a in graph.context_attachments if a.policy == "strict"]
    citations = [
        attachment.citation or attachment.source_id
        for attachment in graph.context_attachments
    ]
    blocking_findings = _build_blocking_findings(graph, strict_attachments)

    stages: list[StageManifest] = []
    proposal_hashes: dict[str, str] = {}
    proposal_payloads: list[FileProposal] = []

    if "01-plan" in requested_stages:
        proposal_target_path = "docs/uiplan-generation-plan.md"
        validate_target_path(
            bundle_root=bundle_root,
            target_path=proposal_target_path,
            stage_id="01-plan",
            file_kind="document",
        )
        proposal_content = _render_plan_proposal(graph, citations)
        proposal_id = "01-plan:uiplan-generation-plan"
        proposal_hash = _sha256(proposal_content)
        proposal_hashes[proposal_id] = proposal_hash
        apply_eligible = not blocking_findings
        stage = StageManifest(
            stage_id="01-plan",
            status="ready_for_review",
            input_graph_hash=graph_hash,
            input_context_hash=context_manifest["context_manifest_hash"],
            generated_files=[proposal_target_path],
            required_approvals=["proposal"],
            blocking_findings=blocking_findings,
            validation_commands=_stage_command_ids("01-plan"),
            apply_eligible=apply_eligible,
        )
        stages.append(stage)
        proposal_payloads.append(
            FileProposal(
                proposal_id=proposal_id,
                stage_id="01-plan",
                target_path=proposal_target_path,
                file_kind="document",
                owning_node_ids=[node.id for node in graph.nodes],
                project_type_ids=sorted({ptype for node in graph.nodes for ptype in node.project_types}),
                proposed_content_hash=proposal_hash,
                base_hash=None,
                diff_path="stages/01-plan/diffs/uiplan-generation-plan.md.diff",
                proposal_path="stages/01-plan/proposals/uiplan-generation-plan.md",
                citations=citations,
                findings=blocking_findings,
                apply_eligible=apply_eligible,
            )
        )

    if "02-scaffold" in requested_stages:
        scaffold_nodes = [
            node
            for node in graph.nodes
            if node.role in {"project_component", "process_step"} and node.project_types
        ]
        generated_files: list[str] = []
        for node in scaffold_nodes:
            slug = _title_to_slug(node.title)
            pascal_title = _title_to_pascal(node.title)
            target_path = f"projects/{pascal_title}/project.manifest.json"
            validate_target_path(
                bundle_root=bundle_root,
                target_path=target_path,
                stage_id="02-scaffold",
                file_kind="project_scaffold",
            )
            proposal_id = f"02-scaffold:{slug}"
            proposal_filename = f"projects-{slug}-manifest.json"
            proposal_content = _render_scaffold_manifest(node, pascal_title)
            proposal_content_text = json.dumps(proposal_content, indent=2, sort_keys=True) + "\n"
            proposal_hash = _sha256(proposal_content_text)
            proposal_hashes[proposal_id] = proposal_hash
            generated_files.append(target_path)
            proposal_payloads.append(
                FileProposal(
                    proposal_id=proposal_id,
                    stage_id="02-scaffold",
                    target_path=target_path,
                    file_kind="project_scaffold",
                    owning_node_ids=[node.id],
                    project_type_ids=node.project_types,
                    proposed_content_hash=proposal_hash,
                    base_hash=None,
                    diff_path=f"stages/02-scaffold/diffs/{proposal_filename}.diff",
                    proposal_path=f"stages/02-scaffold/proposals/{proposal_filename}",
                    citations=citations,
                    findings=[],
                    apply_eligible=True,
                )
            )

        has_scaffold_proposals = bool(generated_files)
        stages.append(
            StageManifest(
                stage_id="02-scaffold",
                status="ready_for_review" if has_scaffold_proposals else "not_started",
                input_graph_hash=graph_hash,
                input_context_hash=context_manifest["context_manifest_hash"],
                generated_files=generated_files,
                required_approvals=["proposal"] if has_scaffold_proposals else [],
                blocking_findings=[],
                validation_commands=_stage_command_ids("02-scaffold"),
                apply_eligible=has_scaffold_proposals,
            )
        )

    layout = create_package_layout(
        bundle_root=bundle_root,
        package_id=package_id,
        graph=graph,
        context_manifest=context_manifest,
        stages=stages,
        proposal_hashes=proposal_hashes,
    )

    for proposal in proposal_payloads:
        stage_root = layout.package_root / "stages" / proposal.stage_id
        proposal_file = stage_root / proposal.proposal_path.split("/", 2)[-1]
        diff_file = stage_root / proposal.diff_path.split("/", 2)[-1]
        if proposal.stage_id == "01-plan":
            content = _render_plan_proposal(graph, proposal.citations)
            _write_text_atomic(proposal_file, content)
            diff = "".join(
                difflib.unified_diff(
                    [],
                    content.splitlines(keepends=True),
                    fromfile=proposal.target_path,
                    tofile=proposal.target_path,
                )
            )
            _write_text_atomic(diff_file, diff)
        elif proposal.stage_id == "02-scaffold":
            node = next((item for item in graph.nodes if item.id in proposal.owning_node_ids), None)
            if node is None:
                raise ValueError(f"missing owning node for scaffold proposal: {proposal.proposal_id}")
            content_payload = _render_scaffold_manifest(node, _title_to_pascal(node.title))
            content_text = json.dumps(content_payload, indent=2, sort_keys=True) + "\n"
            _write_text_atomic(proposal_file, content_text)
            diff = "".join(
                difflib.unified_diff(
                    [],
                    content_text.splitlines(keepends=True),
                    fromfile=proposal.target_path,
                    tofile=proposal.target_path,
                )
            )
            _write_text_atomic(diff_file, diff)
        _write_json_atomic(stage_root / "findings.json", [f.model_dump(mode="json") for f in proposal.findings])
        proposal_manifest_name = proposal_file.with_suffix(".proposal.json").name
        _write_json_atomic(stage_root / "proposals" / proposal_manifest_name, proposal.model_dump(mode="json"))

    return layout.manifest
