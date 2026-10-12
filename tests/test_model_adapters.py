from unittest.mock import MagicMock
import pytest
from app.services.models.laya_adapter import LayaAdapter
from app.services.models.d3_lite_adapter import D3LiteAdapter
from app.services.models.kev_adapter import KevAdapter, KevRunner
from app.services.models.registry import ModelRegistry, normalize_model_name


def test_laya_adapter_predict():
    adapter = LayaAdapter()
    mock_router = MagicMock()
    mock_router.predict.return_value = {"answers": {"q1": {"noul": 0.95}}}
    adapter.router = mock_router

    result = adapter.predict(state="hello", questions={"q1": {"type": "noul"}})
    assert result == {"answers": {"q1": {"noul": 0.95}}}
    mock_router.predict.assert_called_once_with("hello", {"q1": {"type": "noul"}})


def test_d3_lite_adapter_predict():
    adapter = D3LiteAdapter()
    mock_model = MagicMock()
    mock_model.system_one.return_value = {
        "answers": {
            "route": {
                "type": "choice",
                "choice": "billing",
                "confidence": 0.85,
                "probabilities": {"billing": 0.85, "tech": 0.15},
            }
        }
    }
    adapter.model = mock_model

    res = adapter.predict(state="billing inquiry", questions={"route": {"type": "choice"}})
    assert res["answers"]["route"]["choice"] == "billing"
    mock_model.system_one.assert_called_once_with(
        state="billing inquiry", questions={"route": {"type": "choice"}}
    )


def test_d3_lite_adapter_missing_system_one():
    adapter = D3LiteAdapter()
    adapter.model = object()
    with pytest.raises(RuntimeError, match="d3-lite model is missing system_one method"):
        adapter.predict(state="test", questions={})


def test_kev_runner_calibrated_probabilities():
    runner = KevRunner(model_id="kev-mock", is_mock=True)
    questions = {
        "q_noul": {"type": "noul"},
        "q_choice": {"type": "choice", "criteria": {"a": "Alpha", "b": "Beta"}},
        "q_score": {"type": "score", "criteria": ["Low", "High"]},
    }
    res = runner.predict(state="test state", questions=questions)
    answers = res["answers"]
    assert answers["q_noul"]["noul"] == 0.5
    assert answers["q_choice"]["choice"] == "a"
    assert answers["q_choice"]["confidence"] == 0.5
    assert answers["q_choice"]["probabilities"] == {"a": 0.5, "b": 0.5}
    assert answers["q_score"]["score"] == 0.0
    assert answers["q_score"]["confidence"] == 0.5
    assert answers["q_score"]["probabilities"] == {"0": 0.5, "1": 0.5}


def test_kev_runner_system_one_passthrough():
    mock_model = MagicMock()
    mock_model.system_one.return_value = {"answers": {"q": {"noul": 0.99}}}
    runner = KevRunner(model_id="kev-model", model=mock_model, is_mock=False)
    res = runner.predict(state="test", questions={"q": {"type": "noul"}})
    assert res == {"answers": {"q": {"noul": 0.99}}}


def test_kev_adapter_predict():
    adapter = KevAdapter()
    mock_runner = MagicMock()
    mock_runner.predict.return_value = {
        "answers": {
            "urgent": {"type": "noul", "noul": 0.88}
        }
    }
    adapter.runner = mock_runner

    res = adapter.predict(state="urgent issue", questions={"urgent": {"type": "noul"}})
    assert res["answers"]["urgent"]["noul"] == 0.88
    mock_runner.predict.assert_called_once_with("urgent issue", {"urgent": {"type": "noul"}})


def test_adapter_thread_locks():
    laya = LayaAdapter()
    d3 = D3LiteAdapter()
    kev = KevAdapter()
    assert hasattr(laya, "_lock")
    assert hasattr(d3, "_lock")
    assert hasattr(kev, "_lock")


def test_normalize_model_name():
    assert normalize_model_name("laya") == "laya"
    assert normalize_model_name("vllm-sr/d3-lite") == "d3-lite"
    assert normalize_model_name("d3-lite") == "d3-lite"
    assert normalize_model_name("d3_lite") == "d3-lite"
    assert normalize_model_name("jaredpalmer/kev-0.8b") == "kev"
    assert normalize_model_name("kev") == "kev"
    assert normalize_model_name("kev-latest") == "kev"


def test_registry_get_adapter():
    registry = ModelRegistry()
    assert registry.get_adapter("laya").name == "laya"
    assert registry.get_adapter("vllm-sr/d3-lite").name == "d3-lite"
    assert registry.get_adapter("jaredpalmer/kev-0.8b").name == "kev"
    assert registry.get_adapter("unknown-model") is None


def test_registry_preload_all():
    registry = ModelRegistry()
    mock_adapter = MagicMock()
    mock_adapter.name = "laya"
    registry._adapters["laya"] = mock_adapter

    mock_state = MagicMock()
    loaded = registry.preload_all(mock_state, ["laya"])
    assert "laya" in loaded
    mock_adapter.load.assert_called_once()
    assert mock_state.models["laya"] == mock_adapter


