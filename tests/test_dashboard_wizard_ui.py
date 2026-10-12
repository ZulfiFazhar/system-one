import pytest
from fastapi.testclient import TestClient
from app.core import db
from app.core.config import settings
from app.core.security import create_admin_session_token
from app.core.server import create_application


@pytest.fixture
def test_ui_client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_wizard_ui.db")
    db.init_db(db_path)
    monkeypatch.setattr(settings, "database_path", db_path)
    app = create_application()
    client = TestClient(app)
    token = create_admin_session_token("admin")
    client.cookies["admin_session"] = token
    return client, db_path


def test_dashboard_renders_setup_wizard_when_not_completed(test_ui_client):
    client, db_path = test_ui_client
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    html = resp.text
    assert "INITIAL SYSTEM SETUP: SELECT MODELS" in html
    assert 'id="setup-wizard-modal"' in html
    assert "Download & Load Selected Models" in html


def test_dashboard_hides_setup_wizard_when_completed(test_ui_client):
    client, db_path = test_ui_client
    db.update_system_settings(
        {"models_setup_completed": "1", "active_models": "laya"}, db_path=db_path
    )
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "INITIAL SYSTEM SETUP: SELECT MODELS" not in resp.text
