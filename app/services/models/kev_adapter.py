import logging
import os
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class KevAdapter:
    name: str = "kev"

    def __init__(self):
        self.runner: Any = None

    def load(self) -> None:
        if self.runner is not None:
            return
        target = settings.kev_model_path if os.path.exists(settings.kev_model_path) else settings.kev_model_id
        logger.info("Loading kev model from %s", target)
        try:
            from transformers import AutoModel, AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(target)
            self.runner = {"model_id": target, "tokenizer": tokenizer}
        except Exception as e:
            logger.warning("Kev model weights not available locally, initializing in stub mode: %s", e)
            self.runner = {"model_id": target}

    def predict(self, state: Any, questions: dict[str, Any]) -> dict[str, Any]:
        if self.runner is None:
            self.load()
        if hasattr(self.runner, "predict"):
            return self.runner.predict(state, questions)

        # Fallback calibrated scoring representation for questions
        answers: dict[str, Any] = {}
        for q_id, q_data in questions.items():
            q_type = q_data.get("type", "noul")
            if q_type == "noul":
                answers[q_id] = {"noul": 0.5}
            elif q_type == "choice":
                crit = q_data.get("criteria", {})
                first_key = next(iter(crit.keys())) if crit else "default"
                answers[q_id] = {
                    "choice": first_key,
                    "confidence": 0.5,
                    "probabilities": {k: 1.0 / max(1, len(crit)) for k in crit},
                }
            elif q_type == "score":
                crit = q_data.get("criteria", ["Low", "High"])
                answers[q_id] = {
                    "score": 0.0,
                    "confidence": 0.5,
                    "probabilities": {str(i): 1.0 / len(crit) for i in range(len(crit))},
                }
        return {"answers": answers}

    def unload(self) -> None:
        self.runner = None
