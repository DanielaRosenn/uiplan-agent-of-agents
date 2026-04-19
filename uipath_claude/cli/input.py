"""Chat input helper that gracefully handles multi-line paste.

Rich's ``Prompt.ask`` reads a single line. When the user pastes a multi-line
block (e.g. a bullet list) into the terminal, only the first line becomes the
``You:`` input; the remaining lines stay buffered on stdin and are then
consumed by the *next* interactive prompt (``Generate PDD? [y/n]``,
``Choose an option [1/2]``, etc.), which rejects them as invalid and loops.

``read_user_message`` collapses a paste into one ``user_input`` by draining
any extra lines that are already sitting in stdin (non-blocking) right after
the first line is read. On non-TTY stdin we just read one line as before.
"""
from __future__ import annotations

import sys
import time

try:
    import msvcrt  # type: ignore[attr-defined]

    _IS_WINDOWS = True
except ImportError:  # POSIX
    msvcrt = None  # type: ignore[assignment]
    _IS_WINDOWS = False
    import select  # noqa: E402


def _stdin_has_data(timeout: float) -> bool:
    """Return True if stdin has at least one byte ready within ``timeout`` s."""
    if _IS_WINDOWS:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if msvcrt.kbhit():  # type: ignore[union-attr]
                return True
            time.sleep(0.01)
        return msvcrt.kbhit()  # type: ignore[union-attr]
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    return bool(ready)


def _drain_buffered_lines(poll_seconds: float = 0.05) -> list[str]:
    """Read any additional lines that are already sitting in stdin.

    Uses a short non-blocking poll between lines so that legitimate paste
    blocks (which arrive nearly instantaneously) are captured but we never
    block waiting for a second line that the user did not type.
    """
    extra: list[str] = []
    while _stdin_has_data(poll_seconds):
        line = sys.stdin.readline()
        if not line:
            break
        extra.append(line.rstrip("\n").rstrip("\r"))
    return extra


def read_user_message(
    console,
    prompt: str = "[cyan]You:[/cyan] ",
    *,
    first_line: str | None = None,
) -> str:
    """Read a chat message, joining a multi-line paste into one string.

    - If ``first_line`` is provided, use it as the first line (caller already
      read it, e.g. via ``Prompt.ask``). Otherwise read the first line via
      ``console.input(prompt)``.
    - If the first line is empty, returns ``""`` immediately.
    - On a TTY, drains any additional lines already buffered (paste capture)
      and joins them with ``\\n``.
    - Strips a single trailing blank paste artifact while preserving internal
      blank lines.
    - On non-TTY stdin, behaves exactly like the previous single-line read.
    """
    first = first_line if first_line is not None else console.input(prompt)
    if not first.strip():
        return first

    if not getattr(sys.stdin, "isatty", lambda: False)():
        return first

    extra = _drain_buffered_lines()
    if not extra:
        return first

    if extra and extra[-1] == "":
        extra.pop()

    if not extra:
        return first
    return "\n".join([first, *extra])
