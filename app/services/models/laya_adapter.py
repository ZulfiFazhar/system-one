import logging
import threading
from typing import Any

from app.core.config import settings
from app.services.laya_service import ensure_model_weights

logger = logging.getLogger(__name__)


class LayaAdapter:
    name: str = "laya"

    def __init__(self):
        self.router: Any = None
        self._lock = threading.Lock()

    def load(self) -> None:
        if self.router is not None:
            return
        with self._lock:
            if self.router is not None:
                return
            ensure_model_weights()
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
