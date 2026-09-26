import sqlite3
import time
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core import db
from app.core.security import reset_rate_limits, refresh_security_caches
from app.core.server import create_application


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_logging.db")
    db.init_db(db_path)
    monkeypatch.setattr(settings, "database_path", db_path)
    reset_rate_limits()
    refresh_security_caches(db_path)
    return db_path


@pytest.fixture
def client(test_app, temp_db):
    return TestClient(test_app)


def test_logging_middleware_records_endpoint_and_latency(client, temp_db):
    resp = client.get("/health")
    assert resp.status_code == 200

    rows, total = db.get_request_logs(db_path=temp_db)
    assert total >= 1
    log = rows[0]
    assert log["endpoint"] == "/health"
    assert log["method"] == "GET"
    assert log["status_code"] == 200
    assert log["latency_ms"] >= 0.0
    assert log["ip_address"] == "testclient"
    assert log["api_key_id"] is None
    assert log["input_tokens"] == 0
    assert log["output_tokens"] == 0


def test_logging_middleware_records_404_endpoint(client, temp_db):
    resp = client.get("/healthz")
    assert resp.status_code == 404

    rows, total = db.get_request_logs(db_path=temp_db)
    healthz_logs = [r for r in rows if r["endpoint"] == "/healthz"]
    assert len(healthz_logs) == 1
    log = healthz_logs[0]
    assert log["status_code"] == 404
    assert log["method"] == "GET"
    assert log["latency_ms"] >= 0.0


def test_logging_middleware_systemone_tokens_and_api_key(client, temp_db):
    key_id, raw_key, _ = db.create_api_key("Logging Test Key", db_path=temp_db)
    payload = {
        "state": "I need a full refund for my subscription",
        "questions": {
            "refund": {
                "type": "noul",
                "instructions": "Is customer asking for a refund?",
            }
        },
    }
    headers = {"Authorization": f"Bearer {raw_key}"}

    resp = client.post("/v1/systemone", json=payload, headers=headers)
    assert resp.status_code == 200

    rows, total = db.get_request_logs(api_key_id=key_id, db_path=temp_db)
    assert total == 1
    log = rows[0]
    assert log["endpoint"] == "/v1/systemone"
    assert log["method"] == "POST"
    assert log["status_code"] == 200
    assert log["api_key_id"] == key_id
    assert log["input_tokens"] > 0
    assert log["output_tokens"] > 0
    assert log["latency_ms"] >= 0.0


def test_logging_error_does_not_crash_response(client, temp_db, monkeypatch):
    def faulty_record(*args, **kwargs):
        raise sqlite3.OperationalError("disk failure mock")

    monkeypatch.setattr("app.core.middleware.record_request_log", faulty_record)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


def test_lifespan_prunes_old_logs(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test_lifespan_prune.db")
    db.init_db(db_path)
    monkeypatch.setattr(settings, "database_path", db_path)

    conn = db.get_db_connection(db_path)
    old_ts = time.time() - (35 * 86400)
    conn.execute(
        """
        INSERT INTO request_logs (timestamp, endpoint, method, status_code, latency_ms, ip_address)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (old_ts, "/old-call", "GET", 200, 12.5, "127.0.0.1"),
    )
    conn.commit()
    conn.close()

    app = create_application()
    with TestClient(app):
        pass

    conn = db.get_db_connection(db_path)
    count = conn.execute(
        "SELECT COUNT(*) FROM request_logs WHERE endpoint = '/old-call'"
    ).fetchone()[0]
    conn.close()
    assert count == 0
