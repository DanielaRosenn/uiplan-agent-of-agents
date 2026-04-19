"""Tests for ``read_user_message`` chat input helper."""
from __future__ import annotations

import io
import sys
from unittest.mock import MagicMock

import pytest

from uipath_claude.cli import input as chat_input


class _FakeConsole:
    def __init__(self, lines: list[str]):
        self._lines = list(lines)

    def input(self, _prompt: str) -> str:
        return self._lines.pop(0)


def test_single_line_returned_as_is(monkeypatch):
    monkeypatch.setattr(chat_input, "_drain_buffered_lines", lambda: [])
    monkeypatch.setattr(sys, "stdin", MagicMock(isatty=lambda: True))
    out = chat_input.read_user_message(_FakeConsole([]), first_line="hello")
    assert out == "hello"


def test_empty_input_short_circuits(monkeypatch):
    drain = MagicMock()
    monkeypatch.setattr(chat_input, "_drain_buffered_lines", drain)
    out = chat_input.read_user_message(_FakeConsole([]), first_line="")
    assert out == ""
    drain.assert_not_called()


def test_non_tty_returns_first_line_only(monkeypatch):
    drain = MagicMock()
    monkeypatch.setattr(chat_input, "_drain_buffered_lines", drain)
    monkeypatch.setattr(sys, "stdin", MagicMock(isatty=lambda: False))
    out = chat_input.read_user_message(_FakeConsole([]), first_line="one")
    assert out == "one"
    drain.assert_not_called()


def test_first_line_read_from_console_when_not_provided(monkeypatch):
    monkeypatch.setattr(chat_input, "_drain_buffered_lines", lambda: [])
    monkeypatch.setattr(sys, "stdin", MagicMock(isatty=lambda: True))
    out = chat_input.read_user_message(_FakeConsole(["typed"]))
    assert out == "typed"


def test_paste_lines_are_joined(monkeypatch):
    monkeypatch.setattr(sys, "stdin", MagicMock(isatty=lambda: True))
    monkeypatch.setattr(
        chat_input,
        "_drain_buffered_lines",
        lambda: ["  - second line", "  - third line"],
    )
    out = chat_input.read_user_message(
        _FakeConsole([]), first_line="build me a thing:"
    )
    assert out == "build me a thing:\n  - second line\n  - third line"


def test_trailing_blank_artifact_stripped(monkeypatch):
    monkeypatch.setattr(sys, "stdin", MagicMock(isatty=lambda: True))
    monkeypatch.setattr(
        chat_input,
        "_drain_buffered_lines",
        lambda: ["second", ""],
    )
    out = chat_input.read_user_message(_FakeConsole([]), first_line="first")
    assert out == "first\nsecond"


def test_internal_blank_lines_preserved(monkeypatch):
    monkeypatch.setattr(sys, "stdin", MagicMock(isatty=lambda: True))
    monkeypatch.setattr(
        chat_input,
        "_drain_buffered_lines",
        lambda: ["a", "", "b"],
    )
    out = chat_input.read_user_message(_FakeConsole([]), first_line="first")
    assert out == "first\na\n\nb"


def test_drain_returns_empty_when_no_data(monkeypatch):
    monkeypatch.setattr(chat_input, "_stdin_has_data", lambda _t: False)
    assert chat_input._drain_buffered_lines() == []


def test_drain_collects_until_buffer_empty(monkeypatch):
    calls = iter([True, True, False])
    monkeypatch.setattr(chat_input, "_stdin_has_data", lambda _t: next(calls))
    monkeypatch.setattr(sys, "stdin", io.StringIO("alpha\nbeta\n"))
    assert chat_input._drain_buffered_lines() == ["alpha", "beta"]
