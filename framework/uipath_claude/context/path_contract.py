from pathlib import Path


def repo_root_from_any(path: Path) -> Path:
    """Walk parents from *path* to find the repository root.

    Stops at the first directory that has ``pyproject.toml`` and either
    ``langgraph.json`` or a ``skills/`` directory (submodule checkout).
    """
    start = path.resolve()
    if start.is_file():
        start = start.parent
    for ancestor in [start, *start.parents]:
        if not (ancestor / "pyproject.toml").is_file():
            continue
        if (ancestor / "langgraph.json").is_file():
            return ancestor
        if (ancestor / "skills").is_dir():
            return ancestor
    msg = f"Could not resolve repository root from {path}"
    raise FileNotFoundError(msg)


def runtime_root(repo_root: Path) -> Path:
    new_root = repo_root / "framework"
    if (new_root / "uipath_claude").exists() and (new_root / "mcp_server").exists():
        return new_root
    return repo_root


def scripts_root(repo_root: Path) -> Path:
    new_scripts = repo_root / "ops" / "scripts"
    if new_scripts.exists():
        return new_scripts
    return repo_root / "scripts"
