"""Safe command parsing and execution helpers for hooks."""

from __future__ import annotations

import shlex
import subprocess
import re
from collections.abc import Sequence


def _unwrap_matching_quotes(value: str) -> str:
    """Remove a single pair of matching wrapping quotes."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_command(command: str | Sequence[str]) -> list[str]:
    """Normalize a command into argv format."""
    if isinstance(command, str):
        parts = [
            _unwrap_matching_quotes(part)
            for part in shlex.split(command, posix=False)
        ]
    else:
        parts = [str(part) for part in command]

    if not parts:
        raise ValueError("empty command")

    return parts


_SHELL_META_PATTERN = re.compile(r"&&|\|\||[|&;<>`$(){}\[\]*?~\n]")


def _requires_shell_parsing(command: str) -> bool:
    """Return True when command likely needs shell parsing."""
    return bool(_SHELL_META_PATTERN.search(command))


def run_command(
    command: str | Sequence[str],
    *,
    timeout: int = 30,
    allow_shell_fallback: bool = False,
    **kwargs,
) -> subprocess.CompletedProcess:
    """Execute a command safely without shell expansion."""
    if (
        allow_shell_fallback
        and isinstance(command, str)
        and _requires_shell_parsing(command)
    ):
        return subprocess.run(
            command,
            shell=True,
            capture_output=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            **kwargs,
        )

    argv = parse_command(command)
    return subprocess.run(
        argv,
        shell=False,
        capture_output=True,
        timeout=timeout,
        stdin=subprocess.DEVNULL,
        **kwargs,
    )
