import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest

from app.services.setup_manager import ModelSetupManager, default_setup_manager


@pytest.mark.anyio
async def test_setup_manager_pipeline(monkeypatch, tmp_path):
    test_db = str(tmp_path / "setup_test.db")
    from app.core import db

    db.init_db(test_db)

    manager = ModelSetupManager(db_path=test_db)
    app_state = SimpleNamespace(models={})

    mock_adapter = MagicMock()
    mock_adapter.name = "laya"
    mock_adapter.load = MagicMock()

    from app.services.models.registry import ModelRegistry

    monkeypatch.setattr(ModelRegistry, "get_adapter", lambda self, name: mock_adapter)

    events = []

    async def listen():
        async for ev in manager.event_generator():
            events.append(ev)
            if ev.get("phase") in ("completed", "error"):
                break

    listener_task = asyncio.create_task(listen())
    await manager.start_setup(app_state=app_state, models=["laya"])
    await listener_task

    assert any(e.get("phase") == "downloading" for e in events)
    assert any(e.get("phase") == "loading" for e in events)
    assert any(e.get("phase") == "completed" for e in events)

    settings_dict = db.get_system_settings(test_db)
    assert settings_dict["models_setup_completed"] == "1"
    assert "laya" in settings_dict["active_models"]


@pytest.mark.anyio
async def test_setup_manager_empty_models(tmp_path):
    test_db = str(tmp_path / "setup_empty.db")
    from app.core import db

    db.init_db(test_db)

    manager = ModelSetupManager(db_path=test_db)
    app_state = SimpleNamespace(models={})

    with pytest.raises(ValueError, match="No models specified"):
        await manager.start_setup(app_state=app_state, models=[])


@pytest.mark.anyio
async def test_setup_manager_get_status(tmp_path):
    test_db = str(tmp_path / "setup_status.db")
    from app.core import db

    db.init_db(test_db)

    manager = ModelSetupManager(db_path=test_db)
    status = manager.get_status()
    assert status["is_running"] is False
    assert status["setup_completed"] is False
    assert status["active_models"] == []
    assert isinstance(status["last_event"], dict)


def test_default_setup_manager_singleton():
    assert isinstance(default_setup_manager, ModelSetupManager)


def test_sse_message_structure():
    from app.services.setup_manager import SSEMessage
    msg = SSEMessage({"phase": "loading", "progress": 50})
    assert isinstance(msg, str)
    assert msg.startswith("data: {")
    assert msg.endswith("\n\n")
    assert msg.get("phase") == "loading"
    assert msg.get("missing", "default") == "default"
    assert msg["progress"] == 50
    assert "phase" in msg.keys()
    assert 50 in msg.values()


@pytest.mark.anyio
async def test_setup_manager_error_handling(monkeypatch, tmp_path):
    test_db = str(tmp_path / "setup_err.db")
    from app.core import db

    db.init_db(test_db)

    manager = ModelSetupManager(db_path=test_db)
    app_state = SimpleNamespace(models={})

    mock_adapter = MagicMock()
    mock_adapter.name = "failing_model"
    mock_adapter.load.side_effect = RuntimeError("Failed to load weights")

    from app.services.models.registry import ModelRegistry

    monkeypatch.setattr(ModelRegistry, "get_adapter", lambda self, name: mock_adapter)

    events = []

    async def listen():
        async for ev in manager.event_generator():
            events.append(ev)
            if ev.get("phase") in ("completed", "error"):
                break

    listener_task = asyncio.create_task(listen())
    with pytest.raises(RuntimeError, match="Failed to load weights"):
        await manager.start_setup(app_state=app_state, models=["failing_model"])
    await listener_task

    assert any(e.get("phase") == "error" for e in events)
    assert manager.get_status()["is_running"] is False

