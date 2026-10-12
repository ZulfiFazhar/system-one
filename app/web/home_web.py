from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.core.models_meta import get_model_by_slug

router = APIRouter()

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "index.html"
_TEMPLATE_CACHE: str | None = None

MODEL_DETAIL_TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent / "templates" / "model_detail.html"
)
_MODEL_DETAIL_TEMPLATE_CACHE: str | None = None


def get_template_content() -> str:
    global _TEMPLATE_CACHE
    if settings.is_development or _TEMPLATE_CACHE is None:
        _TEMPLATE_CACHE = TEMPLATE_PATH.read_text(encoding="utf-8")
    return _TEMPLATE_CACHE


def get_model_detail_content(model: dict[str, Any]) -> str:
    global _MODEL_DETAIL_TEMPLATE_CACHE
    if MODEL_DETAIL_TEMPLATE_PATH.exists():
        if settings.is_development or _MODEL_DETAIL_TEMPLATE_CACHE is None:
            _MODEL_DETAIL_TEMPLATE_CACHE = MODEL_DETAIL_TEMPLATE_PATH.read_text(
                encoding="utf-8"
            )
        # ponytail: simple string/jinja template render; upgrade when layout inheritance needed
        try:
            import jinja2

            return jinja2.Template(_MODEL_DETAIL_TEMPLATE_CACHE).render(
                model=model, **model
            )
        except Exception:
            return _MODEL_DETAIL_TEMPLATE_CACHE

    display_name = model.get("display_name", model.get("name", ""))
    creator = model.get("creator", "")
    name = model.get("name", "")
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        f"<head><title>{display_name}</title></head>\n"
        "<body>\n"
        f"    <h1>{display_name}</h1>\n"
        f"    <p>Creator: {creator}</p>\n"
        f"    <p>Model: {name}</p>\n"
        "</body>\n"
        "</html>"
    )


@router.get("/", response_class=HTMLResponse)
async def home() -> HTMLResponse:
    return HTMLResponse(content=get_template_content(), status_code=200)


@router.get("/{creator}/{model_name}", response_class=HTMLResponse)
async def model_detail(
    creator: str, model_name: str, request: Request
) -> Response:
    if creator == "admin" and model_name == "login":
        from app.web.admin_web import admin_login_page

        return await admin_login_page(request)

    model = get_model_by_slug(creator, model_name)
    if not model:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{creator}/{model_name}' not found",
        )

    return HTMLResponse(content=get_model_detail_content(model), status_code=200)

