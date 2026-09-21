import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api import router as api_router
from app.core.config import settings

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
    weights_path = os.path.join(settings.laya_model_path, "model.safetensors")
    if not os.path.exists(weights_path):
        logger.info(
            "Local model weights not found at '%s'. Auto-downloading '%s' from Hugging Face...",
            settings.laya_model_path,
            settings.laya_model_id,
        )
        from huggingface_hub import snapshot_download

        snapshot_download(
            repo_id=settings.laya_model_id,
            local_dir=settings.laya_model_path,
        )
        logger.info("Auto-download complete.")

    # Enforce offline mode to prevent any subsequent requests to Hugging Face
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    if not hasattr(app.state, "router") or app.state.router is None:
        import laya

        device = None if settings.laya_device == "auto" else settings.laya_device
        logger.info("Loading Laya model from local path: %s", settings.laya_model_path)
        app.state.router = laya.load(
            settings.laya_model_path,
            device=device,
        )
        logger.info("Laya model loaded successfully from local directory")
    yield
    if hasattr(app.state, "router") and hasattr(app.state.router, "unload"):
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

    return app
