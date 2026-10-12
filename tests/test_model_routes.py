def test_model_detail_route_success(client_no_auth):
    resp = client_no_auth.get("/vllm-sr/d3-lite")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "d3-lite" in resp.text
    assert "vllm-sr" in resp.text

    resp_kev = client_no_auth.get("/jaredpalmer/kev-0.8b")
    assert resp_kev.status_code == 200
    assert "kev-0.8b" in resp_kev.text

    resp_laya = client_no_auth.get("/convaiinnovations/laya-multilingual")
    assert resp_laya.status_code == 200
    assert "laya-multilingual" in resp_laya.text


def test_model_detail_route_not_found(client_no_auth):
    resp = client_no_auth.get("/nonexistent/model-xyz")
    assert resp.status_code == 404
