import asyncio

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.models.registry import default_registry, normalize_model_name
from app.services.setup_manager import default_setup_manager

router = APIRouter()


class ModelActivateRequest(BaseModel):
    model: str = ""


@router.post("/activate")
async def activate_model(body: ModelActivateRequest, request: Request) -> dict[str, str]:
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
