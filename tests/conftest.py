import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import settings
from app.core.server import create_application


@pytest.fixture(scope="session")
def test_app():
    app = create_application()
    with TestClient(app) as client:
        yield app


@pytest.fixture
def client_no_auth(test_app, monkeypatch):
    monkeypatch.setattr(settings, "laya_api_key", None)
    return TestClient(test_app)


@pytest.fixture
def client_with_auth(test_app, monkeypatch):
    monkeypatch.setattr(settings, "laya_api_key", SecretStr("secret-token-123"))
    return TestClient(test_app)
