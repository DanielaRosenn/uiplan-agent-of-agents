"""Helpers for folder-shaped UiPlan bundles (spec.md + plan.md + tasks.md + .meta.yaml)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

UIPLAN_META = ".meta.yaml"
_PLAN_KIND_UIPLAN = "uiplan"
_FOLDER_NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9_-]+$")
_FILENAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9_-]+\.md$")
_SKIP_LIST = frozenset({"_TEMPLATE.md", "README.md"})
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,120}$")


def _safe_plan_file(plans_dir: Path, basename: str) -> Path:
    name = Path(basename).name
    if name in _SKIP_LIST or name.startswith("."):
        raise ValueError(f"refusing to write reserved or hidden name: {name}")
    if ".." in name or "/" in name or "\\" in name:
        raise ValueError("filename must be a plain basename")
    if not _FILENAME_RE.match(name):
        raise ValueError(
            "filename must match YYYY-MM-DD-slug.md (slug: lowercase letters, digits, hyphen, underscore)"
        )
    path = (plans_dir / name).resolve()
    try:
        path.relative_to(plans_dir.resolve())
    except ValueError as exc:
        raise ValueError(f"path escapes {plans_dir}") from exc
    return path


@dataclass(frozen=True)
class ResolvedPlan:
    """A plan is either a legacy single markdown file or a UiPlan directory."""

    path: Path
    kind: Literal["file", "folder"]

    @property
    def is_folder(self) -> bool:
        return self.kind == "folder"


def is_folder_plan(path: Path) -> bool:
    return path.is_dir() and (path / UIPLAN_META).is_file()


def load_folder_meta(folder: Path) -> dict[str, Any]:
    p = folder / UIPLAN_META
    if not p.is_file():
        raise FileNotFoundError(f"missing {UIPLAN_META} under {folder}")
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{UIPLAN_META} must be a YAML mapping")
    return data


def save_folder_meta(folder: Path, meta: dict[str, Any]) -> None:
    dumped = yaml.safe_dump(
        meta,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    ).rstrip()
    (folder / UIPLAN_META).write_text(dumped + "\n", encoding="utf-8")


def _safe_folder_basename(name: str, plans_parent: Path) -> Path:
    base = Path(name).name
    if ".." in base or "/" in base or "\\" in base:
        raise ValueError("folder name must be a plain basename")
    if not _FOLDER_NAME_RE.match(base):
        raise ValueError(
            "folder name must match YYYY-MM-DD-slug (slug: lowercase letters, digits, hyphen, underscore)"
        )
    out = (plans_parent / base).resolve()
    try:
        out.relative_to(plans_parent.resolve())
    except ValueError as exc:
        raise ValueError(f"path escapes {plans_parent}") from exc
    return out


def _slug_from_folder_name(dirname: str) -> str | None:
    m = re.match(r"^\d{4}-\d{2}-\d{2}-(.+)$", dirname)
    return m.group(1) if m else None


def resolve_plan_path(
    plans_dir: Path,
    filename: str | None,
    slug: str | None,
    *,
    extra_dirs: list[Path] | None = None,
) -> ResolvedPlan:
    """Resolve a plan to a file path or a UiPlan folder path."""
    search_dirs: list[Path] = [plans_dir]
    if extra_dirs:
        for d in extra_dirs:
            if d not in search_dirs:
                search_dirs.append(d)

    if filename:
        fn = Path(filename.strip()).name
        for d in search_dirs:
            if not fn.endswith(".md"):
                try:
                    cand = _safe_folder_basename(fn, d)
                except ValueError:
                    continue
                if cand.is_dir() and is_folder_plan(cand):
                    return ResolvedPlan(cand, "folder")
            else:
                try:
                    p = _safe_plan_file(d, fn)
                except ValueError:
                    continue
                if p.is_file():
                    return ResolvedPlan(p, "file")
        if fn.endswith(".md"):
            return ResolvedPlan(_safe_plan_file(search_dirs[0], fn), "file")

    if not slug:
        raise ValueError("provide filename or slug")
    if not _SLUG_RE.match(slug):
        raise ValueError("invalid slug")

    matches: list[ResolvedPlan] = []
    for d in search_dirs:
        if not d.is_dir():
            continue
        # Legacy markdown
        for p in d.glob("*.md"):
            if p.name in _SKIP_LIST or p.name.startswith("_"):
                continue
            try:
                raw = p.read_text(encoding="utf-8")
                if not raw.lstrip().startswith("---"):
                    continue
                m = re.match(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n", raw, re.DOTALL)
                if not m:
                    continue
                meta = yaml.safe_load(m.group(1))
                if isinstance(meta, dict) and str(meta.get("slug", "")) == slug:
                    matches.append(ResolvedPlan(p, "file"))
            except Exception:
                continue
        # Folder UiPlans
        for sub in d.iterdir():
            if not sub.is_dir() or sub.name.startswith("."):
                continue
            if not is_folder_plan(sub):
                continue
            try:
                meta = load_folder_meta(sub)
            except Exception:
                continue
            if str(meta.get("slug", "")) == slug:
                matches.append(ResolvedPlan(sub, "folder"))
            elif _slug_from_folder_name(sub.name) == slug:
                matches.append(ResolvedPlan(sub, "folder"))

    if not matches:
        raise FileNotFoundError(f"no plan with slug {slug!r}")
    if len(matches) > 1:
        names = ", ".join(sorted(str(x.path) for x in matches))
        raise ValueError(f"slug {slug!r} is ambiguous: {names}")
    return matches[0]


def read_plan_yaml_meta(resolved: ResolvedPlan) -> dict[str, Any]:
    if resolved.kind == "folder":
        return load_folder_meta(resolved.path)
    raw = resolved.path.read_text(encoding="utf-8")
    if not raw.lstrip().startswith("---"):
        raise ValueError("Plan must start with YAML front matter (---)")
    m = re.match(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n", raw, re.DOTALL)
    if not m:
        raise ValueError("Invalid front matter")
    meta = yaml.safe_load(m.group(1))
    if not isinstance(meta, dict):
        raise ValueError("Front matter must parse to a YAML mapping")
    return meta


def read_uiplan_files(resolved: ResolvedPlan) -> dict[str, str]:
    if resolved.kind != "folder":
        raise ValueError("not a folder plan")
    root = resolved.path
    out: dict[str, str] = {}
    for name in ("spec.md", "plan.md", "tasks.md"):
        p = root / name
        out[name] = p.read_text(encoding="utf-8") if p.is_file() else ""
    return out


def collect_folder_plan_entries(directory: Path, scope_label: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not directory.is_dir():
        return items
    for sub in sorted(directory.iterdir(), reverse=True):
        if not sub.is_dir() or sub.name.startswith("."):
            continue
        if not is_folder_plan(sub):
            continue
        try:
            meta = load_folder_meta(sub)
        except Exception:
            items.append(
                {
                    "file": f"{sub.name}/",
                    "scope": scope_label,
                    "plan_kind": _PLAN_KIND_UIPLAN,
                    "parse_error": True,
                }
            )
            continue
        if str(meta.get("plan_kind", "")) != _PLAN_KIND_UIPLAN:
            continue
        items.append(
            {
                "file": f"{sub.name}/",
                "scope": scope_label,
                "plan_kind": _PLAN_KIND_UIPLAN,
                "slug": meta.get("slug"),
                "title": meta.get("title"),
                "date": meta.get("date"),
                "status": meta.get("status"),
                "owner": meta.get("owner"),
                "project_type": meta.get("project_type"),
                "accepted_at": meta.get("accepted_at"),
                "published_at": meta.get("published_at"),
            }
        )
    return items
