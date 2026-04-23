"""Publish UiPath Claude Code docs to the Cato RPA Confluence space via UiPath.

Authentication and egress flow through the UiPath ``uip`` CLI, which talks to
Integration Service on our behalf:

    Python publisher
        -> uip is resources execute create/update ...
            -> UiPath Integration Service (connection id below)
                -> Confluence REST API v2

Auth is whatever ``uip login`` has cached (``%USERPROFILE%/.uipath``). No
Atlassian token, no UiPath PAT/client secret is required in env.

Idempotency: page IDs are persisted to ``docs/wiki/.confluence-ids.json`` so
subsequent runs update in place.

Usage::

    python ops/scripts/publish_confluence.py --dry-run
    python ops/scripts/publish_confluence.py

"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
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


CONNECTOR_KEY = "uipath-atlassian-confluence"


class UipCliClient:
    """Thin wrapper around the ``uip`` CLI's Integration Service commands.

    Auth is whatever ``uip login`` has cached. The tenant with SSL inspection
    requires ``NODE_TLS_REJECT_UNAUTHORIZED=0`` to be set in the environment,
    which the caller is expected to arrange (see ``publish-confluence.ps1``).
    """

    def __init__(self, *, connection_id: str) -> None:
        self._connection_id = connection_id
        # Invoke the CLI's JS entry directly via node to avoid cmd.exe shell
        # metachar mangling on Windows (&, <, >, | in --body JSON).
        node = shutil.which("node") or "node"
        npm_root = Path(os.environ.get("APPDATA", "")) / "npm"
        js_entry = npm_root / "node_modules" / "@uipath" / "cli" / "dist" / "index.js"
        if js_entry.exists():
            self._cmd_prefix: list[str] = [node, str(js_entry)]
        else:
            self._cmd_prefix = [shutil.which("uip") or "uip"]

    def _run(self, args: list[str], *, body: dict[str, Any] | None = None) -> dict[str, Any]:
        cmd = [*self._cmd_prefix, *args, "--output", "json"]
        if body is not None:
            cmd.extend(["--body", json.dumps(body)])
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )
        stdout = (result.stdout or "").strip()
        if not stdout:
            raise SystemExit(
                f"uip returned no output (exit={result.returncode}). stderr:\n{result.stderr}"
            )
        # The CLI sometimes emits warnings before the JSON payload; take the
        # last JSON object in stdout.
        payload = _extract_last_json(stdout)
        if payload.get("Result") != "Success":
            raise SystemExit(
                f"uip {' '.join(args)} failed: {json.dumps(payload)[:800]}"
            )
        return payload.get("Data", {})

    def list_records(
        self, object_name: str, *, query: dict[str, str] | None = None
    ) -> list[dict[str, Any]]:
        args = [
            "is", "resources", "execute", "list",
            CONNECTOR_KEY, object_name,
            "--connection-id", self._connection_id,
        ]
        if query:
            args += ["--query", "&".join(f"{k}={v}" for k, v in query.items())]
        data = self._run(args)
        return data if isinstance(data, list) else data.get("results") or data.get("items") or []

    def create_record(
        self, object_name: str, body: dict[str, Any], *, query: dict[str, str] | None = None
    ) -> dict[str, Any]:
        args = [
            "is", "resources", "execute", "create",
            CONNECTOR_KEY, object_name,
            "--connection-id", self._connection_id,
        ]
        if query:
            args += ["--query", "&".join(f"{k}={v}" for k, v in query.items())]
        return self._run(args, body=body)

    def update_record(
        self, object_name: str, record_id: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        args = [
            "is", "resources", "execute", "update",
            CONNECTOR_KEY, object_name,
            "--connection-id", self._connection_id,
            "--id", record_id,
        ]
        return self._run(args, body=body)


def _extract_last_json(text: str) -> dict[str, Any]:
    """Find the last top-level JSON object in the given text."""
    depth = 0
    start = -1
    last: tuple[int, int] | None = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                last = (start, i + 1)
    if last is None:
        raise SystemExit(f"No JSON object found in uip output:\n{text[:800]}")
    return json.loads(text[last[0]:last[1]])


def _resolve_space_id(client: UipCliClient, space_key: str, *, dry_run: bool) -> str:
    if dry_run:
        return "<dry-run-space-id>"
    records = client.list_records("spaces_v2", query={"keys": space_key})
    for rec in records:
        if rec.get("key") == space_key:
            return str(rec["id"])
    raise SystemExit(f"Confluence space not found: key={space_key}")


def _create_page(
    client: UipCliClient,
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
        print(f"[dry-run] create page title={title!r} space={space_id}")
        return "<dry-run-id>"
    data = client.create_record("pages", payload, query={"space_type": "/spaces_v2"})
    return str(data["id"])


def _update_page(
    client: UipCliClient,
    *,
    page_id: str,
    title: str,
    storage: str,
    dry_run: bool,
) -> str:
    if dry_run:
        print(f"[dry-run] update page id={page_id} title={title!r}")
        return page_id
    payload = {
        "id": page_id,
        "status": "current",
        "title": title,
        "body": {"representation": "storage", "value": storage},
    }
    data = client.update_record("pages", page_id, payload)
    return str(data.get("id", page_id))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be sent without calling UiPath or Confluence.",
    )
    args = parser.parse_args(argv)

    connection_id = os.environ.get(
        "UIPATH_CONFLUENCE_CONNECTION_ID"
    ) or os.environ.get("UIPATH_ATLASSIAN_CONNECTION_ID") or _require_env(
        "UIPATH_IS_CONFLUENCE_CONNECTION_ID"
    )
    space_key = os.environ.get("CONFLUENCE_SPACE_KEY", "RPA")
    parent_id = os.environ.get("CONFLUENCE_PARENT_PAGE_ID") or None

    for page in PAGES:
        if not page.source.exists():
            raise SystemExit(f"Source markdown missing: {page.source}")

    ids = _load_id_map()

    client = UipCliClient(connection_id=connection_id)
    space_id = _resolve_space_id(client, space_key, dry_run=args.dry_run)
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
