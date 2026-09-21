from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "index.html"


@router.get("/", response_class=HTMLResponse)
async def home() -> HTMLResponse:
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    return HTMLResponse(content=content, status_code=200)
