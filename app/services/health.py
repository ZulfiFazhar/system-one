from typing import Any

from app.core.config import settings


def check_health(app_state: Any) -> dict[str, Any]:
    router_ready = hasattr(app_state, "router") and app_state.router is not None
    is_ready = router_ready or settings.laya_lazy_load
    return {
        "status": "ready" if is_ready else "initializing",
        "model": "laya",
        "preloaded": bool(router_ready),
    }
