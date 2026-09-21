import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api import router as api_router
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
                logger.warning(
                    "Failed to initialize Laya router, falling back to MockRouter",
                    exc_info=True,
                )
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

    # Mount api routes
    app.include_router(api_router)

    return app
