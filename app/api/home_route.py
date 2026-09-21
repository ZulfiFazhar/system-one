from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.core.config import settings

router = APIRouter()

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "index.html"
_TEMPLATE_CACHE: str | None = None


def get_template_content() -> str:
    global _TEMPLATE_CACHE
    if settings.is_development or _TEMPLATE_CACHE is None:
        _TEMPLATE_CACHE = TEMPLATE_PATH.read_text(encoding="utf-8")
    return _TEMPLATE_CACHE


@router.get("/", response_class=HTMLResponse)
async def home() -> HTMLResponse:
    return HTMLResponse(content=get_template_content(), status_code=200)
