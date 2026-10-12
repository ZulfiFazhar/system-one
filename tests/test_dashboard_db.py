import os
import sqlite3
import time
import pytest
from app.core.config import settings
from app.core import db


@pytest.fixture
def temp_db(tmp_path):
    db_path = str(tmp_path / "test_dashboard.db")
    db.init_db(db_path)
    return db_path


def test_config_settings_defaults():
    assert hasattr(settings, "admin_username")
    assert settings.admin_username == "admin"
    assert hasattr(settings, "admin_password")
    assert settings.admin_password == "changeme"
    assert hasattr(settings, "database_path")
    assert settings.database_path == "data/dashboard.db"


def test_init_db_creates_tables_and_defaults(temp_db):
    conn = db.get_db_connection(temp_db)
    cursor = conn.cursor()

    tables = {
        row[0]
        for row in cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "api_keys" in tables
    assert "request_logs" in tables
    assert "ip_blocklist" in tables
    assert "system_settings" in tables

    # Verify default system settings
    settings_dict = db.get_system_settings(temp_db)
    assert settings_dict.get("public_rate_limit_requests") == "10"
    assert settings_dict.get("public_rate_limit_window_seconds") == "60"

    # Verify admin password in db is hashed
    assert settings_dict.get("admin_username") == "admin"
    admin_pwd_hash = settings_dict.get("admin_password")
    assert admin_pwd_hash is not None
    assert admin_pwd_hash.startswith("pbkdf2:sha256:")
    assert db.verify_password("changeme", admin_pwd_hash)
    assert not db.verify_password("wrongpassword", admin_pwd_hash)

    # Idempotent init_db call
    db.init_db(temp_db)
    conn.close()


def test_get_db_connection_pragmas(temp_db):
    conn = db.get_db_connection(temp_db)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys")
    fk = cursor.fetchone()[0]
    assert fk == 1
    cursor.execute("PRAGMA busy_timeout")
    timeout = cursor.fetchone()[0]
    assert timeout >= 5000
    conn.close()


def test_api_key_lifecycle(temp_db):
    # 1. Create key
    key_id, raw_key, prefix = db.create_api_key(
        name="Test Service", rate_limit=100, db_path=temp_db
    )
    assert key_id > 0
    assert raw_key.startswith("sk_live_")
    assert len(prefix) == 16
    assert prefix == raw_key[:16]

    # 2. Hash key & fetch
    key_hash = db.hash_key(raw_key)
    key_data = db.get_api_key_by_hash(key_hash, db_path=temp_db)
    assert key_data is not None
    assert key_data["id"] == key_id
    assert key_data["name"] == "Test Service"
    assert key_data["key_prefix"] == prefix
    assert key_data["rate_limit"] == 100
    assert key_data["is_active"] == 1
    assert key_data["last_used_at"] is None

    # Fetch with invalid hash
    assert db.get_api_key_by_hash("nonexistent_hash", db_path=temp_db) is None

    # 3. List keys
    keys = db.list_api_keys(db_path=temp_db)
    assert len(keys) == 1
    assert keys[0]["id"] == key_id
    assert keys[0]["name"] == "Test Service"

    # 4. Update key
    updated = db.update_api_key(
        key_id, is_active=False, rate_limit=200, db_path=temp_db
    )
    assert updated is True
    updated_key = db.get_api_key_by_hash(key_hash, db_path=temp_db)
    assert updated_key["is_active"] == 0
    assert updated_key["rate_limit"] == 200

    # Non-existent key update returns False
    assert (
        db.update_api_key(99999, is_active=True, db_path=temp_db) is False
    )

    # 5. Delete key
    deleted = db.delete_api_key(key_id, db_path=temp_db)
    assert deleted is True
    assert db.get_api_key_by_hash(key_hash, db_path=temp_db) is None
    assert db.delete_api_key(key_id, db_path=temp_db) is False


def test_request_logs_and_pagination(temp_db):
    key_id, raw_key, prefix = db.create_api_key("Client App", db_path=temp_db)

    # Record logs
    now = time.time()
    for i in range(15):
        status = 200 if i % 3 != 0 else 500
        ip = "192.168.1.10" if i % 2 == 0 else "10.0.0.1"
        kid = key_id if i < 10 else None
        db.record_request_log(
            endpoint="/api/v1/systemone",
            method="POST",
            status_code=status,
            latency_ms=45.5 + i,
            ip_address=ip,
            api_key_id=kid,
            input_tokens=100 + i,
            output_tokens=50 + i,
            db_path=temp_db,
        )

    # Check api_key last_used_at was updated
    key_hash = db.hash_key(raw_key)
    key_row = db.get_api_key_by_hash(key_hash, db_path=temp_db)
    assert key_row["last_used_at"] is not None

    # Get page 1 (limit 10)
    logs_p1, total = db.get_request_logs(page=1, limit=10, db_path=temp_db)
    assert total == 15
    assert len(logs_p1) == 10
    # Should be ordered descending by timestamp
    assert logs_p1[0]["timestamp"] >= logs_p1[-1]["timestamp"]

    # Get page 2
    logs_p2, total2 = db.get_request_logs(page=2, limit=10, db_path=temp_db)
    assert total2 == 15
    assert len(logs_p2) == 5

    # Filter by status_code
    error_logs, error_total = db.get_request_logs(
        status_code=500, db_path=temp_db
    )
    assert error_total == 5
    assert all(l["status_code"] == 500 for l in error_logs)

    # Filter by IP
    ip_logs, ip_total = db.get_request_logs(
        ip_address="192.168.1.10", db_path=temp_db
    )
    assert ip_total == 8
    assert all(l["ip_address"] == "192.168.1.10" for l in ip_logs)

    # Filter by api_key_id
    key_logs, key_total = db.get_request_logs(api_key_id=key_id, db_path=temp_db)
    assert key_total == 10
    assert all(l["api_key_id"] == key_id for l in key_logs)


def test_delete_api_key_sets_logs_foreign_key_null(temp_db):
    key_id, raw_key, prefix = db.create_api_key("Temp App", db_path=temp_db)
    db.record_request_log(
        endpoint="/api/v1/systemone",
        method="POST",
        status_code=200,
        latency_ms=30.0,
        ip_address="127.0.0.1",
        api_key_id=key_id,
        db_path=temp_db,
    )

    db.delete_api_key(key_id, db_path=temp_db)
    logs, total = db.get_request_logs(db_path=temp_db)
    assert total == 1
    assert logs[0]["api_key_id"] is None


def test_overview_metrics_and_key_activity(temp_db):
    key_id1, _, _ = db.create_api_key("Service A", db_path=temp_db)
    key_id2, _, _ = db.create_api_key("Service B", db_path=temp_db)

    # Empty metrics
    empty_metrics = db.get_overview_metrics(db_path=temp_db)
    assert empty_metrics["total_requests"] == 0
    assert empty_metrics["total_input_tokens"] == 0
    assert empty_metrics["total_output_tokens"] == 0
    assert empty_metrics["avg_latency_ms"] == 0.0
    assert empty_metrics["error_rate_pct"] == 0.0
    assert empty_metrics["active_keys"] == 2
    assert empty_metrics["blocked_ips_count"] == 0

    # Add blocked IP
    db.add_blocked_ip("203.0.113.1", reason="Abuse", db_path=temp_db)

    # Record some requests
    # 3 requests for key 1: two 200s (latency 10ms, 20ms), one 500 (latency 30ms)
    db.record_request_log(
        "/api/v1/systemone", "POST", 200, 10.0, "127.0.0.1", key_id1, 10, 20, temp_db
    )
    db.record_request_log(
        "/api/v1/systemone", "POST", 200, 20.0, "127.0.0.1", key_id1, 15, 25, temp_db
    )
    db.record_request_log(
        "/api/v1/systemone", "POST", 500, 30.0, "127.0.0.1", key_id1, 5, 0, temp_db
    )

    # 1 request for key 2: one 200 (latency 40ms)
    db.record_request_log(
        "/api/v1/systemone", "POST", 200, 40.0, "127.0.0.2", key_id2, 50, 100, temp_db
    )

    overview = db.get_overview_metrics(db_path=temp_db)
    assert overview["total_requests"] == 4
    assert overview["total_input_tokens"] == 80
    assert overview["total_output_tokens"] == 145
    assert overview["avg_latency_ms"] == 25.0  # (10 + 20 + 30 + 40) / 4
    assert overview["error_rate_pct"] == 25.0  # 1 out of 4 is error
    assert overview["active_keys"] == 2
    assert overview["blocked_ips_count"] == 1

    # Key activity for non-existent key
    assert db.get_key_activity(99999, db_path=temp_db) is None

    # Key activity for key 1
    activity1 = db.get_key_activity(key_id1, db_path=temp_db)
    assert activity1 is not None
    assert activity1["total_requests"] == 3
    assert activity1["total_input_tokens"] == 30
    assert activity1["total_output_tokens"] == 45
    assert activity1["avg_latency_ms"] == 20.0  # (10 + 20 + 30) / 3
    assert abs(activity1["error_rate_pct"] - 33.33) < 0.1
    assert "timeseries_24h" in activity1
    assert isinstance(activity1["timeseries_24h"], list)
    assert len(activity1["timeseries_24h"]) == 24
    assert "recent_logs" in activity1
    assert len(activity1["recent_logs"]) == 3


def test_system_settings_crud(temp_db):
    settings_dict = db.get_system_settings(temp_db)
    assert "public_rate_limit_requests" in settings_dict
    assert "public_rate_limit_window_seconds" in settings_dict

    db.update_system_settings(
        {
            "public_rate_limit_requests": "25",
            "custom_banner": "Maintenance at midnight",
        },
        db_path=temp_db,
    )

    updated = db.get_system_settings(temp_db)
    assert updated["public_rate_limit_requests"] == "25"
    assert updated["public_rate_limit_window_seconds"] == "60"
    assert updated["custom_banner"] == "Maintenance at midnight"


def test_ip_blocklist(temp_db):
    assert db.get_blocked_ips(temp_db) == []

    # Add IP
    assert db.add_blocked_ip("198.51.100.5", reason="Malicious scanner", db_path=temp_db) is True
    # Duplicate IP returns False
    assert db.add_blocked_ip("198.51.100.5", reason="Duplicate", db_path=temp_db) is False

    blocked = db.get_blocked_ips(temp_db)
    assert len(blocked) == 1
    assert blocked[0]["ip_address"] == "198.51.100.5"
    assert blocked[0]["reason"] == "Malicious scanner"

    # Remove IP
    assert db.remove_blocked_ip("198.51.100.5", db_path=temp_db) is True
    assert db.remove_blocked_ip("198.51.100.5", db_path=temp_db) is False
    assert db.get_blocked_ips(temp_db) == []


def test_prune_old_logs(temp_db):
    conn = db.get_db_connection(temp_db)
    now = time.time()
    old_time = now - (35 * 86400)  # 35 days ago
    recent_time = now - (10 * 86400)  # 10 days ago

    cursor = conn.cursor()
    # Insert 3 old logs and 2 recent logs directly
    for _ in range(3):
        cursor.execute(
            """
            INSERT INTO request_logs (timestamp, endpoint, method, status_code, latency_ms, ip_address)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (old_time, "/api/v1/systemone", "POST", 200, 25.0, "127.0.0.1"),
        )
    for _ in range(2):
        cursor.execute(
            """
            INSERT INTO request_logs (timestamp, endpoint, method, status_code, latency_ms, ip_address)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (recent_time, "/api/v1/systemone", "POST", 200, 25.0, "127.0.0.1"),
        )
    conn.commit()
    conn.close()

    deleted = db.prune_old_logs(days=30, db_path=temp_db)
    assert deleted == 3

    logs, total = db.get_request_logs(db_path=temp_db)
    assert total == 2
