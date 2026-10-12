from app.core import db
from app.core.config import Settings


def test_config_no_laya_preload_flags():
    s = Settings()
    assert not hasattr(s, "laya_preload")
    assert not hasattr(s, "laya_lazy_load")


def test_system_settings_models_defaults(tmp_path):
    test_db = str(tmp_path / "test_models.db")
    db.init_db(test_db)
    settings_dict = db.get_system_settings(test_db)
    assert "models_setup_completed" in settings_dict
    assert settings_dict["models_setup_completed"] == "0"
    assert "active_models" in settings_dict


def test_lifespan_preloads_when_setup_completed(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.core.config import settings
    from app.core.server import create_application

    test_db = str(tmp_path / "test_lifespan_preload.db")
    db.init_db(test_db)
    db.update_system_settings(
        {"models_setup_completed": "1", "active_models": "laya"},
        db_path=test_db,
    )
    monkeypatch.setattr(settings, "database_path", test_db)

    app = create_application()
    with TestClient(app):
        assert hasattr(app.state, "router")
        assert app.state.router is not None
        assert "laya" in getattr(app.state, "models", {})


def test_lifespan_skips_preloading_when_setup_not_completed(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.core.config import settings
    from app.core.server import create_application

    test_db = str(tmp_path / "test_lifespan_skip.db")
    db.init_db(test_db)
    monkeypatch.setattr(settings, "database_path", test_db)

    app = create_application()
    with TestClient(app):
        assert getattr(app.state, "router", None) is None
