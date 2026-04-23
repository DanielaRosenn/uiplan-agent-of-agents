from pathlib import Path


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
