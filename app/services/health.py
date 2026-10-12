from typing import Any


def check_health(app_state: Any) -> dict[str, Any]:
    router_ready = hasattr(app_state, "router") and app_state.router is not None
    loaded_models = list(getattr(app_state, "models", {}).keys())
    if router_ready and "laya" not in loaded_models:
        loaded_models.append("laya")
    return {
        "status": "ready",
        "model": "laya",
        "preloaded": bool(router_ready or loaded_models),
        "loaded_models": loaded_models,
    }
