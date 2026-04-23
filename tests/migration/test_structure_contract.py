from pathlib import Path


def test_current_expected_roots_exist():
    root = Path(__file__).resolve().parents[2]
    expected = ["uipath_claude", "mcp_server", "scripts", "docs", "skills", "extensions"]
    missing = [name for name in expected if not (root / name).exists()]
    assert not missing, f"Missing roots: {missing}"
