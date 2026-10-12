import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.core.server import create_application


@pytest.fixture
def client_public():
    app = create_application()
    return TestClient(app)


def test_activate_model_validation(client_public):
    # Missing or empty model name
    resp = client_public.post("/api/models/activate", json={"model": ""})
    assert resp.status_code == 400

    # Unknown model name
    resp_unknown = client_public.post(
        "/api/models/activate", json={"model": "completely-unknown-model-xyz"}
    )
    assert resp_unknown.status_code == 400


def test_activate_model_success(client_public):
    from app.services.setup_manager import default_setup_manager

    with patch.object(
        default_setup_manager, "start_setup", new_callable=AsyncMock
    ) as mock_start:
        resp = client_public.post("/api/models/activate", json={"model": "d3-lite"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "started"
        assert data["model"] == "d3-lite"


def test_activate_model_already_active(client_public):
    client_public.app.state.models = {"d3-lite": object()}
    resp = client_public.post("/api/models/activate", json={"model": "d3-lite"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "already_active", "model": "d3-lite"}


def test_activate_model_conflict_when_running(client_public):
    from app.services.setup_manager import default_setup_manager

    with patch.object(default_setup_manager, "_is_running", True):
        resp = client_public.post("/api/models/activate", json={"model": "d3-lite"})
        assert resp.status_code == 409
        assert "in progress" in resp.json().get("detail", "")


def test_activate_model_rate_limit(client_public):
    from fastapi import HTTPException
    with patch(
        "app.api.models_route.check_rate_limit",
        side_effect=HTTPException(status_code=429, detail="Rate limit exceeded"),
    ):
        resp = client_public.post("/api/models/activate", json={"model": "d3-lite"})
        assert resp.status_code == 429


@pytest.mark.anyio
async def test_activate_model_preserves_existing_db_models(monkeypatch, tmp_path):
    test_db = str(tmp_path / "preserve_models.db")
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    from app.core import db
    from app.services.models.registry import ModelRegistry
    from app.services.setup_manager import ModelSetupManager

    db.init_db(test_db)
    db.update_system_settings(
        {"models_setup_completed": "1", "active_models": "laya"},
        db_path=test_db,
    )

    manager = ModelSetupManager(db_path=test_db)
    app_state = SimpleNamespace(models={})
    mock_adapter = MagicMock()
    mock_adapter.name = "d3-lite"
    mock_adapter.load = MagicMock()

    monkeypatch.setattr(ModelRegistry, "get_adapter", lambda self, name: mock_adapter)

    await manager.start_setup(app_state=app_state, models=["d3-lite"])

    settings_dict = db.get_system_settings(test_db)
    assert settings_dict["models_setup_completed"] == "1"
    assert settings_dict["active_models"] == "laya,d3-lite"


def test_public_models_stream(client_public):
    async def _finite_stream():
        yield 'data: {"phase": "connected", "progress": 0, "message": "Stream connected"}\n\n'

    with patch(
        "app.services.setup_manager.default_setup_manager.event_generator",
        _finite_stream,
    ):
        resp = client_public.get("/api/models/stream")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
