import logging
import os
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class LayaAdapter:
    name: str = "laya"

    def __init__(self):
        self.router: Any = None

    def load(self) -> None:
        if self.router is not None:
            return
        weights_path = os.path.join(settings.laya_model_path, "model.safetensors")
        if not os.path.exists(weights_path):
            logger.info("Auto-downloading Laya from %s", settings.laya_model_id)
            from huggingface_hub import snapshot_download

            snapshot_download(repo_id=settings.laya_model_id, local_dir=settings.laya_model_path)
        import laya

        device = None if settings.laya_device == "auto" else settings.laya_device
        self.router = laya.load(settings.laya_model_path, device=device)

    def predict(self, state: Any, questions: dict[str, Any]) -> dict[str, Any]:
        if self.router is None:
            self.load()
        return self.router.predict(state, questions)

    def unload(self) -> None:
        if self.router is not None and hasattr(self.router, "unload"):
            self.router.unload()
        self.router = None
