from app.core.config import Settings


def test_model_settings_defaults():
    s = Settings()
    assert s.default_model == "laya"
    assert "laya" in s.preload_models
    assert "d3-lite" in s.preload_models
    assert "kev" in s.preload_models
    assert s.d3_lite_model_id == "vllm-sr/d3-lite"
    assert s.d3_lite_trust_remote_code is True
    assert s.kev_model_id == "jaredpalmer/kev-0.8b"
