from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.core.models_meta import get_model_by_slug
from app.services.models.registry import normalize_model_name

router = APIRouter()

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "index.html"
_TEMPLATE_CACHE: str | None = None

MODEL_DETAIL_TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent / "templates" / "model_detail.html"
)
_MODEL_DETAIL_TEMPLATE_CACHE: str | None = None


def get_loaded_models(app_state: Any) -> list[str]:
    loaded = list(getattr(app_state, "models", {}).keys())
    if getattr(app_state, "router", None) is not None and "laya" not in loaded:
        loaded.append("laya")
    return loaded


def get_template_content(loaded_models: list[str]) -> str:
    global _TEMPLATE_CACHE
    if settings.is_development or _TEMPLATE_CACHE is None:
        _TEMPLATE_CACHE = TEMPLATE_PATH.read_text(encoding="utf-8")
    try:
        import jinja2

        return jinja2.Template(_TEMPLATE_CACHE).render(
            loaded_models=loaded_models, settings=settings
        )
    except Exception:
        return _TEMPLATE_CACHE


def get_model_detail_content(model: dict[str, Any], is_active: bool) -> str:
    global _MODEL_DETAIL_TEMPLATE_CACHE
    if MODEL_DETAIL_TEMPLATE_PATH.exists():
        if settings.is_development or _MODEL_DETAIL_TEMPLATE_CACHE is None:
            _MODEL_DETAIL_TEMPLATE_CACHE = MODEL_DETAIL_TEMPLATE_PATH.read_text(
                encoding="utf-8"
            )
        try:
            import jinja2

            return jinja2.Template(_MODEL_DETAIL_TEMPLATE_CACHE).render(
                model=model, is_active=is_active, settings=settings
            )
        except Exception:
            return _MODEL_DETAIL_TEMPLATE_CACHE

    display_name = model.get("display_name", model.get("name", ""))
    creator = model.get("creator", "")
    name = model.get("name", "")
    status_label = "Active" if is_active else "Non Active"
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        f"<head><title>{display_name}</title></head>\n"
        "<body>\n"
        f"    <h1>{display_name}</h1>\n"
        f"    <p>Creator: {creator}</p>\n"
        f"    <p>Model: {name}</p>\n"
        f"    <p>Status: {status_label}</p>\n"
        "</body>\n"
        "</html>"
    )


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    loaded = get_loaded_models(request.app.state)
    return HTMLResponse(content=get_template_content(loaded), status_code=200)


@router.get("/{creator}/{model_name}", response_class=HTMLResponse)
async def model_detail(creator: str, model_name: str, request: Request) -> HTMLResponse:
    model = get_model_by_slug(creator, model_name)
    if not model:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{creator}/{model_name}' not found",
        )

    loaded = get_loaded_models(request.app.state)
    normalized = normalize_model_name(model.get("id", model.get("name", "")))
    is_active = normalized in loaded or model.get("name") in loaded

    return HTMLResponse(
        content=get_model_detail_content(model, is_active), status_code=200
    )
