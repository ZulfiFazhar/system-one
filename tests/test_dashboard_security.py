from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBasicCredentials
from pydantic import SecretStr

from app.core.config import settings
from app.core import db
from app.core.security import (
    check_ip_blocklist,
    check_key_rate_limit,
    check_rate_limit,
    refresh_security_caches,
    reset_rate_limits,
    verify_admin_credentials,
    verify_api_key,
)


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_sec.db")
    db.init_db(db_path)
    monkeypatch.setattr(settings, "database_path", db_path)
    reset_rate_limits()
    refresh_security_caches(db_path)
    return db_path


@pytest.fixture(autouse=True)
def clean_state():
    reset_rate_limits()
    yield
    reset_rate_limits()


def make_request(ip: str = "127.0.0.1") -> SimpleNamespace:
    return SimpleNamespace(
        client=SimpleNamespace(host=ip),
        state=SimpleNamespace(api_key_id=None),
    )


# --- Admin Basic Auth Tests ---


def test_verify_admin_credentials_valid(monkeypatch):
    monkeypatch.setattr(settings, "admin_username", "superadmin")
    monkeypatch.setattr(settings, "admin_password", "topsecret")

    creds = HTTPBasicCredentials(username="superadmin", password="topsecret")
    user = verify_admin_credentials(creds)
    assert user == "superadmin"


def test_verify_admin_credentials_invalid_password(monkeypatch):
    monkeypatch.setattr(settings, "admin_username", "superadmin")
    monkeypatch.setattr(settings, "admin_password", "topsecret")

    creds = HTTPBasicCredentials(username="superadmin", password="wrongpassword")
    with pytest.raises(HTTPException) as exc_info:
        verify_admin_credentials(creds)
    assert exc_info.value.status_code == 401
    assert exc_info.value.headers.get("WWW-Authenticate") == "Basic"


def test_verify_admin_credentials_invalid_username(monkeypatch):
    monkeypatch.setattr(settings, "admin_username", "superadmin")
    monkeypatch.setattr(settings, "admin_password", "topsecret")

    creds = HTTPBasicCredentials(username="wronguser", password="topsecret")
    with pytest.raises(HTTPException) as exc_info:
        verify_admin_credentials(creds)
    assert exc_info.value.status_code == 401
    assert exc_info.value.headers.get("WWW-Authenticate") == "Basic"


def test_verify_admin_credentials_missing():
    with pytest.raises(HTTPException) as exc_info:
        verify_admin_credentials(None)
    assert exc_info.value.status_code == 401
    assert exc_info.value.headers.get("WWW-Authenticate") == "Basic"


# --- IP Blocklist Tests ---


def test_check_ip_blocklist_allowed():
    # Should not raise
    check_ip_blocklist("192.168.1.1")


def test_check_ip_blocklist_blocked(temp_db):
    db.add_blocked_ip("198.51.100.42", reason="Scanner", db_path=temp_db)
    refresh_security_caches(temp_db)

    with pytest.raises(HTTPException) as exc_info:
        check_ip_blocklist("198.51.100.42")
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Access forbidden: IP address is blocklisted"


def test_refresh_security_caches_updates_blocklist(temp_db):
    check_ip_blocklist("203.0.113.5")  # not blocked

    db.add_blocked_ip("203.0.113.5", db_path=temp_db)
    refresh_security_caches(temp_db)

    with pytest.raises(HTTPException) as exc_info:
        check_ip_blocklist("203.0.113.5")
    assert exc_info.value.status_code == 403

    db.remove_blocked_ip("203.0.113.5", db_path=temp_db)
    refresh_security_caches(temp_db)
    check_ip_blocklist("203.0.113.5")  # unblocked


# --- Dynamic Public Rate Limit Tests ---


def test_dynamic_public_rate_limit(temp_db):
    db.update_system_settings(
        {
            "public_rate_limit_requests": "2",
            "public_rate_limit_window_seconds": "60",
        },
        db_path=temp_db,
    )
    refresh_security_caches(temp_db)

    ip = "192.0.2.1"
    check_rate_limit(ip)
    check_rate_limit(ip)

    with pytest.raises(HTTPException) as exc_info:
        check_rate_limit(ip)
    assert exc_info.value.status_code == 429
    assert "Public rate limit exceeded (2 requests per 60s)" in exc_info.value.detail
    assert "Retry-After" in exc_info.value.headers


# --- Per-Key Rate Limiting Tests ---


def test_check_key_rate_limit_sliding_window():
    key_id = 99
    check_key_rate_limit(key_id, limit=2, window=60)
    check_key_rate_limit(key_id, limit=2, window=60)

    with pytest.raises(HTTPException) as exc_info:
        check_key_rate_limit(key_id, limit=2, window=60)
    assert exc_info.value.status_code == 429
    assert "API key rate limit exceeded (2 requests per 60s)" in exc_info.value.detail
    assert "Retry-After" in exc_info.value.headers

    # Other key should not be blocked
    check_key_rate_limit(key_id=100, limit=2, window=60)


# --- API Key Verification Integration Tests ---


def test_verify_api_key_blocked_ip_rejected(temp_db):
    db.add_blocked_ip("198.51.100.99", db_path=temp_db)
    refresh_security_caches(temp_db)

    req = make_request("198.51.100.99")
    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(req, None)
    assert exc_info.value.status_code == 403


def test_verify_api_key_db_active(temp_db):
    key_id, raw_key, _ = db.create_api_key("Test Client", rate_limit=None, db_path=temp_db)
    req = make_request("127.0.0.1")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=raw_key)

    verify_api_key(req, creds)
    assert req.state.api_key_id == key_id


def test_verify_api_key_db_revoked(temp_db):
    key_id, raw_key, _ = db.create_api_key("Revoked Client", rate_limit=None, db_path=temp_db)
    db.update_api_key(key_id, is_active=False, db_path=temp_db)

    req = make_request("127.0.0.1")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=raw_key)

    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(req, creds)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "API key has been revoked"


def test_verify_api_key_db_rate_limited(temp_db):
    key_id, raw_key, _ = db.create_api_key("Rate Limited Client", rate_limit=2, db_path=temp_db)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=raw_key)

    req1 = make_request("127.0.0.1")
    verify_api_key(req1, creds)
    assert req1.state.api_key_id == key_id

    req2 = make_request("127.0.0.1")
    verify_api_key(req2, creds)

    req3 = make_request("127.0.0.1")
    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(req3, creds)
    assert exc_info.value.status_code == 429
    assert "API key rate limit exceeded" in exc_info.value.detail


def test_verify_api_key_legacy_env(temp_db, monkeypatch):
    monkeypatch.setattr(settings, "laya_api_key", SecretStr("legacy-secret-key"))

    req = make_request("127.0.0.1")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="legacy-secret-key")

    verify_api_key(req, creds)
    assert req.state.api_key_id is None


def test_verify_api_key_invalid(temp_db, monkeypatch):
    monkeypatch.setattr(settings, "laya_api_key", SecretStr("legacy-secret-key"))

    req = make_request("127.0.0.1")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="completely-wrong-key")

    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(req, creds)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid API key"


def test_verify_api_key_public_unauthenticated(temp_db):
    db.update_system_settings(
        {"public_rate_limit_requests": "1", "public_rate_limit_window_seconds": "60"},
        db_path=temp_db,
    )
    refresh_security_caches(temp_db)

    req1 = make_request("10.10.10.10")
    verify_api_key(req1, None)
    assert req1.state.api_key_id is None

    req2 = make_request("10.10.10.10")
    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(req2, None)
    assert exc_info.value.status_code == 429
