import secrets
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from jinja2 import Template

from app.core.config import settings
from app.core.security import (
    check_ip_blocklist,
    check_rate_limit,
    create_admin_session_token,
    verify_admin_cookie,
)

router = APIRouter()

DASHBOARD_TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent / "templates" / "dashboard.html"
)
_DASHBOARD_TEMPLATE_CACHE: str | None = None

LOGIN_TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent / "templates" / "login.html"
)
_LOGIN_TEMPLATE_CACHE: str | None = None


def is_default_credentials() -> bool:
    return settings.admin_username == "admin" and settings.admin_password == "changeme"


def get_dashboard_template_content() -> str:
    global _DASHBOARD_TEMPLATE_CACHE
    if settings.is_development or _DASHBOARD_TEMPLATE_CACHE is None:
        _DASHBOARD_TEMPLATE_CACHE = DASHBOARD_TEMPLATE_PATH.read_text(encoding="utf-8")
    return _DASHBOARD_TEMPLATE_CACHE


def get_login_template_content() -> str:
    global _LOGIN_TEMPLATE_CACHE
    if settings.is_development or _LOGIN_TEMPLATE_CACHE is None:
        if LOGIN_TEMPLATE_PATH.exists():
            _LOGIN_TEMPLATE_CACHE = LOGIN_TEMPLATE_PATH.read_text(encoding="utf-8")
        else:
            _LOGIN_TEMPLATE_CACHE = (
                "<!DOCTYPE html>\n"
                '<html lang="en">\n'
                "<head>\n"
                '    <meta charset="UTF-8">\n'
                "    <title>Dashboard Sign In</title>\n"
                "</head>\n"
                "<body>\n"
                '    <form id="login-form">\n'
                '        <input type="text" name="username" placeholder="Username" required />\n'
                '        <input type="password" name="password" placeholder="Password" required />\n'
                '        <button type="submit">Sign In</button>\n'
                "    </form>\n"
                "</body>\n"
                "</html>"
            )
    return _LOGIN_TEMPLATE_CACHE


def render_dashboard_html() -> str:
    content = get_dashboard_template_content()
    return Template(content).render(is_default_creds=is_default_credentials())


def render_login_html() -> str:
    content = get_login_template_content()
    return Template(content).render(is_default_creds=is_default_credentials())


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request) -> Response:
    if verify_admin_cookie(request) is None:
        return RedirectResponse(
            url="/login",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return HTMLResponse(content=render_dashboard_html(), status_code=200)


@router.get("/admin", response_class=HTMLResponse)
async def admin_redirect() -> Response:
    return RedirectResponse(
        url="/dashboard",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> Response:
    if verify_admin_cookie(request) is not None:
        return RedirectResponse(
            url="/dashboard",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return HTMLResponse(content=render_login_html(), status_code=200)


@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_redirect() -> Response:
    return RedirectResponse(
        url="/login",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/dashboard/login", response_class=HTMLResponse)
async def dashboard_login_redirect() -> Response:
    return RedirectResponse(
        url="/login",
        status_code=status.HTTP_303_SEE_OTHER,
    )


async def handle_login(request: Request) -> JSONResponse:
    client_ip = request.client.host if request.client else "127.0.0.1"
    check_ip_blocklist(client_ip)
    check_rate_limit(client_ip)

    username = ""
    password = ""
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        try:
            body = await request.json()
            if isinstance(body, dict):
                username = str(body.get("username", ""))
                password = str(body.get("password", ""))
        except Exception:
            pass
    else:
        try:
            form = await request.form()
            username = str(form.get("username", ""))
            password = str(form.get("password", ""))
        except Exception:
            pass
        if not username and not password:
            try:
                body = await request.json()
                if isinstance(body, dict):
                    username = str(body.get("username", ""))
                    password = str(body.get("password", ""))
            except Exception:
                pass

    is_user_valid = secrets.compare_digest(username, settings.admin_username)
    is_pass_valid = secrets.compare_digest(password, settings.admin_password)

    if not (is_user_valid and is_pass_valid):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_admin_session_token(username)
    res = JSONResponse(content={"success": True, "redirect": "/dashboard"})
    res.set_cookie(
        key="admin_session",
        value=token,
        max_age=86400,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        path="/",
    )
    return res


@router.post("/login")
async def login_post(request: Request) -> JSONResponse:
    return await handle_login(request)


@router.post("/admin/login")
async def admin_login_post(request: Request) -> JSONResponse:
    return await handle_login(request)


async def handle_logout() -> JSONResponse:
    res = JSONResponse(content={"success": True, "redirect": "/login"})
    res.delete_cookie(key="admin_session", path="/")
    return res


@router.post("/logout")
async def logout_post() -> JSONResponse:
    return await handle_logout()


@router.post("/admin/logout")
async def admin_logout_post() -> JSONResponse:
    return await handle_logout()
