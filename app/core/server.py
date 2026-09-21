import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import router as api_router
from app.core.config import settings
from app.services.laya_service import load_laya_model

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

    # Mount api routes
    app.include_router(api_router)

    # Mount static public directory
    public_dir = Path(__file__).resolve().parent.parent.parent / "public"
    if public_dir.exists():
        app.mount("/public", StaticFiles(directory=str(public_dir)), name="public")

    return app
