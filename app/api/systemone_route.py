from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool

from app.core.security import verify_api_key
from app.dto.systemone_dto import SystemOneRequest, SystemOneResponse
from app.services.laya_service import MockRouter, format_jev_response

router = APIRouter()


@router.post(
    "/systemone",
    response_model=SystemOneResponse,
    dependencies=[Depends(verify_api_key)],
)
async def systemone(req: SystemOneRequest, request: Request) -> SystemOneResponse:
    router_instance = getattr(request.app.state, "router", None)
    if router_instance is None:
        router_instance = MockRouter()
        request.app.state.router = router_instance

    questions_dict = {
        k: v.model_dump() if hasattr(v, "model_dump") else v
        for k, v in req.questions.items()
    }
    res = await run_in_threadpool(
        router_instance.predict,
        req.state,
        questions_dict,
        req.model,
    )
    laya_answers = res.get("answers", {})
    return format_jev_response(
        model_name=req.model,
        laya_answers=laya_answers,
        questions=req.questions,
        state=req.state,
    )
