from unittest.mock import MagicMock
from app.services.models.laya_adapter import LayaAdapter
from app.services.models.d3_lite_adapter import D3LiteAdapter
from app.services.models.kev_adapter import KevAdapter


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

