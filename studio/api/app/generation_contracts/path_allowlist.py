from __future__ import annotations

from pathlib import Path

SECRET_NAME_FRAGMENTS = ("secret", "credential", "token", "private-key", "private_key")
BLOCKED_SEGMENTS = {".git", "skills", "node_modules", "dist", "build", "__pycache__", ".vite"}
NORMALIZED_BLOCKED_SEGMENTS = {segment.lower() for segment in BLOCKED_SEGMENTS}
PLAN_PREFIXES = ("docs/", ".cursor/plans/")
SCAFFOLD_PREFIXES = ("projects/", "apps/", "services/", "studio/", "packages/", "libs/")
SUPPORTED_STAGE_IDS = {"01-plan", "02-scaffold"}


def validate_target_path(
    *,
    bundle_root: Path,
    target_path: str,
    stage_id: str,
    file_kind: str,
) -> Path:
    _ = file_kind
    raw = target_path.strip().replace("\\", "/")
    if not raw:
        raise ValueError("target path is required")
    if Path(raw).is_absolute():
        raise ValueError("absolute proposal paths are not allowed")
    if raw == ".env" or raw.endswith("/.env") or any(
        fragment in raw.lower() for fragment in SECRET_NAME_FRAGMENTS
    ):
        raise ValueError("secret-like proposal paths are not allowed")
    parts = [part for part in raw.split("/") if part]
    if ".." in parts:
        raise ValueError("path traversal is not allowed")
    normalized_parts = [part.lower() for part in parts]
    if any(part in NORMALIZED_BLOCKED_SEGMENTS for part in normalized_parts):
        raise ValueError("proposal path targets a blocked directory")
    if stage_id not in SUPPORTED_STAGE_IDS:
        raise ValueError(f"unsupported stage id: {stage_id}")
    if stage_id == "01-plan" and not raw.startswith(PLAN_PREFIXES):
        raise ValueError("Plan proposals must target documentation paths")
    if stage_id == "02-scaffold" and not raw.startswith(SCAFFOLD_PREFIXES):
        raise ValueError("Scaffold proposals must target explicit project or manifest paths")
    resolved_root = bundle_root.resolve()
    resolved_target = (resolved_root / raw).resolve()
    try:
        resolved_target.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("proposal path resolves outside the bundle root") from exc
    return resolved_target
