from pathlib import Path

import pytest

from uipath_claude.context.path_contract import repo_root_from_any, runtime_root, scripts_root


def test_runtime_root_returns_framework_when_layout_valid(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    (tmp_path / "langgraph.json").write_text("{}", encoding="utf-8")
    (tmp_path / "framework" / "uipath_claude").mkdir(parents=True)
    (tmp_path / "framework" / "mcp_server").mkdir(parents=True)
    assert runtime_root(tmp_path) == tmp_path / "framework"


def test_runtime_root_raises_when_framework_incomplete(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    (tmp_path / "langgraph.json").write_text("{}", encoding="utf-8")
    (tmp_path / "framework" / "uipath_claude").mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="mcp_server"):
        runtime_root(tmp_path)


def test_scripts_root_returns_ops_scripts(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    (tmp_path / "langgraph.json").write_text("{}", encoding="utf-8")
    (tmp_path / "ops" / "scripts").mkdir(parents=True)
    assert scripts_root(tmp_path) == tmp_path / "ops" / "scripts"


def test_scripts_root_raises_when_missing(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    (tmp_path / "langgraph.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="ops"):
        scripts_root(tmp_path)


def test_no_legacy_runtime_at_repo_root() -> None:
    """Phase 4: duplicate runtime trees must not exist at repository root."""
    root = repo_root_from_any(Path(__file__))
    assert not (root / "uipath_claude" / "__init__.py").is_file()
    assert not (root / "mcp_server" / "server.py").is_file()
