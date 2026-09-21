try:
    from .app import app, create_app, main
except ImportError:
    from app import app, create_app, main

__all__ = ["app", "create_app", "main"]

