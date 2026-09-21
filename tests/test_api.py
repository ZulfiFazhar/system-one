import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from app.core.server import create_application


def test_healthz(client_no_auth):
    resp = client_no_auth.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"

    resp_alias = client_no_auth.get("/health")
    assert resp_alias.status_code == 200
    assert resp_alias.json()["status"] == "ready"


def test_home_landing_page(client_no_auth):
    resp = client_no_auth.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "System One" in resp.text
    assert "We took the opposite research direction" in resp.text


def test_systemone_unauthorized(client_with_auth):
    resp = client_with_auth.post("/v1/systemone", json={
        "state": "test",
        "questions": {"q": {"type": "noul", "instructions": "test"}}
    })
    assert resp.status_code == 401


def test_systemone_authorized(client_with_auth):
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
                "criteria": ["only one"]
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


def test_lifespan_lifecycle(test_app):
    assert hasattr(test_app.state, "router")
    assert test_app.state.router is not None


def test_verify_api_key_constant_time(monkeypatch):
    import secrets
    from unittest.mock import patch
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials
    from app.core.config import settings
    from app.core.security import verify_api_key

    monkeypatch.setattr(settings, "laya_api_key", SecretStr("secret-val"))
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
