from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import os


def _parse_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _parse_int(value: Optional[str], default: int) -> int:
    if value is None or value.strip() == "":
        return default
    return int(value)


def _parse_csv(value: Optional[str]) -> Optional[List[str]]:
    if value is None:
        return None
    tokens = [item.strip() for item in value.split(",") if item.strip()]
    return tokens or None


@dataclass
class Config:
    """Centralized configuration loaded from environment variables."""

    model_name: str = "minishlab/potion-base-8M"
    alias_model_name: Optional[str] = None
    allowed_tokens: Optional[List[str]] = None
    port: int = 8080

    lazy_load_model: bool = False
    model_unload_enabled: bool = False
    model_unload_idle_timeout: int = 1800

    request_timeout_secs: int = 30
    request_body_limit_bytes: int = 2_000_000

    max_input_items: int = 512
    max_input_chars: int = 8192
    max_total_chars: int = 200_000

    concurrency_limit: int = 64

    model_load_max_retries: int = 5
    model_load_retry_base_ms: int = 200
    model_load_retry_max_ms: int = 5000
    model_load_timeout_secs: int = 120

    inference_max_retries: int = 2
    inference_retry_base_ms: int = 50
    inference_retry_max_ms: int = 500

    embedding_cache_max_entries: int = 1024
    embedding_cache_ttl_secs: int = 600

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            model_name=os.getenv("MODEL_NAME", cls.model_name),
            alias_model_name=os.getenv("ALIAS_MODEL_NAME") or None,
            allowed_tokens=_parse_csv(os.getenv("AUTHENTICATION_ALLOWED_TOKENS", "")),
            port=_parse_int(os.getenv("PORT"), cls.port),
            lazy_load_model=_parse_bool(os.getenv("LAZY_LOAD_MODEL"), cls.lazy_load_model),
            model_unload_enabled=_parse_bool(
                os.getenv("MODEL_UNLOAD_ENABLED"), cls.model_unload_enabled
            ),
            model_unload_idle_timeout=_parse_int(
                os.getenv("MODEL_UNLOAD_IDLE_TIMEOUT"), cls.model_unload_idle_timeout
            ),
            request_timeout_secs=_parse_int(
                os.getenv("REQUEST_TIMEOUT_SECS"), cls.request_timeout_secs
            ),
            request_body_limit_bytes=_parse_int(
                os.getenv("REQUEST_BODY_LIMIT_BYTES"), cls.request_body_limit_bytes
            ),
            max_input_items=_parse_int(os.getenv("MAX_INPUT_ITEMS"), cls.max_input_items),
            max_input_chars=_parse_int(os.getenv("MAX_INPUT_CHARS"), cls.max_input_chars),
            max_total_chars=_parse_int(os.getenv("MAX_TOTAL_CHARS"), cls.max_total_chars),
            concurrency_limit=_parse_int(
                os.getenv("CONCURRENCY_LIMIT"), cls.concurrency_limit
            ),
            model_load_max_retries=_parse_int(
                os.getenv("MODEL_LOAD_MAX_RETRIES"), cls.model_load_max_retries
            ),
            model_load_retry_base_ms=_parse_int(
                os.getenv("MODEL_LOAD_RETRY_BASE_MS"), cls.model_load_retry_base_ms
            ),
            model_load_retry_max_ms=_parse_int(
                os.getenv("MODEL_LOAD_RETRY_MAX_MS"), cls.model_load_retry_max_ms
            ),
            model_load_timeout_secs=_parse_int(
                os.getenv("MODEL_LOAD_TIMEOUT_SECS"), cls.model_load_timeout_secs
            ),
            inference_max_retries=_parse_int(
                os.getenv("INFERENCE_MAX_RETRIES"), cls.inference_max_retries
            ),
            inference_retry_base_ms=_parse_int(
                os.getenv("INFERENCE_RETRY_BASE_MS"), cls.inference_retry_base_ms
            ),
            inference_retry_max_ms=_parse_int(
                os.getenv("INFERENCE_RETRY_MAX_MS"), cls.inference_retry_max_ms
            ),
            embedding_cache_max_entries=_parse_int(
                os.getenv("EMBEDDING_CACHE_MAX_ENTRIES"),
                cls.embedding_cache_max_entries,
            ),
            embedding_cache_ttl_secs=_parse_int(
                os.getenv("EMBEDDING_CACHE_TTL_SECS"),
                cls.embedding_cache_ttl_secs,
            ),
        )

    def is_valid_token(self, token: str) -> bool:
        if not self.allowed_tokens:
            return True
        return token in self.allowed_tokens

    def is_auth_enabled(self) -> bool:
        return bool(self.allowed_tokens)


_config: Optional[Config] = None


def set_config(config: Config) -> None:
    global _config
    _config = config


def get_config() -> Config:
    return _config if _config is not None else Config()
