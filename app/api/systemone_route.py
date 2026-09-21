from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool

from app.core.security import verify_api_key
from app.dto.systemone_dto import SystemOneRequest, SystemOneResponse
from app.services.laya_service import format_jev_response, get_or_load_router

router = APIRouter()


@router.post(
    "/systemone",
    response_model=SystemOneResponse,
    dependencies=[Depends(verify_api_key)],
)
async def systemone(req: SystemOneRequest, request: Request) -> SystemOneResponse:
    router_instance = await get_or_load_router(request.app.state)
    if router_instance is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Laya model is not initialized",
        )

    questions_dict = {
        k: v.model_dump() if hasattr(v, "model_dump") else v
        for k, v in req.questions.items()
    }
    res = await run_in_threadpool(
        router_instance.predict,
        req.state,
        questions_dict,
    )
    laya_answers = res.get("answers", {})
    return format_jev_response(
        model_name=req.model,
        laya_answers=laya_answers,
        questions=req.questions,
        state=req.state,
    )
