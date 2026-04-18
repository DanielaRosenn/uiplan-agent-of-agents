"""Publish UiPath Claude Code docs to the Cato RPA Confluence space.

Reads Markdown drafts under ``docs/wiki/`` and creates or updates two Confluence
pages via the Atlassian REST API v2. Idempotent: page IDs are persisted to
``docs/wiki/.confluence-ids.json`` so subsequent runs update in place.

Auth via basic auth with an Atlassian API token. See ``.env.example`` for the
required environment variables.

Usage::

    python scripts/publish_confluence.py --dry-run
    python scripts/publish_confluence.py

"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = REPO_ROOT / "docs" / "wiki"
ID_MAP_PATH = WIKI_DIR / ".confluence-ids.json"


@dataclass(frozen=True)
class Page:
    key: str
    title: str
    source: Path


PAGES: tuple[Page, ...] = (
    Page(
        key="overview",
        title="UiPath Claude Code - Overview",
        source=WIKI_DIR / "confluence-overview.md",
    ),
    Page(
        key="quickstart",
        title="UiPath Claude Code - Quickstart for developers",
        source=WIKI_DIR / "confluence-quickstart.md",
    ),
)


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"Missing required environment variable: {name}. See .env.example."
        )
    return value


def _load_id_map() -> dict[str, str]:
    if not ID_MAP_PATH.exists():
        return {}
    try:
        return json.loads(ID_MAP_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_id_map(ids: dict[str, str]) -> None:
    ID_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    ID_MAP_PATH.write_text(
        json.dumps(ids, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _markdown_to_storage(markdown: str) -> str:
    """Minimal Markdown -> Confluence storage-format converter.

    Handles headings (h1-h3), paragraphs, and fenced code blocks. Swap in a
    fuller renderer (e.g. ``md2cf``) if richer Markdown is needed.
    """
    lines = markdown.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    in_code = False
    for raw in lines:
        if raw.startswith("```"):
            if in_code:
                out.append("]]></ac:plain-text-body></ac:structured-macro>")
                in_code = False
            else:
                out.append(
                    '<ac:structured-macro ac:name="code"><ac:plain-text-body><![CDATA['
                )
                in_code = True
            continue
        if in_code:
            out.append(raw)
            continue
        if raw.startswith("# "):
            out.append(f"<h1>{_html_escape(raw[2:])}</h1>")
        elif raw.startswith("## "):
            out.append(f"<h2>{_html_escape(raw[3:])}</h2>")
        elif raw.startswith("### "):
            out.append(f"<h3>{_html_escape(raw[4:])}</h3>")
        elif raw.strip() == "":
            out.append("")
        else:
            out.append(f"<p>{_html_escape(raw)}</p>")
    if in_code:
        out.append("]]></ac:plain-text-body></ac:structured-macro>")
    return "\n".join(out)


def _html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _build_client(base_url: str, email: str, token: str) -> httpx.Client:
    return httpx.Client(
        base_url=base_url.rstrip("/"),
        auth=(email, token),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )


def _resolve_space_id(client: httpx.Client, space_key: str) -> str:
    resp = client.get("/wiki/api/v2/spaces", params={"keys": space_key})
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        raise SystemExit(f"Confluence space not found: key={space_key}")
    return str(results[0]["id"])


def _get_current_version(client: httpx.Client, page_id: str) -> int:
    resp = client.get(f"/wiki/api/v2/pages/{page_id}")
    resp.raise_for_status()
    return int(resp.json().get("version", {}).get("number", 1))


def _create_page(
    client: httpx.Client,
    *,
    space_id: str,
    parent_id: str | None,
    title: str,
    storage: str,
    dry_run: bool,
) -> str:
    payload: dict[str, Any] = {
        "spaceId": space_id,
        "status": "current",
        "title": title,
        "body": {"representation": "storage", "value": storage},
    }
    if parent_id:
        payload["parentId"] = parent_id
    if dry_run:
        print(f"[dry-run] CREATE '{title}' payload keys: {sorted(payload)}")
        return "<dry-run-id>"
    resp = client.post("/wiki/api/v2/pages", json=payload)
    resp.raise_for_status()
    return str(resp.json()["id"])


def _update_page(
    client: httpx.Client,
    *,
    page_id: str,
    title: str,
    storage: str,
    dry_run: bool,
) -> str:
    if dry_run:
        print(f"[dry-run] UPDATE id={page_id} title='{title}'")
        return page_id
    current_version = _get_current_version(client, page_id)
    payload = {
        "id": page_id,
        "status": "current",
        "title": title,
        "body": {"representation": "storage", "value": storage},
        "version": {"number": current_version + 1},
    }
    resp = client.put(f"/wiki/api/v2/pages/{page_id}", json=payload)
    resp.raise_for_status()
    return str(resp.json()["id"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be sent without calling the Confluence API.",
    )
    args = parser.parse_args(argv)

    base_url = _require_env("ATLASSIAN_BASE_URL")
    email = _require_env("ATLASSIAN_EMAIL")
    token = _require_env("ATLASSIAN_API_TOKEN")
    space_key = os.environ.get("CONFLUENCE_SPACE_KEY", "RPA")
    parent_id = os.environ.get("CONFLUENCE_PARENT_PAGE_ID") or None

    for page in PAGES:
        if not page.source.exists():
            raise SystemExit(f"Source markdown missing: {page.source}")

    ids = _load_id_map()

    with _build_client(base_url, email, token) as client:
        space_id = (
            "<dry-run-space-id>"
            if args.dry_run
            else _resolve_space_id(client, space_key)
        )
        for page in PAGES:
            markdown = page.source.read_text(encoding="utf-8")
            storage = _markdown_to_storage(markdown)
            existing_id = ids.get(page.key)
            if existing_id:
                new_id = _update_page(
                    client,
                    page_id=existing_id,
                    title=page.title,
                    storage=storage,
                    dry_run=args.dry_run,
                )
            else:
                new_id = _create_page(
                    client,
                    space_id=space_id,
                    parent_id=parent_id,
                    title=page.title,
                    storage=storage,
                    dry_run=args.dry_run,
                )
            ids[page.key] = new_id
            print(f"[{'dry-run' if args.dry_run else 'ok'}] {page.key}: id={new_id}")

    if not args.dry_run:
        _save_id_map(ids)
        print(f"Wrote {ID_MAP_PATH.relative_to(REPO_ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
