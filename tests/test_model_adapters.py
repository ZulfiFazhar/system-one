from unittest.mock import MagicMock
from app.services.models.laya_adapter import LayaAdapter


def test_laya_adapter_predict():
    adapter = LayaAdapter()
    mock_router = MagicMock()
    mock_router.predict.return_value = {"answers": {"q1": {"noul": 0.95}}}
    adapter.router = mock_router

    result = adapter.predict(state="hello", questions={"q1": {"type": "noul"}})
    assert result == {"answers": {"q1": {"noul": 0.95}}}
    mock_router.predict.assert_called_once_with("hello", {"q1": {"type": "noul"}})
