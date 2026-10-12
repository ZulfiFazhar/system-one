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


def test_admin_unauthenticated_redirects_to_login(client):
    resp = client.get("/admin", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/login"


def test_admin_login_page_renders(client):
    resp = client.get("/admin/login")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "Admin Sign In" in resp.text
    assert '<form id="login-form"' in resp.text


def test_admin_login_failure(client):
    # Bad JSON credentials
    resp = client.post(
        "/admin/login",
        json={"username": "admin", "password": "wrongpassword"},
    )
    assert resp.status_code == 401
    assert "admin_session" not in resp.cookies

    # Bad Form credentials
    resp_form = client.post(
        "/admin/login",
        data={"username": "admin", "password": "wrongpassword"},
    )
    assert resp_form.status_code == 401
    assert "admin_session" not in resp_form.cookies

    # Bad username
    resp_user = client.post(
        "/admin/login",
        json={"username": "wronguser", "password": "changeme"},
    )
    assert resp_user.status_code == 401
    assert "admin_session" not in resp_user.cookies


def test_admin_login_success_and_access(client):
    # JSON login
    resp = client.post(
        "/admin/login",
        json={"username": "admin", "password": "changeme"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"success": True, "redirect": "/admin"}
    assert "admin_session" in resp.cookies
    token = resp.cookies["admin_session"]

    # Access /admin with cookie
    client_auth = TestClient(client.app)
    client_auth.cookies["admin_session"] = token
    resp_admin = client_auth.get("/admin")
    assert resp_admin.status_code == 200
    assert "text/html" in resp_admin.headers.get("content-type", "")

    # Access /admin/login when already authenticated redirects to /admin
    resp_login = client_auth.get("/admin/login", follow_redirects=False)
    assert resp_login.status_code == 303
    assert resp_login.headers["location"] == "/admin"

    # Form login also works
    client_form = TestClient(client.app)
    resp_form = client_form.post(
        "/admin/login",
        data={"username": "admin", "password": "changeme"},
    )
    assert resp_form.status_code == 200
    assert resp_form.json() == {"success": True, "redirect": "/admin"}
    assert "admin_session" in resp_form.cookies


def test_admin_logout(client):
    # Login first
    login_resp = client.post(
        "/admin/login",
        json={"username": "admin", "password": "changeme"},
    )
    assert login_resp.status_code == 200
    assert "admin_session" in client.cookies

    # Logout
    logout_resp = client.post("/admin/logout")
    assert logout_resp.status_code == 200
    assert logout_resp.json() == {"success": True, "redirect": "/admin/login"}
    assert client.cookies.get("admin_session") is None

    # Subsequent GET /admin redirects to login
    resp = client.get("/admin", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin/login"


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
