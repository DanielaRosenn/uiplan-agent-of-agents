"""Tests for ``tests.artifact_output_paths`` path safety."""

from __future__ import annotations

import pytest

from tests.artifact_output_paths import ensure_subdir


def test_ensure_subdir_accepts_single_segment() -> None:
    p = ensure_subdir("suite-a")
    assert p.name == "suite-a"
    assert "generated" in p.parts and "pytest" in p.parts


@pytest.mark.parametrize(
    "bad",
    [
        "..",
        "a/../b",
        "a/b",
        "",
        " ",
        "x/../y",
    ],
)
def test_ensure_subdir_rejects_unsafe(bad: str) -> None:
    with pytest.raises(ValueError):
        ensure_subdir(bad)
