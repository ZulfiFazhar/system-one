import pytest
from fastapi.testclient import TestClient

from app.core import db
from app.core.config import settings
from app.core.security import refresh_security_caches, reset_rate_limits
from app.core.server import create_application


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_admin_api.db")
    db.init_db(db_path)
    monkeypatch.setattr(settings, "database_path", db_path)
    monkeypatch.setattr(settings, "admin_username", "admin")
    monkeypatch.setattr(settings, "admin_password", "changeme")
    reset_rate_limits()
    refresh_security_caches(db_path)
    return db_path


@pytest.fixture
def client(temp_db):
    app = create_application()
    return TestClient(app)


ADMIN_AUTH = ("admin", "changeme")


# 1. Auth Protection
def test_admin_endpoints_require_auth(client):
    endpoints = [
        ("GET", "/api/admin/overview"),
        ("GET", "/api/admin/health"),
        ("GET", "/api/admin/keys"),
        ("POST", "/api/admin/keys"),
        ("GET", "/api/admin/logs"),
        ("GET", "/api/admin/settings"),
        ("PUT", "/api/admin/settings"),
        ("GET", "/api/admin/blocklist"),
        ("POST", "/api/admin/blocklist"),
    ]
    for method, path in endpoints:
        resp = client.request(method, path)
        assert resp.status_code == 401, f"{method} {path} should be 401 without auth"

    resp = client.get("/api/admin/overview", auth=("admin", "wrongpassword"))
    assert resp.status_code == 401


# 2. Keys CRUD & Activity
def test_keys_crud_and_activity(client, temp_db):
    # Create key
    create_resp = client.post(
        "/api/admin/keys",
        json={"name": "test-key-1", "rate_limit": 100},
        auth=ADMIN_AUTH,
    )
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["name"] == "test-key-1"
    assert created_data["rate_limit"] == 100
    assert created_data["is_active"] is True
    assert "raw_key" in created_data
    assert created_data["raw_key"].startswith("sk_live_")
    key_id = created_data["id"]

    # List keys
    list_resp = client.get("/api/admin/keys", auth=ADMIN_AUTH)
    assert list_resp.status_code == 200
    keys = list_resp.json()
    assert len(keys) == 1
    assert keys[0]["id"] == key_id
    assert keys[0]["name"] == "test-key-1"
    assert "raw_key" not in keys[0]
    assert "key_hash" not in keys[0]

    # Patch key (disable)
    patch_resp = client.patch(
        f"/api/admin/keys/{key_id}",
        json={"is_active": False, "rate_limit": 50},
        auth=ADMIN_AUTH,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json() == {"success": True, "key_id": key_id}

    # Verify update
    list_resp = client.get("/api/admin/keys", auth=ADMIN_AUTH)
    assert list_resp.json()[0]["is_active"] is False
    assert list_resp.json()[0]["rate_limit"] == 50

    # Patch key rate_limit to None
    patch_resp_none = client.patch(
        f"/api/admin/keys/{key_id}",
        json={"rate_limit": None},
        auth=ADMIN_AUTH,
    )
    assert patch_resp_none.status_code == 200
    list_resp = client.get("/api/admin/keys", auth=ADMIN_AUTH)
    assert list_resp.json()[0]["rate_limit"] is None

    # Patch non-existent key
    patch_404 = client.patch(
        "/api/admin/keys/99999",
        json={"is_active": True},
        auth=ADMIN_AUTH,
    )
    assert patch_404.status_code == 404

    # Key activity
    activity_resp = client.get(f"/api/admin/keys/{key_id}/activity", auth=ADMIN_AUTH)
    assert activity_resp.status_code == 200
    activity = activity_resp.json()
    assert "total_requests" in activity
    assert "timeseries_24h" in activity
    assert "recent_logs" in activity
    assert len(activity["timeseries_24h"]) == 24

    # Key activity 404
    act_404 = client.get("/api/admin/keys/99999/activity", auth=ADMIN_AUTH)
    assert act_404.status_code == 404

    # Delete key
    del_resp = client.delete(f"/api/admin/keys/{key_id}", auth=ADMIN_AUTH)
    assert del_resp.status_code == 200
    assert del_resp.json() == {"success": True}

    # Delete non-existent key
    del_404 = client.delete(f"/api/admin/keys/{key_id}", auth=ADMIN_AUTH)
    assert del_404.status_code == 404


# 3. Overview Endpoint
def test_overview_endpoint(client, temp_db):
    resp = client.get("/api/admin/overview", auth=ADMIN_AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_requests" in data
    assert "total_input_tokens" in data
    assert "total_output_tokens" in data
    assert "avg_latency_ms" in data
    assert "error_rate_pct" in data
    assert "active_keys" in data
    assert "blocked_ips_count" in data
    assert "timeseries_24h" in data
    assert len(data["timeseries_24h"]) == 24


# 4. Health Endpoint
def test_health_endpoint(client, temp_db):
    resp = client.get("/api/admin/health", auth=ADMIN_AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert "model_loaded" in data
    assert data["model_id"] == settings.laya_model_id
    assert data["device"] == settings.laya_device
    assert "memory_rss_mb" in data
    assert isinstance(data["memory_rss_mb"], (int, float))
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0
    assert "database_size_bytes" in data
    assert isinstance(data["database_size_bytes"], int)


# 5. Logs Endpoint
def test_logs_endpoint(client, temp_db):
    # Add dummy logs
    db.record_request_log("/v1/system-one", "POST", 200, 45.2, "10.0.0.1", None, 10, 20, db_path=temp_db)
    db.record_request_log("/v1/system-one", "POST", 500, 10.0, "10.0.0.2", None, 5, 0, db_path=temp_db)

    # All logs
    resp = client.get("/api/admin/logs?page=1&limit=10", auth=ADMIN_AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert data["page"] == 1
    assert data["limit"] == 10
    assert data["pages"] >= 1
    assert len(data["items"]) >= 2

    # Filter status code
    resp_filtered = client.get("/api/admin/logs?status_code=500", auth=ADMIN_AUTH)
    assert resp_filtered.status_code == 200
    data_500 = resp_filtered.json()
    assert all(item["status_code"] == 500 for item in data_500["items"])

    # Filter IP
    resp_ip = client.get("/api/admin/logs?ip=10.0.0.1", auth=ADMIN_AUTH)
    assert resp_ip.status_code == 200
    data_ip = resp_ip.json()
    assert all(item["ip_address"] == "10.0.0.1" for item in data_ip["items"])

    # Filter api_key_id
    resp_no_key = client.get("/api/admin/logs?api_key_id=99999", auth=ADMIN_AUTH)
    assert resp_no_key.status_code == 200
    assert resp_no_key.json()["total"] == 0


# 6. Settings Endpoints
def test_settings_endpoints(client, temp_db):
    # Get settings
    resp = client.get("/api/admin/settings", auth=ADMIN_AUTH)
    assert resp.status_code == 200
    settings_data = resp.json()
    assert "public_rate_limit_requests" in settings_data
    assert "public_rate_limit_window_seconds" in settings_data

    # Update settings
    update_resp = client.put(
        "/api/admin/settings",
        json={"rate_limit_requests": 42, "rate_limit_window_seconds": 120},
        auth=ADMIN_AUTH,
    )
    assert update_resp.status_code == 200

    # Verify update
    resp2 = client.get("/api/admin/settings", auth=ADMIN_AUTH)
    assert resp2.status_code == 200
    updated_data = resp2.json()
    assert updated_data["public_rate_limit_requests"] == "42"
    assert updated_data["public_rate_limit_window_seconds"] == "120"


# 7. Blocklist Endpoints
def test_blocklist_endpoints(client, temp_db):
    # Add to blocklist
    resp = client.post(
        "/api/admin/blocklist",
        json={"ip_address": "192.168.1.50", "reason": "test spam"},
        auth=ADMIN_AUTH,
    )
    assert resp.status_code == 201
    assert resp.json() == {"success": True, "ip_address": "192.168.1.50"}

    # Duplicate block
    dup_resp = client.post(
        "/api/admin/blocklist",
        json={"ip_address": "192.168.1.50", "reason": "duplicate"},
        auth=ADMIN_AUTH,
    )
    assert dup_resp.status_code == 409

    # List blocklist
    list_resp = client.get("/api/admin/blocklist", auth=ADMIN_AUTH)
    assert list_resp.status_code == 200
    blocked = list_resp.json()
    assert any(item["ip_address"] == "192.168.1.50" for item in blocked)

    # Delete from blocklist
    del_resp = client.delete("/api/admin/blocklist/192.168.1.50", auth=ADMIN_AUTH)
    assert del_resp.status_code == 200
    assert del_resp.json() == {"success": True}

    # Delete non-existent
    del_404 = client.delete("/api/admin/blocklist/192.168.1.50", auth=ADMIN_AUTH)
    assert del_404.status_code == 404
