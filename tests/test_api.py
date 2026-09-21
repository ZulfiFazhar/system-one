import os
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
import pytest
from app import create_app

@pytest.fixture
def client_no_auth():
    os.environ.pop("LAYA_API_KEY", None)
    app = create_app(mock_router=True)
    return TestClient(app)

@pytest.fixture
def client_with_auth():
    os.environ["LAYA_API_KEY"] = "secret-token-123"
    app = create_app(mock_router=True)
    yield TestClient(app)
    os.environ.pop("LAYA_API_KEY", None)

def test_healthz(client_no_auth):
    resp = client_no_auth.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"

def test_systemone_unauthorized(client_with_auth):
    resp = client_with_auth.post("/v1/systemone", json={
        "state": "test",
        "questions": {"q": {"type": "noul", "instructions": "test"}}
    })
    assert resp.status_code == 401

def test_systemone_authorized_mock(client_with_auth):
    resp = client_with_auth.post(
        "/v1/systemone",
        headers={"Authorization": "Bearer secret-token-123"},
        json={
            "state": "test duplicate charge",
            "questions": {
                "is_refund": {
                    "type": "noul",
                    "instructions": "Is refund requested?"
                }
            }
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "laya"
    assert "is_refund" in data["answers"]
    assert data["answers"]["is_refund"]["type"] == "noul"

def test_systemone_invalid_schema(client_no_auth):
    resp = client_no_auth.post("/v1/systemone", json={
        "state": "test",
        "questions": {
            "invalid_score": {
                "type": "score",
                "instructions": "rate",
                "criteria": ["only one"]  # requires min 2
            }
        }
    })
    assert resp.status_code == 422


def test_systemone_wrong_token(client_with_auth):
    resp = client_with_auth.post(
        "/v1/systemone",
        headers={"Authorization": "Bearer wrong-token"},
        json={
            "state": "test",
            "questions": {"q": {"type": "noul", "instructions": "test"}}
        }
    )
    assert resp.status_code == 401


def test_systemone_multi_question(client_no_auth):
    resp = client_no_auth.post(
        "/v1/systemone",
        json={
            "state": "urgent billing issue",
            "model": "laya",
            "questions": {
                "urgent": {"type": "noul", "instructions": "Is urgent?"},
                "category": {
                    "type": "choice",
                    "instructions": "Category?",
                    "criteria": {"billing": "Billing", "tech": "Tech"}
                },
                "frustration": {
                    "type": "score",
                    "instructions": "Rate frustration",
                    "criteria": ["Low", "High"]
                }
            }
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "laya"
    assert data["answers"]["urgent"]["type"] == "noul"
    assert data["answers"]["category"]["type"] == "choice"
    assert data["answers"]["frustration"]["type"] == "score"
    assert "usage" in data


def test_lifespan_lifecycle():
    app = create_app(mock_router=True)
    with TestClient(app) as client:
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert hasattr(app.state, "router")


def test_main_entrypoint(monkeypatch):
    from unittest.mock import patch
    import app as app_module
    with patch("uvicorn.run") as mock_run:
        app_module.main()
        mock_run.assert_called_once_with(app_module.app, host="0.0.0.0", port=8000, reload=False)


def test_verify_api_key_constant_time(monkeypatch):
    import secrets
    from unittest.mock import patch
    from fastapi import HTTPException
    from app import verify_api_key
    from fastapi.security import HTTPAuthorizationCredentials

    monkeypatch.setenv("LAYA_API_KEY", "secret-val")
    with patch("secrets.compare_digest", wraps=secrets.compare_digest) as mock_compare:
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="secret-val")
        verify_api_key(creds)
        mock_compare.assert_called_with("secret-val", "secret-val")

        mock_compare.reset_mock()
        with pytest.raises(HTTPException) as exc_info:
            bad_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong-val")
            verify_api_key(bad_creds)
        assert exc_info.value.status_code == 401
        mock_compare.assert_called_with("wrong-val", "secret-val")


