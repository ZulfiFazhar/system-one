# Task 5 Brief: API Routes, Server & Main Entrypoint

**Files:**
- Create: `D:\Zulfi\Programming\FastAPI\system-one\app\api\__init__.py`
- Create: `D:\Zulfi\Programming\FastAPI\system-one\app\api\health_route.py`
- Create: `D:\Zulfi\Programming\FastAPI\system-one\app\api\systemone_route.py`
- Create: `D:\Zulfi\Programming\FastAPI\system-one\app\core\server.py`
- Create: `D:\Zulfi\Programming\FastAPI\system-one\app\main.py`

### Requirements
1. Create `app/api/health_route.py`:
```python
from typing import Any
from fastapi import APIRouter, Request
from app.services.health import check_health

router = APIRouter()


@router.get("/healthz")
@router.get("/health")
def health(request: Request) -> dict[str, Any]:
    return check_health(request.app.state)
```

2. Create `app/api/systemone_route.py`:
```python
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
```

3. Create `app/api/__init__.py`:
```python
from fastapi import APIRouter
from app.api.health_route import router as health_router
from app.api.systemone_route import router as systemone_router

router = APIRouter()

router.include_router(health_router, tags=["health"])
router.include_router(systemone_router, prefix="/v1", tags=["systemone"])
```

4. Create `app/core/server.py`:
```python
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api import router as api_router
from app.api.health_route import router as root_health_router
from app.core.config import settings
from app.services.laya_service import MockRouter

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(level=settings.log_level.upper(), format=settings.log_format)


def setup_middlewares(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if settings.is_production:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not hasattr(app.state, "router"):
        if settings.laya_mock_router:
            app.state.router = MockRouter()
        else:
            try:
                import laya

                app.state.router = laya.Router(
                    preload=settings.laya_preload,
                    device=settings.laya_device,
                )
            except Exception:
                app.state.router = MockRouter()
    yield
    if hasattr(app.state, "router") and hasattr(app.state.router, "unload"):
        app.state.router.unload()


def create_application(mock_router: bool = False) -> FastAPI:
    setup_logging()

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        lifespan=lifespan,
    )

    setup_middlewares(app)

    if mock_router or settings.laya_mock_router:
        app.state.router = MockRouter()

    # Mount health directly at root (/healthz) for backward compatibility
    app.include_router(root_health_router)
    # Mount api routes
    app.include_router(api_router)

    return app
```

5. Create `app/main.py`:
```python
from app.core.server import create_application

app = create_application()

__all__ = ["app"]
```

6. Verification:
Run: `uv run python -c "from app.main import app; print('app loaded ok')"`
Expected: Output `app loaded ok`.

7. Commit:
`git add app/api app/core/server.py app/main.py && git commit -m "feat: implement app.api routes, app.core.server, and app.main"`
