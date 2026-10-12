import asyncio

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.security import check_rate_limit
from app.services.models.registry import default_registry, normalize_model_name
from app.services.setup_manager import default_setup_manager

router = APIRouter()


class ModelActivateRequest(BaseModel):
    model: str = ""


@router.post("/activate")
async def activate_model(body: ModelActivateRequest, request: Request) -> dict[str, str]:
    client_ip = request.client.host if request.client else "127.0.0.1"
    check_rate_limit(client_ip)

    if not body.model or not body.model.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model name is required",
        )

    model_name = normalize_model_name(body.model)
    if not default_registry.get_adapter(model_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown model: {body.model}",
        )

    loaded_models = getattr(request.app.state, "models", {})
    if model_name in loaded_models:
        return {"status": "already_active", "model": model_name}

    if default_setup_manager._is_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another model setup or activation is currently in progress",
        )

    # ponytail: fire-and-forget background task; upgrade to durable queue if multi-instance.
    asyncio.create_task(
        default_setup_manager.start_setup(request.app.state, [model_name])
    )
    return {"status": "started", "model": model_name}


@router.get("/stream")
def stream_models() -> StreamingResponse:
    return StreamingResponse(
        default_setup_manager.event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
