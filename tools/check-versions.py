"""Verify that VERSION, the studio app, and the studio API are pinned together.

The repo declares its product version in three places (intentionally - each
ecosystem expects to find it in its own conventional file). They MUST agree.
This script is the single point of truth that catches drift.

Run via:

    python tools/check-versions.py

Exits non-zero with a diff-style report on any mismatch. Wired into the
`secret-scan.yml` GitHub Actions workflow so a PR that bumps one but
forgets the others fails CI.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def read_root_version() -> str:
    return (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()


def read_studio_app_version() -> str:
    pkg = json.loads(
        (REPO_ROOT / "studio" / "web" / "package.json").read_text(encoding="utf-8")
    )
    return str(pkg["version"])


def read_studio_api_version() -> str:
    text = (REPO_ROOT / "studio" / "api" / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    match = re.search(r"^version\s*=\s*\"([^\"]+)\"", text, re.MULTILINE)
    if match is None:
        raise SystemExit(
            "could not find `version = \"...\"` in studio/api/pyproject.toml"
        )
    return match.group(1)


def main() -> int:
    sources = {
        "VERSION": read_root_version(),
        "studio/web/package.json": read_studio_app_version(),
        "studio/api/pyproject.toml": read_studio_api_version(),
    }
    distinct = set(sources.values())
    if len(distinct) == 1:
        version = distinct.pop()
        print(f"[ok] all version sources agree: {version}")
        for path in sources:
            print(f"     - {path}")
        return 0

    print("[FAIL] version drift detected:")
    for path, version in sources.items():
        print(f"  {version!r:>12}  <-  {path}")
    print(
        "\nFix: bump all three to the same semver. The root VERSION file "
        "is the canonical source; sync the others to match it."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
