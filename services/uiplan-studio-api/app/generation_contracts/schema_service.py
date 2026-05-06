from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"


def load_contract_schemas() -> dict[str, dict[str, Any]]:
    schemas: dict[str, dict[str, Any]] = {}
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schemas[path.name] = json.loads(path.read_text(encoding="utf-8"))
    if len(schemas) != 5:
        raise RuntimeError(f"expected 5 contract schemas in {SCHEMA_DIR}, found {len(schemas)}")
    return schemas


def copy_contract_schemas(bundle_root: Path) -> list[Path]:
    """Copy bundled contract schemas into a pre-validated bundle root directory.

    This utility is intentionally low-level and expects `bundle_root` to already
    be validated by callers as a project bundle location.
    """
    if not bundle_root.exists() or not bundle_root.is_dir():
        raise ValueError(f"bundle_root must be an existing directory: {bundle_root}")

    schema_target = bundle_root / ".uiplan" / "generation" / "schemas"
    schema_target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, payload in load_contract_schemas().items():
        target = schema_target / name
        target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(target)
    return written
