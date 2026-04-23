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
    """Return ``<repo>/framework`` after verifying the Phase 4 runtime layout."""
    fr = repo_root / "framework"
    uc = fr / "uipath_claude"
    ms = fr / "mcp_server"
    missing = [p.name for p in (uc, ms) if not p.is_dir()]
    if missing:
        msg = (
            f"Framework runtime incomplete at {fr}: "
            f"missing {', '.join(missing)}. Expected uipath_claude/ and mcp_server/ under framework/."
        )
        raise FileNotFoundError(msg)
    return fr


def scripts_root(repo_root: Path) -> Path:
    """Return ``<repo>/ops/scripts`` (canonical); no repo-root ``scripts/`` fallback."""
    p = repo_root / "ops" / "scripts"
    if not p.is_dir():
        msg = f"Expected scripts directory at {p}"
        raise FileNotFoundError(msg)
    return p
