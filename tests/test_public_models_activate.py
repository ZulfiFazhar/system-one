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
