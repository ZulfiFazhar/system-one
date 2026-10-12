import logging
from typing import Any
from app.services.models.base import BaseModelAdapter
from app.services.models.d3_lite_adapter import D3LiteAdapter
from app.services.models.kev_adapter import KevAdapter
from app.services.models.laya_adapter import LayaAdapter

logger = logging.getLogger(__name__)

ALIASES = {
    "laya": "laya",
    "convaiinnovations/laya-multilingual": "laya",
    "d3-lite": "d3-lite",
    "d3_lite": "d3-lite",
    "vllm-sr/d3-lite": "d3-lite",
    "kev": "kev",
    "kev-0.8b": "kev",
    "kev-latest": "kev",
    "jaredpalmer/kev-0.8b": "kev",
}


def normalize_model_name(name: str) -> str:
    cleaned = name.strip().lower()
    return ALIASES.get(cleaned, cleaned)


class ModelRegistry:
    def __init__(self):
        self._adapters: dict[str, BaseModelAdapter] = {}
        self._classes = {
            "laya": LayaAdapter,
            "d3-lite": D3LiteAdapter,
            "kev": KevAdapter,
        }

    def get_adapter(self, name: str) -> BaseModelAdapter | None:
        normalized = normalize_model_name(name)
        if normalized not in self._adapters:
            adapter_cls = self._classes.get(normalized)
            if adapter_cls is None:
                return None
            self._adapters[normalized] = adapter_cls()
        return self._adapters[normalized]

    def preload_all(self, app_state: Any, models_to_load: list[str]) -> dict[str, BaseModelAdapter]:
        loaded: dict[str, BaseModelAdapter] = {}
        for m in models_to_load:
            adapter = self.get_adapter(m)
            if adapter:
                try:
                    adapter.load()
                    loaded[adapter.name] = adapter
                    logger.info("Preloaded model '%s'", adapter.name)
                except Exception as e:
                    logger.error("Failed to preload model '%s': %s", adapter.name, e)
        app_state.models = loaded
        return loaded


default_registry = ModelRegistry()
