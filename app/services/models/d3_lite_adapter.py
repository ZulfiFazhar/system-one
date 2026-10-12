import logging
import os
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class D3LiteAdapter:
    name: str = "d3-lite"

    def __init__(self):
        self.model: Any = None

    def load(self) -> None:
        if self.model is not None:
            return
        from transformers import AutoModel

        target = (
            settings.d3_lite_model_path
            if os.path.exists(settings.d3_lite_model_path)
            else settings.d3_lite_model_id
        )
        logger.info("Loading d3-lite model from %s", target)
        device_map = None if settings.d3_lite_device == "auto" else settings.d3_lite_device
        self.model = AutoModel.from_pretrained(target, trust_remote_code=True, device_map=device_map)

    def predict(self, state: Any, questions: dict[str, Any]) -> dict[str, Any]:
        if self.model is None:
            self.load()
        if hasattr(self.model, "system_one"):
            return self.model.system_one(state=state, questions=questions)
        return {"answers": {}}

    def unload(self) -> None:
        self.model = None
