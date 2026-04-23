from pathlib import Path


def test_current_expected_roots_exist():
    root = Path(__file__).resolve().parents[3]
    checks = [
        root / "framework" / "uipath_claude",
        root / "framework" / "mcp_server",
        root / "ops" / "scripts",
        root / "docs",
        root / "skills",
        root / "extensions",
    ]
    missing = [str(p) for p in checks if not p.exists()]
    assert not missing, f"Missing roots: {missing}"
