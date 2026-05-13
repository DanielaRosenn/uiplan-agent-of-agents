from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from app.generation_contracts.approval_state import create_initial_approval_state
from app.generation_contracts.constants import STAGE_IDS
from app.generation_contracts.models import (
    ApprovalPackageManifest,
    ApprovalState,
    GenerationGraph,
    StageManifest,
)
from app.generation_contracts.schema_service import copy_contract_schemas

PACKAGE_STAGE_DIRS = {
    "01-plan": ("proposals", "diffs"),
    "02-scaffold": ("proposals", "diffs"),
}


@dataclass(frozen=True)
class PackageLayout:
    package_root: Path
    manifest: ApprovalPackageManifest
    approval_state: ApprovalState


def _stable_json_hash(payload: Any) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(path.parent),
        delete=False,
        newline="\n",
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


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


def create_package_layout(
    *,
    bundle_root: Path,
    package_id: str,
    graph: GenerationGraph,
    context_manifest: dict[str, Any],
    stages: list[StageManifest],
    proposal_hashes: dict[str, str],
) -> PackageLayout:
    copy_contract_schemas(bundle_root)
    packages_root = bundle_root / ".uiplan" / "generation" / "packages"
    package_root = packages_root / package_id
    package_root.mkdir(parents=True, exist_ok=True)

    generated_stage_ids = [stage.stage_id for stage in stages]
    manifest = ApprovalPackageManifest(
        package_id=package_id,
        graph_id=graph.graph_id,
        bundle_root=str(bundle_root),
        generated_stages=generated_stage_ids,
        safety_policy={"direct_writes": False, "external_mutation": False},
    )

    proposal_ids: list[str] = list(proposal_hashes)
    context_manifest_hash = context_manifest.get("context_manifest_hash")
    if not context_manifest_hash or not isinstance(context_manifest_hash, str):
        raise ValueError("context_manifest_hash is required in context_manifest")
    source_graph_hash = context_manifest.get("source_graph_hash")
    if not source_graph_hash or not isinstance(source_graph_hash, str):
        source_graph_hash = _stable_json_hash(graph.model_dump(mode="json"))
    approval_state = create_initial_approval_state(
        package_id=package_id,
        stage_ids=STAGE_IDS,
        proposal_ids=proposal_ids,
        source_graph_hash=source_graph_hash,
        context_manifest_hash=context_manifest_hash,
        proposal_hashes=proposal_hashes,
        ready_stage_ids=generated_stage_ids,
    )
    for stage in stages:
        approval_state.stage_statuses[stage.stage_id] = stage.status
    if stages:
        approval_state.current_stage = stages[0].stage_id

    _write_json_atomic(package_root / "manifest.json", manifest.model_dump(mode="json"))
    _write_json_atomic(package_root / "graph.snapshot.json", graph.model_dump(mode="json"))
    _write_json_atomic(package_root / "context.manifest.json", context_manifest)
    _write_json_atomic(
        package_root / "approval-state.json",
        approval_state.model_dump(mode="json"),
    )

    stage_root = package_root / "stages"
    for stage in stages:
        if stage.stage_id not in PACKAGE_STAGE_DIRS:
            continue
        current_stage_root = stage_root / stage.stage_id
        for subdir in PACKAGE_STAGE_DIRS[stage.stage_id]:
            (current_stage_root / subdir).mkdir(parents=True, exist_ok=True)
        _write_json_atomic(
            current_stage_root / "stage.manifest.json",
            stage.model_dump(mode="json"),
        )
        _write_json_atomic(current_stage_root / "findings.json", [])
        _write_text_atomic(current_stage_root / "reviewer-notes.md", "")

    return PackageLayout(
        package_root=package_root,
        manifest=manifest,
        approval_state=approval_state,
    )


def write_package_state(
    package_root: Path,
    state: ApprovalState,
    *,
    expected_updated_at: str | None = None,
) -> None:
    approval_state_path = package_root / "approval-state.json"
    if expected_updated_at is not None and approval_state_path.exists():
        current_state = read_package_state(package_root)
        if current_state.updated_at != expected_updated_at:
            raise ValueError(
                "stale approval state write: expected updated_at "
                f"{expected_updated_at}, found {current_state.updated_at}"
            )
    _write_json_atomic(approval_state_path, state.model_dump(mode="json"))


def read_package_state(package_root: Path) -> ApprovalState:
    payload = json.loads((package_root / "approval-state.json").read_text(encoding="utf-8"))
    return ApprovalState.model_validate(payload)


def list_packages(bundle_root: Path) -> list[ApprovalPackageManifest]:
    packages_root = bundle_root / ".uiplan" / "generation" / "packages"
    if not packages_root.exists():
        return []
    manifests: list[ApprovalPackageManifest] = []
    for manifest_path in sorted(packages_root.glob("*/manifest.json")):
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifests.append(ApprovalPackageManifest.model_validate(payload))
    return manifests
