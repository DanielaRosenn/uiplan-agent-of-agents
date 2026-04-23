from pathlib import Path


def resolve_runtime_root(root: Path) -> Path:
    if (root / "framework" / "uipath_claude").exists():
        return root / "framework"
    return root


def test_resolve_runtime_root_prefers_legacy_before_phase2(tmp_path: Path) -> None:
    (tmp_path / "framework" / "uipath_claude").mkdir(parents=True)
    (tmp_path / "uipath_claude").mkdir(parents=True)
    assert resolve_runtime_root(tmp_path) == tmp_path / "framework"
