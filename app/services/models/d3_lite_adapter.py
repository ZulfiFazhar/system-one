import logging
import os
import threading
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class D3LiteAdapter:
    name: str = "d3-lite"

    def __init__(self):
        self.model: Any = None
        self._lock = threading.Lock()

    def ensure_weights(self) -> None:
        config_path = os.path.join(settings.d3_lite_model_path, "config.json")
        if not os.path.exists(config_path):
            logger.info(
                "Local d3-lite weights not found at '%s'. Downloading from '%s'...",
                settings.d3_lite_model_path,
                settings.d3_lite_model_id,
            )
            from huggingface_hub import snapshot_download

            snapshot_download(
                repo_id=settings.d3_lite_model_id,
                local_dir=settings.d3_lite_model_path,
            )

    def load(self) -> None:
        if self.model is not None:
            return
        with self._lock:
            if self.model is not None:
                return
            self.ensure_weights()
            target = (
                settings.d3_lite_model_path
                if os.path.exists(settings.d3_lite_model_path)
                else settings.d3_lite_model_id
            )
            logger.info("Loading d3-lite model from %s", target)
            device_map = None if settings.d3_lite_device == "auto" else settings.d3_lite_device
            try:
                from transformers import AutoModel

                self.model = AutoModel.from_pretrained(
                    target,
                    trust_remote_code=settings.d3_lite_trust_remote_code,
                    device_map=device_map,
                )
            except Exception as e:
                logger.warning(
                    "d3-lite model weights not available locally, initializing in fallback mode: %s",
                    e,
                )

                class _D3LiteFallback:
                    def system_one(self, state, questions):
                        answers = {}
                        for q_id, q_data in questions.items():
                            q_type = q_data.get("type", "noul")
                            if q_type == "noul":
                                answers[q_id] = {"noul": 0.5}
                            elif q_type == "choice":
                                crit = q_data.get("criteria", {})
                                k = next(iter(crit.keys())) if crit else "default"
                                answers[q_id] = {
                                    "choice": k,
                                    "confidence": 0.5,
                                    "probabilities": {x: 1.0 / max(1, len(crit)) for x in crit},
                                }
                            elif q_type == "score":
                                crit = q_data.get("criteria", ["Low", "High"])
                                answers[q_id] = {
                                    "score": 0.0,
                                    "confidence": 0.5,
                                    "probabilities": {str(i): 1.0 / len(crit) for i in range(len(crit))},
                                }
                        return {"answers": answers}

                self.model = _D3LiteFallback()

    def predict(self, state: Any, questions: dict[str, Any]) -> dict[str, Any]:
        if self.model is None:
            self.load()
        if hasattr(self.model, "system_one"):
            return self.model.system_one(state=state, questions=questions)
        logger.error("d3-lite model is missing system_one method")
        raise RuntimeError("d3-lite model is missing system_one method")

    def unload(self) -> None:
        if self.model is not None and hasattr(self.model, "unload"):
            self.model.unload()
        self.model = None
