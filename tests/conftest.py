from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import settings
from app.core.server import create_application


def create_mock_router():
    router = MagicMock()
    router.unload = MagicMock()

    def mock_predict(state, questions):
        answers = {}
        for q_id, q in questions.items():
            q_type = q.get("type") if isinstance(q, dict) else getattr(q, "type", "noul")
            if q_type == "noul":
                answers[q_id] = {"noul": 0.9}
            elif q_type == "choice":
                criteria = q.get("criteria", {}) if isinstance(q, dict) else getattr(q, "criteria", {})
                choice_key = list(criteria.keys())[0] if criteria else "default"
                answers[q_id] = {
                    "choice": choice_key,
                    "probabilities": {choice_key: 1.0},
                    "confidence": 1.0,
                }
            elif q_type == "score":
                answers[q_id] = {"score": 1.0, "confidence": 0.8}
        return {"answers": answers}

    router.predict.side_effect = mock_predict
    return router


@pytest.fixture(scope="session")
def test_app():
    mock_router = create_mock_router()

    def mock_load(app_state):
        app_state.router = mock_router
        return mock_router

    with patch("app.core.server.load_laya_model", side_effect=mock_load), \
         patch("app.services.laya_service.load_laya_model", side_effect=mock_load), \
         patch("app.services.laya_service.ensure_model_weights", return_value=None):
        app = create_application()
        with TestClient(app) as client:
            yield app


@pytest.fixture(autouse=True)
def mock_lazy_laya_load(monkeypatch):
    mock_router = create_mock_router()

    def mock_load(app_state):
        app_state.router = mock_router
        return mock_router

    monkeypatch.setattr("app.services.laya_service.ensure_model_weights", lambda: None)
    monkeypatch.setattr("app.services.laya_service.load_laya_model", mock_load)
    monkeypatch.setattr("app.core.server.load_laya_model", mock_load)


@pytest.fixture
def client_no_auth(test_app, monkeypatch):
    monkeypatch.setattr(settings, "laya_api_key", None)
    return TestClient(test_app)


@pytest.fixture
def client_with_auth(test_app, monkeypatch):
    monkeypatch.setattr(settings, "laya_api_key", SecretStr("secret-token-123"))
    return TestClient(test_app)
