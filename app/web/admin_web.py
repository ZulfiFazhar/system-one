import secrets
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.core.config import settings
from app.core.security import create_admin_session_token, verify_admin_cookie

router = APIRouter()

DASHBOARD_TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent / "templates" / "dashboard.html"
)
_DASHBOARD_TEMPLATE_CACHE: str | None = None

LOGIN_TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent / "templates" / "login.html"
)
_LOGIN_TEMPLATE_CACHE: str | None = None


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
                "    <title>Admin Sign In</title>\n"
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


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request) -> Response:
    if verify_admin_cookie(request) is None:
        return RedirectResponse(
            url="/admin/login",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return HTMLResponse(content=get_dashboard_template_content(), status_code=200)


@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request) -> Response:
    if verify_admin_cookie(request) is not None:
        return RedirectResponse(
            url="/admin",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return HTMLResponse(content=get_login_template_content(), status_code=200)


@router.post("/admin/login")
async def admin_login(request: Request) -> JSONResponse:
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
    res = JSONResponse(content={"success": True, "redirect": "/admin"})
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


@router.post("/admin/logout")
async def admin_logout() -> JSONResponse:
    res = JSONResponse(content={"success": True, "redirect": "/admin/login"})
    res.delete_cookie(key="admin_session", path="/")
    return res
