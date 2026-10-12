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


def test_model_detail_page_contents(client_no_auth):
    resp = client_no_auth.get("/vllm-sr/d3-lite")
    assert resp.status_code == 200
    html = resp.text
    assert "Model Card" in html
    assert "Playground" in html
    assert "vllm-sr/d3-lite" in html
    assert "Parameters" in html
    assert "Context" in html
    assert "/v1/systemone" in html


def test_admin_login_and_model_route_precedence(client_no_auth):
    resp_login = client_no_auth.get("/admin/login")
    assert resp_login.status_code == 200
    assert "Admin Sign In" in resp_login.text

    resp_model = client_no_auth.get("/vllm-sr/d3-lite")
    assert resp_model.status_code == 200
    assert "d3-lite" in resp_model.text

