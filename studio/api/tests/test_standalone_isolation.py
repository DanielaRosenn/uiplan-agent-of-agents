"""Verify studio/api can start and serve all core endpoints without framework/.

This test blocks the ``uipath_claude`` and ``mcp_server`` packages from
being importable, simulating a checkout that contains only the studio/
directory.  Every non-framework-dependent endpoint must return a
success-class status code; framework-dependent endpoints (library search,
review) must degrade gracefully instead of crashing.
"""
from __future__ import annotations

import sys
import types
from unittest.mock import patch

import pytest


def _make_import_blocker(blocked_prefixes: tuple[str, ...]):
    """Return a meta_path finder that blocks imports starting with *blocked_prefixes*."""
    from importlib.abc import MetaPathFinder
    from importlib.machinery import ModuleSpec

    class _Blocker(MetaPathFinder):
        def find_spec(self, fullname: str, path=None, target=None):
            if fullname.startswith(blocked_prefixes):
                raise ModuleNotFoundError(
                    f"[isolation-test] {fullname} is blocked to simulate standalone studio/"
                )
            return None

    return _Blocker()


BLOCKED = ("uipath_claude", "mcp_server")


@pytest.fixture()
def isolated_app():
    """Import the FastAPI app with framework modules blocked."""
    blocker = _make_import_blocker(BLOCKED)
    # Remove any already-cached framework modules so the blocker takes effect.
    cached = {k: v for k, v in sys.modules.items() if k.startswith(BLOCKED)}
    for key in cached:
        sys.modules.pop(key, None)

    sys.meta_path.insert(0, blocker)
    try:
        # Force a fresh import of the modules that touch framework code.
        for mod_name in list(sys.modules):
            if mod_name.startswith("app."):
                sys.modules.pop(mod_name, None)

        from app.main import app  # noqa: F811
        from fastapi.testclient import TestClient

        yield TestClient(app, headers={"host": "127.0.0.1:8000"})
    finally:
        sys.meta_path.remove(blocker)
        # Restore cached modules.
        sys.modules.update(cached)


def test_health_endpoint_works_standalone(isolated_app):
    resp = isolated_app.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_context_sources_degrade_gracefully(isolated_app):
    resp = isolated_app.get("/context/sources")
    assert resp.status_code == 200
    body = resp.json()
    assert "categories" in body


def test_copilotkit_info_works_standalone(isolated_app):
    resp = isolated_app.get("/copilotkit/info")
    assert resp.status_code == 200


def test_review_degrades_without_framework(isolated_app):
    resp = isolated_app.post(
        "/review/run",
        json={
            "bundle_root": "nonexistent",
            "spec": "# spec",
            "plan": "# plan",
            "tasks": "# tasks",
        },
    )
    # Should not be a 500 — either 200 with degraded result or a handled error
    assert resp.status_code != 500


def test_library_search_degrades_without_framework(isolated_app):
    resp = isolated_app.post(
        "/copilotkit/runtime/action/search_library_context",
        json={"arguments": {"query": "deploy agent"}},
    )
    assert resp.status_code == 200
    body = resp.json()
    # Should return empty items, not crash
    assert body["result"]["items"] == []
