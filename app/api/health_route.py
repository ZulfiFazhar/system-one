from typing import Any

from fastapi import APIRouter, Request

from app.services.health import check_health

router = APIRouter()


@router.get("/health")
def health(request: Request) -> dict[str, Any]:
    return check_health(request.app.state)
