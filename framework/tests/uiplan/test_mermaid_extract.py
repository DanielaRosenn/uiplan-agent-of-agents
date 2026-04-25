from pathlib import Path

from tools.uiplan.validators.mermaid_extract import iter_mermaid_blocks


def test_iter_mermaid_blocks_counts(tmp_path: Path) -> None:
    md = tmp_path / "a.md"
    md.write_text(
        "# t\n\n```mermaid\nflowchart LR\n  A-->B\n```\n\n```Mermaid\ngraph TD\n  x\n```\n",
        encoding="utf-8",
    )
    blocks = iter_mermaid_blocks([md])
    assert len(blocks) == 2
    assert "flowchart LR" in blocks[0].body
    assert blocks[0].start_line == 3


def test_no_blocks(tmp_path: Path) -> None:
    md = tmp_path / "b.md"
    md.write_text("# no diagrams\n", encoding="utf-8")
    assert iter_mermaid_blocks([md]) == []
