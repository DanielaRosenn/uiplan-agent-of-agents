import json
from pathlib import Path

import pytest

from app.generation_contracts.models import (
    GenerationContextAttachment,
    GenerationGraph,
    GenerationGraphNode,
)
from app.generation_contracts.package_generation import generate_approval_package


def _mixed_graph(bundle_root: Path) -> GenerationGraph:
    return GenerationGraph(
        graph_id="graph-plan",
        bundle_root=str(bundle_root),
        created_from="test",
        nodes=[
            GenerationGraphNode(
                id="intake",
                title="Customer Intake",
                role="process_step",
                output_type="document",
                project_types=["docs", "coded-agent"],
                description="Capture customer request and decide next action.",
                context_attachment_ids=["ctx-1"],
            ),
            GenerationGraphNode(
                id="deploy",
                title="Deployment Gate",
                role="deployment_gate",
                output_type="approval_gate",
                project_types=["platform-resource"],
                description="Manual deployment readiness only.",
                context_attachment_ids=["ctx-2"],
            ),
        ],
        context_attachments=[
            GenerationContextAttachment(
                source_kind="repo_doc",
                source_id="docs/PDD.md",
                citation="docs/PDD.md",
                scope="graph",
                policy="advisory",
                summary="Business context for intake.",
            ),
            GenerationContextAttachment(
                source_kind="library_book",
                source_id="ctx-2",
                citation="uipath-cli/package-analyze",
                scope="node",
                policy="strict",
                summary="Deployment gate commands are strict context.",
            ),
        ],
    )


def test_generate_plan_package_persists_manifest_and_proposal(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    package = generate_approval_package(
        bundle_root=bundle_root,
        graph=_mixed_graph(bundle_root),
        requested_stages=["01-plan"],
        reviewer="Daniela",
    )

    package_root = bundle_root / ".uiplan" / "generation" / "packages" / package.package_id
    plan_stage = package_root / "stages" / "01-plan"
    proposals = sorted((plan_stage / "proposals").glob("*.md"))

    assert package.generated_stages == ["01-plan"]
    assert len(proposals) == 1
    proposal_text = proposals[0].read_text(encoding="utf-8")
    assert "# UiPlan Generation Plan" in proposal_text
    assert "Customer Intake" in proposal_text
    assert "uipath-cli/package-analyze" in proposal_text
    assert "No deploy, publish, invoke, or external mutation command is executed." in proposal_text
    state = json.loads((package_root / "approval-state.json").read_text(encoding="utf-8"))
    assert state["stage_statuses"]["01-plan"] == "ready_for_review"
    assert state["stage_statuses"]["03-code"] == "not_started"


def test_plan_package_blocks_missing_strict_context_for_deployment_gate(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    graph = _mixed_graph(bundle_root)
    graph.context_attachments = [
        attachment for attachment in graph.context_attachments if attachment.policy != "strict"
    ]

    package = generate_approval_package(
        bundle_root=bundle_root,
        graph=graph,
        requested_stages=["01-plan"],
        reviewer="Daniela",
    )

    package_root = bundle_root / ".uiplan" / "generation" / "packages" / package.package_id
    findings = json.loads(
        (package_root / "stages" / "01-plan" / "findings.json").read_text(encoding="utf-8")
    )
    assert findings[0]["severity"] == "error"
    assert findings[0]["blocks_apply"] is True
    assert "strict citation" in findings[0]["message"].lower()


def test_plan_package_blocks_sensitive_node_without_node_linked_strict_citation(
    tmp_path: Path,
) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    graph = _mixed_graph(bundle_root)
    deploy_node = next(node for node in graph.nodes if node.id == "deploy")
    deploy_node.context_attachment_ids = ["ctx-missing"]
    graph.context_attachments.append(
        GenerationContextAttachment(
            source_kind="library_book",
            source_id="ctx-1",
            citation="ctx-1",
            scope="node",
            policy="strict",
            summary="Strict citation linked only to the non-sensitive intake node.",
        )
    )

    package = generate_approval_package(
        bundle_root=bundle_root,
        graph=graph,
        requested_stages=["01-plan"],
        reviewer="Daniela",
    )

    package_root = bundle_root / ".uiplan" / "generation" / "packages" / package.package_id
    findings = json.loads(
        (package_root / "stages" / "01-plan" / "findings.json").read_text(encoding="utf-8")
    )
    assert any(finding["target_id"] == "deploy" for finding in findings)
    assert package.generated_stages == ["01-plan"]


def test_generate_scaffold_package_uses_prior_plan_and_writes_manifest_proposals(
    tmp_path: Path,
) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    graph = _mixed_graph(bundle_root)

    package = generate_approval_package(
        bundle_root=bundle_root,
        graph=graph,
        requested_stages=["01-plan", "02-scaffold"],
        reviewer="Daniela",
    )

    package_root = bundle_root / ".uiplan" / "generation" / "packages" / package.package_id
    scaffold_stage = package_root / "stages" / "02-scaffold"
    proposals = sorted(path.name for path in (scaffold_stage / "proposals").glob("*"))

    assert "projects-customer-intake-manifest.json" in proposals
    manifest = json.loads(
        (scaffold_stage / "proposals" / "projects-customer-intake-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["package_name"] == "UiPlan.CustomerIntake"
    assert manifest["project_types"] == ["docs", "coded-agent"]
    assert manifest["direct_write"] is False
    assert manifest["external_mutation"] is False
    scaffold_target = bundle_root / "projects" / "CustomerIntake" / "project.manifest.json"
    assert not scaffold_target.exists()
    state = json.loads((package_root / "approval-state.json").read_text(encoding="utf-8"))
    assert state["stage_statuses"]["02-scaffold"] == "ready_for_review"


def test_scaffold_stage_rejects_when_plan_not_requested_and_no_approved_prior_package(
    tmp_path: Path,
) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    with pytest.raises(
        ValueError,
        match=(
            "02-scaffold requires 01-plan in the request or an approved prior Plan package "
            "with matching graph lineage"
        ),
    ):
        generate_approval_package(
            bundle_root=bundle_root,
            graph=_mixed_graph(bundle_root),
            requested_stages=["02-scaffold"],
            reviewer="Daniela",
        )


def test_scaffold_stage_succeeds_with_approved_prior_plan_package(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    graph = _mixed_graph(bundle_root)

    prior_plan_package = generate_approval_package(
        bundle_root=bundle_root,
        graph=graph,
        requested_stages=["01-plan"],
        reviewer="Daniela",
    )
    prior_plan_root = bundle_root / ".uiplan" / "generation" / "packages" / prior_plan_package.package_id
    prior_state_path = prior_plan_root / "approval-state.json"
    prior_state = json.loads(prior_state_path.read_text(encoding="utf-8"))
    prior_state["stage_statuses"]["01-plan"] = "approved"
    prior_state_path.write_text(json.dumps(prior_state, indent=2) + "\n", encoding="utf-8")

    scaffold_package = generate_approval_package(
        bundle_root=bundle_root,
        graph=graph,
        requested_stages=["02-scaffold"],
        reviewer="Daniela",
    )

    scaffold_root = bundle_root / ".uiplan" / "generation" / "packages" / scaffold_package.package_id
    scaffold_stage = scaffold_root / "stages" / "02-scaffold"
    assert scaffold_package.generated_stages == ["02-scaffold"]
    assert (scaffold_stage / "proposals" / "projects-customer-intake-manifest.json").exists()
    assert not (bundle_root / "projects" / "CustomerIntake" / "project.manifest.json").exists()
    scaffold_state = json.loads((scaffold_root / "approval-state.json").read_text(encoding="utf-8"))
    assert scaffold_state["stage_statuses"]["01-plan"] == "not_started"
    assert scaffold_state["stage_statuses"]["02-scaffold"] == "ready_for_review"


def test_scaffold_stage_rejects_approved_prior_plan_with_different_graph_lineage(
    tmp_path: Path,
) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    prior_graph = _mixed_graph(bundle_root)
    prior_graph.graph_id = "graph-prior"
    request_graph = _mixed_graph(bundle_root)
    request_graph.graph_id = "graph-request"

    prior_plan_package = generate_approval_package(
        bundle_root=bundle_root,
        graph=prior_graph,
        requested_stages=["01-plan"],
        reviewer="Daniela",
    )
    prior_plan_root = bundle_root / ".uiplan" / "generation" / "packages" / prior_plan_package.package_id
    prior_state_path = prior_plan_root / "approval-state.json"
    prior_state = json.loads(prior_state_path.read_text(encoding="utf-8"))
    prior_state["stage_statuses"]["01-plan"] = "approved"
    prior_state_path.write_text(json.dumps(prior_state, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=(
            "02-scaffold requires 01-plan in the request or an approved prior Plan package "
            "with matching graph lineage"
        ),
    ):
        generate_approval_package(
            bundle_root=bundle_root,
            graph=request_graph,
            requested_stages=["02-scaffold"],
            reviewer="Daniela",
        )


def test_scaffold_stage_without_eligible_nodes_keeps_not_started_status(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    graph = _mixed_graph(bundle_root)
    for node in graph.nodes:
        node.role = "deployment_gate"
        node.project_types = []

    package = generate_approval_package(
        bundle_root=bundle_root,
        graph=graph,
        requested_stages=["01-plan", "02-scaffold"],
        reviewer="Daniela",
    )

    package_root = bundle_root / ".uiplan" / "generation" / "packages" / package.package_id
    state = json.loads((package_root / "approval-state.json").read_text(encoding="utf-8"))
    assert state["stage_statuses"]["02-scaffold"] == "not_started"
    stage_manifest = json.loads(
        (package_root / "stages" / "02-scaffold" / "stage.manifest.json").read_text(encoding="utf-8")
    )
    assert stage_manifest["generated_files"] == []
    assert stage_manifest["required_approvals"] == []
    assert stage_manifest["apply_eligible"] is False


def test_code_tests_and_validation_generation_are_deferred(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    with pytest.raises(ValueError, match="stage generation is deferred: 03-code"):
        generate_approval_package(
            bundle_root=bundle_root,
            graph=_mixed_graph(bundle_root),
            requested_stages=["03-code"],
            reviewer="Daniela",
        )
