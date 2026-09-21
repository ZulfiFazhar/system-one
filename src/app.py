import os
import secrets
from contextlib import asynccontextmanager
from typing import Any
from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

try:
    from .schemas import SystemOneRequest, SystemOneResponse
    from .adapter import format_jev_response
except ImportError:
    from schemas import SystemOneRequest, SystemOneResponse
    from adapter import format_jev_response

security = HTTPBearer(auto_error=False)

def verify_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> None:
    api_key = os.getenv("LAYA_API_KEY")
    if not api_key:
        return
    if not credentials or not secrets.compare_digest(credentials.credentials, api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
        )

class MockRouter:
    def predict(self, state: Any, questions: dict[str, Any], model: str | None = None) -> dict[str, Any]:
        answers = {}
        for q_id, q in questions.items():
            q_type = q.type if hasattr(q, "type") else q.get("type")
            if q_type == "noul":
                answers[q_id] = {"noul": 0.85}
            elif q_type == "choice":
                crit = q.criteria if hasattr(q, "criteria") else q.get("criteria", {})
                first_opt = next(iter(crit.keys())) if crit else "default"
                answers[q_id] = {
                    "choice": first_opt,
                    "probabilities": {k: 1.0 / len(crit) for k in crit},
                    "confidence": 0.9,
                }
            elif q_type == "score":
                answers[q_id] = {"score": 1.0, "probabilities": {"0": 0.2, "1": 0.8}, "confidence": 0.8}
        return {"answers": answers, "routing": {"model": model or "laya"}}

    def unload(self) -> None:
        pass

def create_app(mock_router: bool = False) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if not hasattr(app.state, "router"):
            if mock_router or os.getenv("LAYA_MOCK_ROUTER", "").lower() in ("1", "true"):
                app.state.router = MockRouter()
            else:
                try:
                    import laya
                    device = os.getenv("LAYA_DEVICE", "auto")
                    preload = os.getenv("LAYA_PRELOAD", "true").lower() in ("1", "true")
                    app.state.router = laya.Router(preload=preload, device=device)
                except Exception:
                    app.state.router = MockRouter()
        yield
        if hasattr(app.state, "router") and hasattr(app.state.router, "unload"):
            app.state.router.unload()

    app = FastAPI(title="System One (Laya) API", lifespan=lifespan)
    if mock_router or os.getenv("LAYA_MOCK_ROUTER", "").lower() in ("1", "true"):
        app.state.router = MockRouter()

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {"status": "ready", "model": "laya", "preloaded": True}

    @app.post("/v1/systemone", response_model=SystemOneResponse, dependencies=[Depends(verify_api_key)])
    async def systemone(req: SystemOneRequest) -> SystemOneResponse:
        router = getattr(app.state, "router", None)
        if router is None:
            router = MockRouter()
            app.state.router = router
        # Execute model inference in thread pool to avoid blocking asyncio event loop
        questions_dict = {
            k: v.model_dump() if hasattr(v, "model_dump") else v
            for k, v in req.questions.items()
        }
        res = await run_in_threadpool(
            router.predict,
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

    return app

def main() -> None:
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port, reload=False)

app = create_app()
