"""Append-only per-project BUILD_LOG.md writer.

Every notable agent or CLI action records a Markdown event so that auditors and
future builders can reconstruct exactly how a UiPath project was built.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import threading
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .redact import redact_argv, redact_text

_HEADER_SENTINEL = "<!-- BUILD_LOG schema:1 -->"
_LOCK = threading.Lock()


def _now_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: str | Path) -> str | None:
    """Return the hex SHA-256 of a file, or None if it cannot be read."""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(64 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _project_label(project_dir: Path) -> str:
    name = project_dir.name
    pj = project_dir / "project.json"
    try:
        if pj.exists():
            data = json.loads(pj.read_text(encoding="utf-8"))
            name = data.get("name") or name
    except Exception:
        pass
    return name


def write_header_if_missing(project_dir: str | Path) -> Path:
    """Create BUILD_LOG.md with an audit-purpose header if it does not exist."""
    pdir = Path(project_dir).resolve()
    pdir.mkdir(parents=True, exist_ok=True)
    log_path = pdir / "BUILD_LOG.md"
    if log_path.exists() and _HEADER_SENTINEL in log_path.read_text(encoding="utf-8", errors="replace"):
        return log_path

    project_name = _project_label(pdir)
    schema_version = ""
    deps_block = ""
    pj = pdir / "project.json"
    if pj.exists():
        try:
            data = json.loads(pj.read_text(encoding="utf-8"))
            schema_version = data.get("schemaVersion", "")
            deps = data.get("dependencies", {}) or {}
            if deps:
                deps_block = "\n".join(f"  - `{k}`: `{v}`" for k, v in sorted(deps.items()))
        except Exception:
            pass

    header = (
        f"{_HEADER_SENTINEL}\n"
        f"# BUILD_LOG — {project_name}\n\n"
        "## Audit purpose\n\n"
        "This file is the **append-only source of truth** for every action the "
        "uipath-builder-agent (or a human collaborator) takes inside this UiPath "
        "project. It exists so that:\n\n"
        "1. Reviewers can trace exactly which CLI commands were executed, which "
        "files were written, and which validation passes / runs were attempted.\n"
        "2. Failed runs can be diagnosed long after the fact by reading the "
        "full command line, exit code, and trimmed stdout/stderr.\n"
        "3. Recurring incidents graduate into "
        "`data/library/books/lessons-learned/99-incidents/` so the agent learns "
        "from past mistakes.\n\n"
        "Do **not** edit historical entries; append new events only. Secrets "
        "(connection strings, tokens, asset values) are masked before they reach "
        "this file — see `uipath_claude/audit/redact.py`.\n\n"
        "## Project snapshot at first event\n\n"
        f"- **Project name:** `{project_name}`\n"
        f"- **schemaVersion:** `{schema_version}`\n"
        + (f"- **Dependencies:**\n{deps_block}\n" if deps_block else "")
        + "\n## Events\n\n"
    )
    with _LOCK:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(header)
    return log_path


def _excerpt(text: str | None, *, head_lines: int = 50, tail_lines: int = 50) -> str:
    if not text:
        return ""
    lines = text.splitlines()
    if len(lines) <= head_lines + tail_lines:
        return "\n".join(lines)
    head = lines[:head_lines]
    tail = lines[-tail_lines:]
    omitted = len(lines) - len(head) - len(tail)
    return "\n".join(head + [f"... (omitted {omitted} lines) ..."] + tail)


def _render_files(files: Iterable[Mapping[str, Any]] | None) -> str:
    if not files:
        return ""
    rows = ["| Path | SHA-256 | Bytes |", "|---|---|---|"]
    for entry in files:
        path = entry.get("path", "")
        sha = entry.get("sha256", "") or ""
        size = entry.get("bytes", "")
        rows.append(f"| `{path}` | `{sha[:12] + '…' if sha else ''}` | {size} |")
    return "\n".join(rows)


def _render_validation(passes: Sequence[Mapping[str, Any]] | None) -> str:
    if not passes:
        return ""
    rows = ["| Pass | Errors | Warnings |", "|---|---|---|"]
    for entry in passes:
        rows.append(
            "| {pass_} | {err} | {warn} |".format(
                pass_=entry.get("pass", "?"),
                err=len(entry.get("errors", []) or []),
                warn=len(entry.get("warnings", []) or []),
            )
        )
    return "\n".join(rows)


def append_event(project_dir: str | Path, event: Mapping[str, Any]) -> Path | None:
    """Append a single event to `<project_dir>/BUILD_LOG.md`.

    Best-effort: returns None and silently swallows IO errors so audit failures
    never break the agent or CLI runner. Callers should still pass a meaningful
    project_dir (a missing path will be created).
    """
    try:
        pdir = Path(project_dir).resolve()
        log_path = write_header_if_missing(pdir)

        actor = event.get("actor", "agent")
        action = event.get("action", "unknown")
        timestamp = event.get("timestamp") or _now_iso()
        outcome = event.get("outcome", "")
        exit_code = event.get("exit_code", "")
        studio_attached = event.get("studio_attached", "unknown")

        argv = event.get("command")
        if isinstance(argv, (list, tuple)):
            cmd_text = " ".join(redact_argv(argv))
        elif isinstance(argv, str):
            cmd_text = redact_text(argv)
        else:
            cmd_text = ""

        stdout_excerpt = redact_text(_excerpt(event.get("stdout_excerpt") or event.get("stdout")))
        stderr_excerpt = redact_text(_excerpt(event.get("stderr_excerpt") or event.get("stderr")))

        files_md = _render_files(event.get("files_written"))
        validation_md = _render_validation(event.get("validation_passes"))

        notes = event.get("notes") or ""

        parts = [
            f"### {timestamp} · `{action}` · actor=`{actor}` · outcome=`{outcome or '-'}`",
            "",
            f"- **exit_code:** `{exit_code}`" if exit_code != "" else "",
            f"- **studio_attached:** `{studio_attached}`",
        ]
        if notes:
            parts.append(f"- **notes:** {notes}")
        if cmd_text:
            parts.extend(["", "**command:**", "", "```", cmd_text, "```"])
        if files_md:
            parts.extend(["", "**files written:**", "", files_md])
        if validation_md:
            parts.extend(["", "**validation passes:**", "", validation_md])
        if stdout_excerpt:
            parts.extend(["", "<details><summary>stdout (excerpt)</summary>", "", "```", stdout_excerpt, "```", "", "</details>"])
        if stderr_excerpt:
            parts.extend(["", "<details><summary>stderr (excerpt)</summary>", "", "```", stderr_excerpt, "```", "", "</details>"])
        parts.append("\n---\n")

        body = "\n".join(p for p in parts if p is not None)
        with _LOCK:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(body + "\n")
        return log_path
    except Exception:
        # Auditing must never break the build. Best-effort only.
        try:
            os.write(2, b"[audit.build_log] append_event failed\n")
        except Exception:
            pass
        return None
