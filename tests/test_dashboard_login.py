import pytest
from fastapi.testclient import TestClient

from app.core import db
from app.core.config import settings
from app.core.security import (
    create_admin_session_token,
    refresh_security_caches,
    reset_rate_limits,
)
from app.core.server import create_application


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_dashboard_login.db")
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


def test_dashboard_unauthenticated_redirects_to_login(client):
    # Direct access to /dashboard without cookie redirects to /login
    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"

    # Legacy /admin redirects to /dashboard
    resp_admin = client.get("/admin", follow_redirects=False)
    assert resp_admin.status_code == 303
    assert resp_admin.headers["location"] == "/dashboard"

    # Legacy /admin/login redirects to /login
    resp_legacy_login = client.get("/admin/login", follow_redirects=False)
    assert resp_legacy_login.status_code == 303
    assert resp_legacy_login.headers["location"] == "/login"


def test_login_page_renders_with_default_creds_hint(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "Dashboard Sign In" in resp.text
    assert '<form id="login-form"' in resp.text
    # Creds are default ("admin" / "changeme"), verify hint is present
    assert "Default Credentials Active" in resp.text
    assert "admin" in resp.text
    assert "changeme" in resp.text


def test_login_page_renders_without_hint_when_creds_changed(temp_db, monkeypatch):
    monkeypatch.setattr(settings, "admin_username", "custom_admin")
    monkeypatch.setattr(settings, "admin_password", "strong_secret_pwd_99")
    app = create_application()
    client = TestClient(app)

    resp = client.get("/login")
    assert resp.status_code == 200
    assert "Default Credentials Active" not in resp.text


def test_login_failure(client):
    # Bad JSON credentials
    resp = client.post(
        "/login",
        json={"username": "admin", "password": "wrongpassword"},
    )
    assert resp.status_code == 401
    assert "admin_session" not in resp.cookies

    # Bad Form credentials
    resp_form = client.post(
        "/login",
        data={"username": "admin", "password": "wrongpassword"},
    )
    assert resp_form.status_code == 401
    assert "admin_session" not in resp_form.cookies

    # Bad username
    resp_user = client.post(
        "/login",
        json={"username": "wronguser", "password": "changeme"},
    )
    assert resp_user.status_code == 401
    assert "admin_session" not in resp_user.cookies


def test_login_success_and_dashboard_warning_modal(client):
    # JSON login
    resp = client.post(
        "/login",
        json={"username": "admin", "password": "changeme"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"success": True, "redirect": "/dashboard"}
    assert "admin_session" in resp.cookies
    token = resp.cookies["admin_session"]

    # Access /dashboard with cookie
    client_auth = TestClient(client.app)
    client_auth.cookies["admin_session"] = token
    resp_dashboard = client_auth.get("/dashboard")
    assert resp_dashboard.status_code == 200
    assert "text/html" in resp_dashboard.headers.get("content-type", "")
    # Since creds are still default, warning modal must be present
    assert "SECURITY WARNING: DEFAULT CREDENTIALS IN USE" in resp_dashboard.text

    # Access /login when already authenticated redirects to /dashboard
    resp_login = client_auth.get("/login", follow_redirects=False)
    assert resp_login.status_code == 303
    assert resp_login.headers["location"] == "/dashboard"

    # Form login also works
    client_form = TestClient(client.app)
    resp_form = client_form.post(
        "/login",
        data={"username": "admin", "password": "changeme"},
    )
    assert resp_form.status_code == 200
    assert resp_form.json() == {"success": True, "redirect": "/dashboard"}
    assert "admin_session" in resp_form.cookies


def test_dashboard_modal_hidden_when_creds_changed(temp_db, monkeypatch):
    monkeypatch.setattr(settings, "admin_username", "custom_admin")
    monkeypatch.setattr(settings, "admin_password", "strong_secret_pwd_99")
    app = create_application()
    client = TestClient(app)

    token = create_admin_session_token("custom_admin")
    client.cookies["admin_session"] = token
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    # Creds are custom, warning modal must NOT be rendered
    assert "SECURITY WARNING: DEFAULT CREDENTIALS IN USE" not in resp.text


def test_logout(client):
    # Login first
    login_resp = client.post(
        "/login",
        json={"username": "admin", "password": "changeme"},
    )
    assert login_resp.status_code == 200
    assert "admin_session" in client.cookies

    # Logout
    logout_resp = client.post("/logout")
    assert logout_resp.status_code == 200
    assert logout_resp.json() == {"success": True, "redirect": "/login"}
    assert client.cookies.get("admin_session") is None

    # Subsequent GET /dashboard redirects to /login
    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_api_admin_dual_auth(client):
    # 1. HTTP Basic auth succeeds
    resp_basic = client.get("/api/admin/overview", auth=("admin", "changeme"))
    assert resp_basic.status_code == 200
    assert "total_requests" in resp_basic.json()

    # 2. admin_session cookie succeeds without basic auth
    token = create_admin_session_token("admin")
    client_cookie = TestClient(client.app)
    client_cookie.cookies["admin_session"] = token
    resp_cookie = client_cookie.get("/api/admin/overview")
    assert resp_cookie.status_code == 200
    assert "total_requests" in resp_cookie.json()

    # 3. Unauthenticated fails with 401
    resp_unauth = client.get("/api/admin/overview")
    assert resp_unauth.status_code == 401
