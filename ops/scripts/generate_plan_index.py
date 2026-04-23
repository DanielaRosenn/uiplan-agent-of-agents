#!/usr/bin/env python3
"""Rebuild docs/plans/README.md from plan markdown front matter.

Run from repo root:
  python ops/scripts/generate_plan_index.py

Scans docs/plans/*.md excluding _TEMPLATE.md and README.md.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parents[2]
PLANS_DIR = REPO_ROOT / "docs" / "plans"
README_PATH = PLANS_DIR / "README.md"
SKIP = {"_TEMPLATE.md", "README.md"}
UIPLAN_META = ".meta.yaml"


def _split_front_matter(text: str) -> tuple[dict, str] | None:
    if not text.startswith("---"):
        return None
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return None
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(meta, dict):
        return None
    body = text[m.end() :]
    return meta, body


def collect_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not PLANS_DIR.is_dir():
        return rows
    for path in sorted(PLANS_DIR.glob("*.md")):
        if path.name in SKIP:
            continue
        raw = path.read_text(encoding="utf-8")
        parsed = _split_front_matter(raw)
        if not parsed:
            rows.append(
                {
                    "file": path.name,
                    "slug": "",
                    "title": path.stem,
                    "date": "",
                    "status": "",
                    "owner": "",
                    "linked_pdd": "",
                }
            )
            continue
        meta, _ = parsed
        rows.append(
            {
                "file": path.name,
                "slug": str(meta.get("slug", "")),
                "title": str(meta.get("title", path.stem)),
                "date": str(meta.get("date", "")),
                "status": str(meta.get("status", "")),
                "owner": str(meta.get("owner", "")),
                "linked_pdd": str(meta.get("linked_pdd", "") or ""),
            }
        )
    for sub in sorted(PLANS_DIR.iterdir(), reverse=True):
        if not sub.is_dir() or sub.name.startswith("."):
            continue
        meta_path = sub / UIPLAN_META
        if not meta_path.is_file():
            continue
        try:
            meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        if str(meta.get("plan_kind", "")) != "uiplan":
            continue
        link = f"{sub.name}/spec.md"
        rows.append(
            {
                "file": link,
                "slug": str(meta.get("slug", "")),
                "title": str(meta.get("title", sub.name)),
                "date": str(meta.get("date", "")),
                "status": str(meta.get("status", "")),
                "owner": str(meta.get("owner", "")),
                "linked_pdd": str(meta.get("linked_pdd", "") or ""),
            }
        )
    rows.sort(key=lambda r: (r["date"], r["file"]), reverse=True)
    return rows


def render_readme(rows: list[dict[str, str]]) -> str:
    lines = [
        "# Implementation plans",
        "",
        "Git-tracked plans for multi-step work in this repo. Template: "
        "[_TEMPLATE.md](_TEMPLATE.md). Process context: "
        "[../PDD_LIFECYCLE.md](../PDD_LIFECYCLE.md).",
        "",
        "To refresh this table after adding or editing a plan:",
        "",
        "```bash",
        "python ops/scripts/generate_plan_index.py",
        "```",
        "",
        "| File | Date | Status | Slug | Title | Owner | Linked PDD |",
        "|------|------|--------|------|-------|-------|------------|",
    ]
    for r in rows:
        pdd = r["linked_pdd"].replace("|", "\\|")
        lines.append(
            f"| [{r['file']}]({r['file']}) | {r['date']} | {r['status']} | "
            f"`{r['slug']}` | {r['title']} | {r['owner']} | {pdd} |"
        )
    if len(rows) == 0:
        lines.append("| *(no plans yet)* | | | | | | |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    text = render_readme(collect_rows())
    README_PATH.write_text(text, encoding="utf-8")
    print(f"Wrote {README_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
