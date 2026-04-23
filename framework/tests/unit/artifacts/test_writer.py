"""Bootstrap artifact writer tests."""
from pathlib import Path

from uipath_claude.artifacts.writer import BootstrapArtifactWriter


def test_bootstrap_artifact_writer_writes_all(tmp_path: Path) -> None:
    writer = BootstrapArtifactWriter(tmp_path)
    pdd = writer.write_pdd("# PDD")
    sdd = writer.write_sdd("# SDD")
    qa = writer.write_qa("# QA")
    dev = writer.write_developer_artifacts("plan body", "Invoice bot")

    assert pdd.read_text(encoding="utf-8") == "# PDD"
    assert "pdd" in str(pdd)
    assert sdd.read_text(encoding="utf-8") == "# SDD"
    assert qa.read_text(encoding="utf-8") == "# QA"
    assert Path(dev["implementation_plan"]).read_text(encoding="utf-8") == "plan body"
    assert Path(dev["project_json"]).exists()
    assert Path(dev["main_xaml"]).exists()
