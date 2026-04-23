from tools.uiplan.cli import app


def test_commands_registered():
    names = {c.name for c in app.registered_commands}
    assert "generate-docs" in names
    assert "scaffold-code" in names
