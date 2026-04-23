"""CLI smoke checks for local/CI verification."""

from __future__ import annotations

import subprocess
import sys


def run_cmd(cmd: list[str], input_text: str | None = None) -> tuple[int, str]:
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    out, _ = proc.communicate(input=input_text, timeout=90)
    return proc.returncode, out


def main() -> int:
    code, out = run_cmd(["uipath-claude", "--help"])
    if code != 0 or "chat" not in out.lower():
        print("FAIL: CLI help check failed")
        print(out)
        return 1

    code, out = run_cmd(
        ["uipath-claude", "chat", "--no-banner"],
        input_text="/help\n/skills\n/status\nexit\n",
    )
    if code != 0:
        print("FAIL: chat command execution failed")
        print(out)
        return 2
    if "available commands" not in out.lower():
        print("FAIL: /help output missing")
        print(out)
        return 3
    if "skills for role" not in out.lower() and "no skills found" not in out.lower():
        print("FAIL: /skills output missing")
        print(out)
        return 4
    if "model" not in out.lower() or "skill_count" not in out.lower():
        print("FAIL: /status output missing session fields")
        print(out)
        return 5

    print("PASS: CLI smoke checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

