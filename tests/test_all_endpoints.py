from fastapi.testclient import TestClient

from app.core import db
from app.core.config import settings
from app.core.security import create_admin_session_token


def test_full_system_endpoints_sweep(client_with_auth):
    client = client_with_auth

    # 1. Health & Public Web
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"
    assert "loaded_models" in resp.json()

    resp = client.get("/")
    assert resp.status_code == 200
    assert "Supported Decision Models" in resp.text

    resp = client.get("/convaiinnovations/laya-multilingual")
    assert resp.status_code == 200
    assert "laya-multilingual" in resp.text

    resp = client.get("/vllm-sr/d3-lite")
    assert resp.status_code == 200
    assert "d3-lite" in resp.text

    resp = client.get("/jaredpalmer/kev-0.8b")
    assert resp.status_code == 200
    assert "kev-0.8b" in resp.text

    resp = client.get("/nonexistent/unknown-model")
    assert resp.status_code == 404

    # 2. Auth & Web Redirects
    resp = client.get("/login")
    assert resp.status_code == 200
    assert "Dashboard Sign In" in resp.text

    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"

    resp = client.get("/admin", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/dashboard"

    resp = client.get("/admin/login", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"

    # Bad login
    resp = client.post("/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401

    # Good login
    resp = client.post("/login", json={"username": "admin", "password": "changeme"})
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Authenticated client with cookie
    token = create_admin_session_token("admin")
    client.cookies["admin_session"] = token

    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "Dashboard" in resp.text

    resp = client.get("/login", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/dashboard"

    # 3. SystemOne Inference
    q = {"q": {"type": "noul", "instructions": "test"}}
    resp = client.post("/v1/systemone", json={"state": "hello", "questions": q})
    assert resp.status_code == 200
    assert resp.json()["model"] == "laya"

    resp = client.post(
        "/v1/systemone", json={"state": "hello", "model": "d3-lite", "questions": q}
    )
    assert resp.status_code == 200
    assert resp.json()["model"] == "d3-lite"

    resp = client.post(
        "/v1/systemone", json={"state": "hello", "model": "kev", "questions": q}
    )
    assert resp.status_code == 200
    assert resp.json()["model"] == "kev"

    resp = client.post(
        "/v1/systemone",
        json={"state": "hello", "model": "vllm-sr/d3-lite", "questions": q},
    )
    assert resp.status_code == 200

    resp = client.post(
        "/v1/systemone",
        json={"state": "hello", "model": "jaredpalmer/kev-0.8b", "questions": q},
    )
    assert resp.status_code == 200

    resp = client.post(
        "/v1/systemone",
        json={"state": "hello", "model": "unsupported-model-xyz", "questions": q},
    )
    assert resp.status_code == 400

    # 4. Admin API Endpoints
    resp = client.get("/api/admin/overview")
    assert resp.status_code == 200
    assert "total_requests" in resp.json()

    resp = client.get("/api/admin/health")
    assert resp.status_code == 200

    resp = client.get("/api/admin/keys")
    assert resp.status_code == 200

    resp = client.post("/api/admin/keys", json={"name": "test-key-suite"})
    assert resp.status_code == 201
    key_id = resp.json()["id"]

    resp = client.get(f"/api/admin/keys/{key_id}/activity")
    assert resp.status_code == 200

    resp = client.delete(f"/api/admin/keys/{key_id}")
    assert resp.status_code == 200

    resp = client.get("/api/admin/logs")
    assert resp.status_code == 200

    resp = client.get("/api/admin/settings")
    assert resp.status_code == 200

    resp = client.put(
        "/api/admin/settings",
        json={"rate_limit_requests": 25, "rate_limit_window_seconds": 60},
    )
    assert resp.status_code == 200

    resp = client.put(
        "/api/admin/credentials",
        json={"username": "admin", "password": "changeme"},
    )
    assert resp.status_code == 200

    resp = client.get("/api/admin/blocklist")
    assert resp.status_code == 200

    resp = client.post(
        "/api/admin/blocklist",
        json={"ip_address": "192.168.200.1", "reason": "test block"},
    )
    assert resp.status_code == 201

    resp = client.delete("/api/admin/blocklist/192.168.200.1")
    assert resp.status_code == 200

    resp = client.get("/api/admin/models/setup/status")
    assert resp.status_code == 200

    resp = client.post("/api/admin/models/setup", json={"models": []})
    assert resp.status_code == 400

    # Stream endpoint verification
    from unittest.mock import patch

    async def _finite_event_stream():
        yield "data: {}\n\n"

    with patch(
        "app.api.admin_route.default_setup_manager.event_generator",
        _finite_event_stream,
    ):
        resp = client.get("/api/admin/models/setup/stream")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

    # Logout
    resp = client.post("/logout")
    assert resp.status_code == 200
    assert resp.json()["success"] is True
