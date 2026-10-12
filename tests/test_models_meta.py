from app.core.models_meta import get_all_models, get_model_by_slug


def test_get_all_models():
    models = get_all_models()
    assert len(models) == 3
    ids = [m["id"] for m in models]
    assert "convaiinnovations/laya-multilingual" in ids
    assert "vllm-sr/d3-lite" in ids
    assert "jaredpalmer/kev-0.8b" in ids


def test_get_model_by_slug():
    d3 = get_model_by_slug("vllm-sr", "d3-lite")
    assert d3 is not None
    assert d3["name"] == "d3-lite"
    assert d3["creator"] == "vllm-sr"
    assert "multimodal" in d3["modality"].lower()

    kev = get_model_by_slug("jaredpalmer", "kev-0.8b")
    assert kev is not None
    assert kev["name"] == "kev-0.8b"

    laya = get_model_by_slug("convaiinnovations", "laya-multilingual")
    assert laya is not None
    assert laya["name"] == "laya-multilingual"

    assert get_model_by_slug("unknown", "model") is None


def test_model_fields_complete():
    required_fields = {
        "id",
        "creator",
        "name",
        "display_name",
        "params",
        "context_window",
        "modality",
        "license",
        "summary",
        "description",
        "architecture",
        "huggingface_url",
        "benchmarks",
        "code_curl",
        "code_python",
    }
    models = get_all_models()
    for m in models:
        missing = required_fields - set(m.keys())
        assert not missing, f"Model {m.get('id')} missing fields: {missing}"
        assert isinstance(m["benchmarks"], list)
        for b in m["benchmarks"]:
            assert "metric" in b
            assert "value" in b
            assert "note" in b
        assert isinstance(m["code_curl"], str) and len(m["code_curl"]) > 0
        assert isinstance(m["code_python"], str) and len(m["code_python"]) > 0
