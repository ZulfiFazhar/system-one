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
    db_path = str(tmp_path / "test_dashboard_ui.db")
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


def test_admin_ui_unauthenticated_redirects_to_login(client):
    resp = client.get("/admin", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers.get("location") == "/admin/login"


def test_admin_login_page_renders_html(client):
    resp = client.get("/admin/login")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    html = resp.text
    assert "System One" in html
    assert "Admin Console Authentication" in html
    assert "username-input" in html
    assert "password-input" in html
    assert "login-form" in html


def test_admin_ui_authenticated_with_session_cookie(client):
    token = create_admin_session_token("admin")
    client.cookies["admin_session"] = token
    resp = client.get("/admin")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")

    html = resp.text
    # Core headings / titles & logout button
    assert "System One" in html
    assert "Admin Dashboard" in html
    assert "logout-btn" in html

    # Tab navigation elements
    assert "Overview &amp; Health" in html or "Overview & Health" in html
    assert "API Keys &amp; Activity" in html or "API Keys & Activity" in html
    assert "Rate Limits &amp; Blocklist" in html or "Rate Limits & Blocklist" in html
    assert "Live Request Logs" in html
    assert "Playground" in html

    # Tab 1: Overview & System Health
    assert "kpi-total-requests" in html
    assert "kpi-error-rate" in html
    assert "kpi-avg-latency" in html
    assert "kpi-total-tokens" in html
    assert "kpi-active-keys" in html
    assert "kpi-blocked-ips" in html
    assert "overview-traffic-chart" in html
    assert "diag-model-status" in html
    assert "diag-device" in html

    # Tab 2: API Keys & Activity Drawer
    assert "Generate Key" in html
    assert "key-create-modal" in html
    assert "raw-key-display" in html
    assert "copy-raw-key-btn" in html
    assert "key-activity-drawer" in html
    assert "drawer-activity-chart" in html

    # Tab 3: Rate Limits & IP Blocklist
    assert "Public Rate Limiting" in html
    assert "rate-limit-requests-input" in html
    assert "rate-limit-window-input" in html
    assert "IP Blocklist" in html
    assert "block-ip-input" in html

    # Tab 4: Live Request Logs
    assert "logs-status-filter" in html
    assert "logs-ip-filter" in html
    assert "logs-auto-refresh-toggle" in html
    assert "logs-table-body" in html

    # Tab 5: Playground
    assert "Customer Support (Noul)" in html
    assert "Topic Routing (Choice)" in html
    assert "Incident Severity (Score)" in html
    assert "pg-auth-select" in html
    assert "pg-state-input" in html
    assert "pg-questions-input" in html
    assert "pg-send-btn" in html
    assert "pg-raw-output" in html

    # Essential script tags / CDNs
    assert "cdn.tailwindcss.com" in html
    assert "chart.js" in html.lower()


def test_admin_ui_trailing_slash_redirect(client):
    token = create_admin_session_token("admin")
    client.cookies["admin_session"] = token
    resp = client.get("/admin/", follow_redirects=True)
    assert resp.status_code == 200
    assert "Admin Dashboard" in resp.text
