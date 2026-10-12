from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool

from app.core.security import verify_api_key
from app.dto.systemone_dto import SystemOneRequest, SystemOneResponse
from app.services.laya_service import format_jev_response
from app.services.models.registry import default_registry, normalize_model_name

router = APIRouter()


@router.post(
    "/systemone",
    response_model=SystemOneResponse,
    dependencies=[Depends(verify_api_key)],
)
async def systemone(req: SystemOneRequest, request: Request) -> SystemOneResponse:
    model_name = normalize_model_name(req.model)
    adapter = None
    if hasattr(request.app.state, "models") and request.app.state.models:
        adapter = request.app.state.models.get(model_name)

    if adapter is None:
        adapter = default_registry.get_adapter(model_name)
        if adapter is not None:
            if not hasattr(request.app.state, "models") or request.app.state.models is None:
                request.app.state.models = {}
            request.app.state.models[model_name] = adapter

    if adapter is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{req.model}' is not supported. Supported models: laya, d3-lite, kev",
        )

    # Sync router for backwards compatibility and tests
    if model_name == "laya":
        if hasattr(request.app.state, "router") and request.app.state.router is not None:
            adapter.router = request.app.state.router
        else:
            await run_in_threadpool(adapter.load)
            request.app.state.router = adapter.router

    questions_dict = {
        k: v.model_dump() if hasattr(v, "model_dump") else v
        for k, v in req.questions.items()
    }
    res = await run_in_threadpool(
        adapter.predict,
        req.state,
        questions_dict,
    )
    raw_answers = res.get("answers", {}) if isinstance(res, dict) else {}
    response = format_jev_response(
        model_name=req.model,
        laya_answers=raw_answers,
        questions=req.questions,
        state=req.state,
    )
    request.state.usage = response.usage
    return response
