import asyncio
import inspect
import json
import logging
from typing import Any, AsyncGenerator

from app.core import db
from app.services.models.registry import ModelRegistry, default_registry

logger = logging.getLogger(__name__)


class SSEMessage(str):
    """String formatted as an SSE message with dict-like attribute access."""

    def __new__(cls, data: dict):
        raw_str = f"data: {json.dumps(data)}\n\n"
        obj = super().__new__(cls, raw_str)
        obj._data = data
        return obj

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def __getitem__(self, item: str) -> Any:
        return self._data[item]

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()


class ModelSetupManager:
    # ponytail: in-memory asyncio.Queue pub-sub supports single-process SSE; upgrade to Redis pub/sub if scaling across multiple workers.
    def __init__(
        self,
        db_path: str | None = None,
        registry: ModelRegistry | None = None,
    ) -> None:
        self.db_path = db_path
        self._registry = registry
        self._subscribers: list[asyncio.Queue] = []
        self._is_running: bool = False
        self._last_event: dict = {}

    @property
    def registry(self) -> ModelRegistry:
        return self._registry or default_registry

    def broadcast(self, event_dict: dict) -> None:
        self._last_event = event_dict
        msg = SSEMessage(event_dict)
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(msg)
            except Exception:
                pass

    async def event_generator(self) -> AsyncGenerator[SSEMessage, None]:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(queue)
        try:
            while True:
                msg = await queue.get()
                yield msg
        finally:
            if queue in self._subscribers:
                self._subscribers.remove(queue)

    def get_status(self) -> dict:
        settings_dict = db.get_system_settings(self.db_path)
        setup_completed = settings_dict.get("models_setup_completed") == "1"
        active_models_raw = settings_dict.get("active_models", "")
        active_models = [m.strip() for m in active_models_raw.split(",") if m.strip()]
        return {
            "is_running": self._is_running,
            "last_event": self._last_event,
            "setup_completed": setup_completed,
            "active_models": active_models,
        }

    async def start_setup(self, app_state: Any, models: list[str]) -> None:
        clean_models = [m.strip() for m in models if m.strip()]
        if not clean_models:
            self.broadcast(
                {
                    "phase": "error",
                    "progress": 0,
                    "message": "No models specified for setup",
                }
            )
            raise ValueError("No models specified for setup")

        if self._is_running:
            raise RuntimeError("Model setup is already in progress")

        self._is_running = True
        try:
            # Yield control so any waiting subscriber tasks are registered
            await asyncio.sleep(0)

            total = len(clean_models)
            self.broadcast(
                {
                    "phase": "downloading",
                    "progress": 10,
                    "message": f"Downloading assets for {total} model(s)...",
                    "models": clean_models,
                }
            )
            await asyncio.sleep(0.01)

            if not hasattr(app_state, "models") or app_state.models is None:
                app_state.models = {}

            for idx, m in enumerate(clean_models):
                self.broadcast(
                    {
                        "phase": "downloading",
                        "progress": int(10 + (idx / total) * 30),
                        "message": f"Downloading model '{m}'...",
                        "model": m,
                    }
                )
                await asyncio.sleep(0.01)

                adapter = self.registry.get_adapter(m)
                if adapter is None:
                    raise ValueError(f"Unknown or unavailable model adapter: '{m}'")

                self.broadcast(
                    {
                        "phase": "loading",
                        "progress": int(40 + (idx / total) * 50),
                        "message": f"Loading model '{m}' into memory...",
                        "model": m,
                    }
                )
                await asyncio.sleep(0.01)

                if inspect.iscoroutinefunction(getattr(adapter, "load", None)):
                    await adapter.load()
                else:
                    await asyncio.to_thread(adapter.load)

                app_state.models[adapter.name] = adapter
                if adapter.name == "laya" and hasattr(adapter, "router"):
                    app_state.router = adapter.router

            db.update_system_settings(
                {
                    "models_setup_completed": "1",
                    "active_models": ",".join(clean_models),
                },
                db_path=self.db_path,
            )

            self.broadcast(
                {
                    "phase": "completed",
                    "progress": 100,
                    "message": "All models loaded successfully!",
                    "models": clean_models,
                }
            )
            await asyncio.sleep(0.01)

        except Exception as e:
            logger.error("Model setup failed: %s", e)
            self.broadcast(
                {
                    "phase": "error",
                    "progress": 0,
                    "message": f"Setup failed: {str(e)}",
                    "error": str(e),
                }
            )
            raise
        finally:
            self._is_running = False


default_setup_manager = ModelSetupManager()
