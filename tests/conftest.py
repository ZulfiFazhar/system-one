import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import settings
from app.core.server import create_application


@pytest.fixture
def client_no_auth(monkeypatch):
    monkeypatch.setattr(settings, "laya_api_key", None)
    monkeypatch.setattr(settings, "laya_mock_router", True)
    app = create_application(mock_router=True)
    return TestClient(app)


@pytest.fixture
def client_with_auth(monkeypatch):
    monkeypatch.setattr(settings, "laya_api_key", SecretStr("secret-token-123"))
    monkeypatch.setattr(settings, "laya_mock_router", True)
    app = create_application(mock_router=True)
    return TestClient(app)
