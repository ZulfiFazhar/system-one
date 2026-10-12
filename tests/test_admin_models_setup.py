import pytest
from fastapi.testclient import TestClient
from app.core import db
from app.core.config import settings
from app.core.security import create_admin_session_token
from app.core.server import create_application


@pytest.fixture
def test_setup_client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_api_setup.db")
    db.init_db(db_path)
    monkeypatch.setattr(settings, "database_path", db_path)

    async def _mock_event_generator():
        yield "data: {}\n\n"

    monkeypatch.setattr(
        "app.api.admin_route.default_setup_manager.event_generator",
        _mock_event_generator,
    )

    app = create_application()
    client = TestClient(app)
    token = create_admin_session_token("admin")
    client.cookies["admin_session"] = token
    return client


def test_setup_status_endpoint(test_setup_client):
    resp = test_setup_client.get("/api/admin/models/setup/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "setup_completed" in data
    assert "active_models" in data
    assert "is_running" in data


def test_setup_post_validation(test_setup_client):
    # Empty models list rejected with 400
    resp_empty = test_setup_client.post("/api/admin/models/setup", json={"models": []})
    assert resp_empty.status_code == 400

    # Invalid payload rejected
    resp_bad = test_setup_client.post("/api/admin/models/setup", json={})
    assert resp_bad.status_code in (400, 422)


def test_setup_stream_endpoint(test_setup_client):
    resp = test_setup_client.get("/api/admin/models/setup/stream")
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")


def test_setup_post_success(test_setup_client, monkeypatch):
    from unittest.mock import AsyncMock
    from app.api.admin_route import default_setup_manager

    mock_start = AsyncMock()
    monkeypatch.setattr(default_setup_manager, "start_setup", mock_start)
    monkeypatch.setattr(default_setup_manager, "_is_running", False)

    resp = test_setup_client.post(
        "/api/admin/models/setup", json={"models": ["laya"]}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "started"
    assert data["models"] == ["laya"]


def test_setup_post_already_running(test_setup_client, monkeypatch):
    from app.api.admin_route import default_setup_manager

    monkeypatch.setattr(default_setup_manager, "_is_running", True)

    resp = test_setup_client.post(
        "/api/admin/models/setup", json={"models": ["laya"]}
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Model setup is already in progress"


def test_setup_unauthorized(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_unauth.db")
    db.init_db(db_path)
    monkeypatch.setattr(settings, "database_path", db_path)
    app = create_application()
    client = TestClient(app)

    resp_status = client.get("/api/admin/models/setup/status")
    assert resp_status.status_code == 401

    resp_post = client.post("/api/admin/models/setup", json={"models": ["laya"]})
    assert resp_post.status_code == 401

    resp_stream = client.get("/api/admin/models/setup/stream")
    assert resp_stream.status_code == 401
