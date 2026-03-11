import importlib

from fastapi.testclient import TestClient


def _build_client(monkeypatch, **env):
    for key, value in env.items():
        monkeypatch.setenv(key, str(value))

    import src.config as config_module
    import src.app as app_module

    importlib.reload(config_module)
    importlib.reload(app_module)

    return TestClient(app_module.app)


def test_validation_empty_input(monkeypatch):
    client = _build_client(
        monkeypatch,
        LAZY_LOAD_MODEL="true",
        AUTHENTICATION_ALLOWED_TOKENS="",
    )
    with client:
        res = client.post(
            "/v1/embeddings",
            json={"input": "", "model": "minishlab/potion-base-8M"},
        )

    assert res.status_code == 400
    body = res.json()
    assert body["error"]["error_type"] == "invalid_request_error"
    assert "input" in (body["error"]["param"] or "")
    assert "empty" in body["error"]["message"]


def test_validation_max_items(monkeypatch):
    client = _build_client(
        monkeypatch,
        LAZY_LOAD_MODEL="true",
        AUTHENTICATION_ALLOWED_TOKENS="",
        MAX_INPUT_ITEMS="1",
    )
    with client:
        res = client.post(
            "/v1/embeddings",
            json={"input": ["a", "b"], "model": "minishlab/potion-base-8M"},
        )

    assert res.status_code == 400
    body = res.json()
    assert body["error"]["error_type"] == "invalid_request_error"
    assert "maximum is 1" in body["error"]["message"]
