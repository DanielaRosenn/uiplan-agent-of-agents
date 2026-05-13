import json
from pathlib import Path

import pytest

from app.generation_contracts.models import (
    ApprovalPackageManifest,
    ApprovalState,
    GenerationGraph,
    StageManifest,
)
from app.generation_contracts.storage import (
    create_package_layout,
    list_packages,
    read_package_state,
    write_package_state,
)


def test_create_package_layout_writes_phase_zero_directories(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    graph = GenerationGraph(
        graph_id="graph-1",
        bundle_root=str(bundle_root),
        created_from="test",
    )

    layout = create_package_layout(
        bundle_root=bundle_root,
        package_id="pkg-1",
        graph=graph,
        context_manifest={"attachments": [], "context_manifest_hash": "context-hash"},
        stages=[
            StageManifest(
                stage_id="01-plan",
                status="ready_for_review",
                input_graph_hash="graph-hash",
                input_context_hash="context-hash",
            )
        ],
        proposal_hashes={"01-plan:plan-doc": "proposal-hash"},
    )

    package_root = bundle_root / ".uiplan" / "generation" / "packages" / "pkg-1"
    assert layout.package_root == package_root
    assert (package_root / "manifest.json").is_file()
    assert (package_root / "graph.snapshot.json").is_file()
    assert (package_root / "context.manifest.json").is_file()
    assert (package_root / "approval-state.json").is_file()
    assert (package_root / "stages" / "01-plan" / "proposals").is_dir()
    assert (package_root / "stages" / "01-plan" / "diffs").is_dir()
    assert not (package_root / "stages" / "03-code").exists()
    assert json.loads((package_root / "manifest.json").read_text())["package_id"] == "pkg-1"


def test_package_state_round_trip_persists_review_metadata(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    package_root = bundle_root / ".uiplan" / "generation" / "packages" / "pkg-1"
    package_root.mkdir(parents=True)
    state = ApprovalState(
        package_id="pkg-1",
        current_stage="01-plan",
        stage_statuses={"01-plan": "ready_for_review", "02-scaffold": "not_started"},
    )

    write_package_state(package_root, state)

    loaded = read_package_state(package_root)
    assert loaded.package_id == "pkg-1"
    assert loaded.stage_statuses["01-plan"] == "ready_for_review"


def test_list_packages_returns_manifest_summaries(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    package_root = bundle_root / ".uiplan" / "generation" / "packages" / "pkg-1"
    package_root.mkdir(parents=True)
    manifest = ApprovalPackageManifest(
        package_id="pkg-1",
        graph_id="graph-1",
        bundle_root=str(bundle_root),
        generated_stages=["01-plan"],
        safety_policy={"direct_writes": False, "external_mutation": False},
    )
    (package_root / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

    packages = list_packages(bundle_root)

    assert [package.package_id for package in packages] == ["pkg-1"]


def test_create_package_layout_requires_hashes_in_context_manifest(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    graph = GenerationGraph(
        graph_id="graph-1",
        bundle_root=str(bundle_root),
        created_from="test",
    )

    with pytest.raises(ValueError, match="context_manifest_hash is required"):
        create_package_layout(
            bundle_root=bundle_root,
            package_id="pkg-1",
            graph=graph,
            context_manifest={"attachments": []},
            stages=[
                StageManifest(
                    stage_id="01-plan",
                    status="ready_for_review",
                    input_graph_hash="graph-hash",
                    input_context_hash="context-hash",
                )
            ],
            proposal_hashes={"01-plan:plan-doc": "proposal-hash"},
        )


def test_create_package_layout_derives_source_graph_hash_when_missing(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    graph = GenerationGraph(
        graph_id="graph-1",
        bundle_root=str(bundle_root),
        created_from="test",
    )

    layout = create_package_layout(
        bundle_root=bundle_root,
        package_id="pkg-1",
        graph=graph,
        context_manifest={"context_manifest_hash": "context-hash"},
        stages=[
            StageManifest(
                stage_id="01-plan",
                status="ready_for_review",
                input_graph_hash="graph-hash",
                input_context_hash="context-hash",
            )
        ],
        proposal_hashes={"01-plan:plan-doc": "proposal-hash"},
    )

    proposal = layout.approval_state.proposals["01-plan:plan-doc"]
    assert proposal.source_graph_hash
    assert proposal.source_graph_hash != "graph-snapshot"


def test_write_package_state_rejects_stale_expected_updated_at(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    package_root = bundle_root / ".uiplan" / "generation" / "packages" / "pkg-1"
    package_root.mkdir(parents=True)
    state = ApprovalState(
        package_id="pkg-1",
        current_stage="01-plan",
        stage_statuses={"01-plan": "ready_for_review", "02-scaffold": "not_started"},
    )
    write_package_state(package_root, state)

    stale_state = state.model_copy(deep=True)
    stale_state.current_stage = "02-scaffold"

    with pytest.raises(ValueError, match="stale approval state write"):
        write_package_state(
            package_root,
            stale_state,
            expected_updated_at="2001-01-01T00:00:00Z",
        )


def test_write_package_state_accepts_matching_expected_updated_at(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    package_root = bundle_root / ".uiplan" / "generation" / "packages" / "pkg-1"
    package_root.mkdir(parents=True)
    state = ApprovalState(
        package_id="pkg-1",
        current_stage="01-plan",
        stage_statuses={"01-plan": "ready_for_review", "02-scaffold": "not_started"},
    )
    write_package_state(package_root, state)
    loaded = read_package_state(package_root)

    next_state = loaded.model_copy(deep=True)
    next_state.current_stage = "02-scaffold"

    write_package_state(
        package_root,
        next_state,
        expected_updated_at=loaded.updated_at,
    )
    reloaded = read_package_state(package_root)
    assert reloaded.current_stage == "02-scaffold"
