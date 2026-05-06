from dataclasses import dataclass
from pathlib import Path

REQUIRED_DOCS = ("spec.md", "plan.md", "tasks.md")


@dataclass(frozen=True)
class LoadedBundle:
    slug: str
    status: str
    root: Path
    documents: dict[str, str]


def _parse_meta(meta_path: Path) -> dict[str, str]:
    raw = meta_path.read_text(encoding="utf-8")
    parsed: dict[str, str] = {}
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        parsed[key.strip()] = value.strip().strip('"').strip("'")
    return parsed


def load_bundle(bundle_root: Path) -> LoadedBundle:
    root = bundle_root.resolve()
    meta = _parse_meta(root / ".meta.yaml")
    documents = {name: (root / name).read_text(encoding="utf-8") for name in REQUIRED_DOCS}
    return LoadedBundle(
        slug=meta.get("slug", root.name),
        status=meta.get("status", "draft"),
        root=root,
        documents=documents,
    )
