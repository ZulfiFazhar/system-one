import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import router as api_router
from app.core.config import settings
from app.core.db import init_db, prune_old_logs
from app.core.middleware import DashboardLoggingMiddleware
from app.core.security import refresh_security_caches
from app.services.laya_service import load_laya_model
from app.web import web_router

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
    app.add_middleware(DashboardLoggingMiddleware)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.start_time = time.time()
    init_db()
    refresh_security_caches()
    prune_old_logs(30)

    should_preload = settings.laya_preload and not settings.laya_lazy_load

    if should_preload:
        load_laya_model(app.state)
    else:
        logger.info(
            "Lazy loading active (LAYA_LAZY_LOAD=true). Model will load upon first inference request."
        )

    yield

    if hasattr(app.state, "router") and hasattr(app.state.router, "unload") and app.state.router:
        app.state.router.unload()


def create_application() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        lifespan=lifespan,
    )

    setup_middlewares(app)

    # Mount web UI routes
    app.include_router(web_router)
    # Mount api routes
    app.include_router(api_router)

    # Mount static public directory
    public_dir = Path(__file__).resolve().parent.parent.parent / "public"
    if public_dir.exists():
        app.mount("/public", StaticFiles(directory=str(public_dir)), name="public")

    return app
