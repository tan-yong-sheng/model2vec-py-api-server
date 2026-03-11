import os

from src.config import Config


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "test/model")
    monkeypatch.setenv("ALIAS_MODEL_NAME", "alias-model")
    monkeypatch.setenv("AUTHENTICATION_ALLOWED_TOKENS", "token1, token2, ,")
    monkeypatch.setenv("PORT", "9001")
    monkeypatch.setenv("LAZY_LOAD_MODEL", "true")
    monkeypatch.setenv("MODEL_UNLOAD_ENABLED", "true")
    monkeypatch.setenv("MODEL_UNLOAD_IDLE_TIMEOUT", "120")
    monkeypatch.setenv("REQUEST_TIMEOUT_SECS", "15")
    monkeypatch.setenv("REQUEST_BODY_LIMIT_BYTES", "12345")
    monkeypatch.setenv("MAX_INPUT_ITEMS", "8")
    monkeypatch.setenv("MAX_INPUT_CHARS", "256")
    monkeypatch.setenv("MAX_TOTAL_CHARS", "1024")
    monkeypatch.setenv("CONCURRENCY_LIMIT", "3")
    monkeypatch.setenv("MODEL_LOAD_MAX_RETRIES", "2")
    monkeypatch.setenv("MODEL_LOAD_RETRY_BASE_MS", "10")
    monkeypatch.setenv("MODEL_LOAD_RETRY_MAX_MS", "100")
    monkeypatch.setenv("MODEL_LOAD_TIMEOUT_SECS", "7")
    monkeypatch.setenv("INFERENCE_MAX_RETRIES", "4")
    monkeypatch.setenv("INFERENCE_RETRY_BASE_MS", "5")
    monkeypatch.setenv("INFERENCE_RETRY_MAX_MS", "50")
    monkeypatch.setenv("EMBEDDING_CACHE_MAX_ENTRIES", "256")
    monkeypatch.setenv("EMBEDDING_CACHE_TTL_SECS", "30")

    config = Config.from_env()

    assert config.model_name == "test/model"
    assert config.alias_model_name == "alias-model"
    assert config.allowed_tokens == ["token1", "token2"]
    assert config.port == 9001
    assert config.lazy_load_model is True
    assert config.model_unload_enabled is True
    assert config.model_unload_idle_timeout == 120
    assert config.request_timeout_secs == 15
    assert config.request_body_limit_bytes == 12345
    assert config.max_input_items == 8
    assert config.max_input_chars == 256
    assert config.max_total_chars == 1024
    assert config.concurrency_limit == 3
    assert config.model_load_max_retries == 2
    assert config.model_load_retry_base_ms == 10
    assert config.model_load_retry_max_ms == 100
    assert config.model_load_timeout_secs == 7
    assert config.inference_max_retries == 4
    assert config.inference_retry_base_ms == 5
    assert config.inference_retry_max_ms == 50
    assert config.embedding_cache_max_entries == 256
    assert config.embedding_cache_ttl_secs == 30

    assert config.is_auth_enabled() is True
    assert config.is_valid_token("token1") is True
    assert config.is_valid_token("nope") is False

