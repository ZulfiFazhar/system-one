from typing import Any


def check_health(app_state: Any) -> dict[str, Any]:
    router_ready = hasattr(app_state, "router") and app_state.router is not None
    return {
        "status": "ready" if router_ready else "initializing",
        "model": "laya",
        "preloaded": True,
    }
