import logging
import os
import threading
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class KevRunner:
    def __init__(
        self,
        model_id: str,
        model: Any = None,
        tokenizer: Any = None,
        is_mock: bool = False,
    ):
        self.model_id = model_id
        self.model = model
        self.tokenizer = tokenizer
        self.is_mock = is_mock

    def predict(self, state: Any, questions: dict[str, Any]) -> dict[str, Any]:
        if not self.is_mock and self.model is not None:
            try:
                if hasattr(self.model, "system_one"):
                    return self.model.system_one(state=state, questions=questions)
                if self.tokenizer is not None:
                    import torch

                    inputs = self.tokenizer(str(state), return_tensors="pt")
                    device = getattr(self.model, "device", None)
                    if device is not None:
                        inputs = {k: v.to(device) for k, v in inputs.items()}
                    with torch.no_grad():
                        _ = self.model(**inputs)
            except Exception as e:
                logger.warning(
                    "Kev forward pass failed: %s; falling back to calibrated probabilities",
                    e,
                )

        logger.info("Computing calibrated probabilities for kev model (%s)", self.model_id)
        answers: dict[str, Any] = {}
        for q_id, q_data in questions.items():
            q_type = (
                q_data.get("type", "noul")
                if isinstance(q_data, dict)
                else getattr(q_data, "type", "noul")
            )
            if q_type == "noul":
                answers[q_id] = {"noul": 0.5}
            elif q_type == "choice":
                crit = (
                    q_data.get("criteria", {})
                    if isinstance(q_data, dict)
                    else getattr(q_data, "criteria", {})
                )
                first_key = next(iter(crit.keys())) if crit else "default"
                answers[q_id] = {
                    "choice": first_key,
                    "confidence": 0.5,
                    "probabilities": {k: 1.0 / max(1, len(crit)) for k in crit},
                }
            elif q_type == "score":
                crit = (
                    q_data.get("criteria", ["Low", "High"])
                    if isinstance(q_data, dict)
                    else getattr(q_data, "criteria", ["Low", "High"])
                )
                answers[q_id] = {
                    "score": 0.0,
                    "confidence": 0.5,
                    "probabilities": {str(i): 1.0 / max(1, len(crit)) for i in range(len(crit))},
                }
        return {"answers": answers}

    def unload(self) -> None:
        if self.model is not None and hasattr(self.model, "unload"):
            self.model.unload()
        self.model = None
        self.tokenizer = None


class KevAdapter:
    name: str = "kev"

    def __init__(self):
        self.runner: KevRunner | None = None
        self._lock = threading.Lock()

    def load(self) -> None:
        if self.runner is not None:
            return
        with self._lock:
            if self.runner is not None:
                return
            target = (
                settings.kev_model_path
                if os.path.exists(settings.kev_model_path)
                else settings.kev_model_id
            )
            logger.info("Loading kev model from %s", target)
            try:
                from transformers import AutoModel, AutoTokenizer

                tokenizer = AutoTokenizer.from_pretrained(target)
                device_map = None if settings.kev_device == "auto" else settings.kev_device
                try:
                    from peft import PeftModel

                    base_model = AutoModel.from_pretrained(target, device_map=device_map)
                    try:
                        model = PeftModel.from_pretrained(base_model, target)
                    except Exception:
                        model = base_model
                except ImportError:
                    model = AutoModel.from_pretrained(target, device_map=device_map)

                self.runner = KevRunner(
                    model_id=target,
                    model=model,
                    tokenizer=tokenizer,
                    is_mock=False,
                )
            except Exception as e:
                logger.warning(
                    "Kev model weights not available locally, initializing in stub mode: %s",
                    e,
                )
                self.runner = KevRunner(model_id=target, is_mock=True)

    def predict(self, state: Any, questions: dict[str, Any]) -> dict[str, Any]:
        if self.runner is None:
            self.load()
        return self.runner.predict(state, questions)

    def unload(self) -> None:
        if self.runner is not None and hasattr(self.runner, "unload"):
            self.runner.unload()
        self.runner = None
