import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.server import create_application


def test_health(client_no_auth):
    resp = client_no_auth.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"

    # Verify /healthz is completely removed
    resp_old = client_no_auth.get("/healthz")
    assert resp_old.status_code == 404


def test_home_landing_page(client_no_auth):
    resp = client_no_auth.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "System One" in resp.text
    assert "We took the opposite research direction" in resp.text


def test_systemone_public_access_and_rate_limit(client_with_auth, monkeypatch):
    from app.core.config import settings
    from app.core.security import reset_rate_limits

    reset_rate_limits()
    monkeypatch.setattr(settings, "rate_limit_requests", 2)
    monkeypatch.setattr(settings, "rate_limit_window_seconds", 60)

    # 1st request without key (public access) -> 200 OK
    resp1 = client_with_auth.post(
        "/v1/systemone",
        json={
            "state": "test public 1",
            "questions": {"q": {"type": "noul", "instructions": "test"}},
        },
    )
    assert resp1.status_code == 200

    # 2nd request without key -> 200 OK
    resp2 = client_with_auth.post(
        "/v1/systemone",
        json={
            "state": "test public 2",
            "questions": {"q": {"type": "noul", "instructions": "test"}},
        },
    )
    assert resp2.status_code == 200

    # 3rd request exceeds limit -> 429 Too Many Requests
    resp3 = client_with_auth.post(
        "/v1/systemone",
        json={
            "state": "test public 3",
            "questions": {"q": {"type": "noul", "instructions": "test"}},
        },
    )
    assert resp3.status_code == 429
    assert "Public rate limit exceeded" in resp3.json()["detail"]
    assert "Retry-After" in resp3.headers

    reset_rate_limits()


def test_systemone_authorized(client_with_auth):
    resp = client_with_auth.post(
        "/v1/systemone",
        headers={"Authorization": "Bearer secret-token-123"},
        json={
            "state": "test duplicate charge",
            "questions": {
                "is_refund": {"type": "noul", "instructions": "Is refund requested?"}
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "laya"
    assert "is_refund" in data["answers"]
    assert data["answers"]["is_refund"]["type"] == "noul"


def test_systemone_invalid_schema(client_no_auth):
    resp = client_no_auth.post(
        "/v1/systemone",
        json={
            "state": "test",
            "questions": {
                "invalid_score": {
                    "type": "score",
                    "instructions": "rate",
                    "criteria": ["only one"],
                }
            },
        },
    )
    assert resp.status_code == 422


def test_systemone_wrong_token(client_with_auth):
    resp = client_with_auth.post(
        "/v1/systemone",
        headers={"Authorization": "Bearer wrong-token"},
        json={
            "state": "test",
            "questions": {"q": {"type": "noul", "instructions": "test"}},
        },
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
                    "criteria": {"billing": "Billing", "tech": "Tech"},
                },
                "frustration": {
                    "type": "score",
                    "instructions": "Rate frustration",
                    "criteria": ["Low", "High"],
                },
            },
        },
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
    from unittest.mock import MagicMock, patch

    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    from app.core.config import settings
    from app.core.security import verify_api_key

    mock_request = MagicMock()
    mock_request.client.host = "127.0.0.1"

    monkeypatch.setattr(settings, "laya_api_key", SecretStr("secret-val"))
    with patch("secrets.compare_digest", wraps=secrets.compare_digest) as mock_compare:
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="secret-val")
        verify_api_key(mock_request, creds)
        mock_compare.assert_called_with("secret-val", "secret-val")

        mock_compare.reset_mock()
        with pytest.raises(HTTPException) as exc_info:
            bad_creds = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials="wrong-val"
            )
            verify_api_key(mock_request, bad_creds)
        assert exc_info.value.status_code == 401
        mock_compare.assert_called_with("wrong-val", "secret-val")


def test_lazy_loading(monkeypatch):
    from fastapi.testclient import TestClient
    from app.core.config import settings
    from app.core.server import create_application

    monkeypatch.setattr(settings, "laya_lazy_load", True)
    monkeypatch.setattr(settings, "laya_api_key", None)
    app = create_application()
    with TestClient(app) as client:
        assert getattr(app.state, "router", None) is None

        health_resp = client.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["status"] == "ready"
        assert health_resp.json()["preloaded"] is False

        resp = client.post(
            "/v1/systemone",
            json={
                "state": "test lazy loading",
                "questions": {"q": {"type": "noul", "instructions": "test"}},
            },
        )
        assert resp.status_code == 200
        assert getattr(app.state, "router", None) is not None
