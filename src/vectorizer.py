import asyncio
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from operator import attrgetter

from cachetools import TTLCache, cachedmethod
from cachetools.keys import hashkey
from pydantic import BaseModel, field_validator, model_validator

from src.config import Config, get_config
from model2vec import StaticModel

logger = logging.getLogger("uvicorn")


class VectorInputConfig(BaseModel):
    pooling_strategy: Optional[str] = None
    task_type: Optional[str] = None

    def __hash__(self):
        return hash((self.pooling_strategy, self.task_type))

    def __eq__(self, other):
        if isinstance(other, VectorInputConfig):
            return (
                self.pooling_strategy == other.pooling_strategy
                and self.task_type == other.task_type
            )
        return False


class VectorInput(BaseModel):
    input: str | list[str]
    model: str
    config: Optional[VectorInputConfig] = None
    encoding_format: str = "float"
    dimensions: Optional[int] = None

    def __hash__(self):
        if isinstance(self.input, list):
            input_hashable = tuple(self.input)  # Convert list to tuple for hashability
        else:
            input_hashable = self.input
        return hash((input_hashable, self.config))

    def __eq__(self, other):
        if isinstance(other, VectorInput):
            return self.input == other.input and self.config == other.config
        return False

    @field_validator("input")
    @classmethod
    def validate_input(cls, value):
        if isinstance(value, str):
            if not value.strip():
                raise ValueError("input string cannot be empty")
            return value
        if isinstance(value, list):
            if not value:
                raise ValueError("input array cannot be empty")
            for item in value:
                if not isinstance(item, str):
                    raise ValueError("all input items must be strings")
                if item == "":
                    raise ValueError("input array contains empty string")
            return value
        raise ValueError("input must be a string or array of strings")

    @field_validator("model")
    @classmethod
    def validate_model(cls, value):
        if not value or not value.strip():
            raise ValueError("model must not be empty")
        return value

    @field_validator("encoding_format")
    @classmethod
    def validate_encoding_format(cls, value):
        if value not in {"float", "base64"}:
            raise ValueError("encoding_format must be 'float' or 'base64'")
        return value

    @field_validator("dimensions")
    @classmethod
    def validate_dimensions(cls, value):
        if value is not None and value <= 0:
            raise ValueError("dimensions must be positive")
        return value

    @model_validator(mode="after")
    def validate_input_limits(self):
        config = get_config()
        if isinstance(self.input, str):
            items = [self.input]
        else:
            items = list(self.input)

        if len(items) > config.max_input_items:
            raise ValueError(
                f"input array contains {len(items)} items, maximum is {config.max_input_items}"
            )

        total_chars = sum(len(item) for item in items)
        for index, item in enumerate(items):
            if len(item) > config.max_input_chars:
                raise ValueError(
                    f"input item {index} contains {len(item)} characters, "
                    f"maximum per item is {config.max_input_chars}"
                )

        if total_chars > config.max_total_chars:
            raise ValueError(
                f"total characters {total_chars} exceeds maximum of {config.max_total_chars}"
            )

        return self


class Model2VecVectorizer:
    model: StaticModel

    def __init__(self, model_path: str, config: Config):
        self.model = StaticModel.load_local(model_path)
        self.config = config
        self.cache = TTLCache(
            maxsize=config.embedding_cache_max_entries,
            ttl=config.embedding_cache_ttl_secs,
        )

    def _cache_key(self, text: str | list[str], config: Optional[VectorInputConfig]):
        if isinstance(text, list):
            text = tuple(text)
        return hashkey(text, config)

    @cachedmethod(cache=attrgetter("cache"), key=lambda self, text, config: self._cache_key(text, config))
    def _vectorize_cached(self, text: str | tuple[str, ...], config: Optional[VectorInputConfig]):
        if isinstance(text, str):
            input_list = [text]
        else:
            input_list = list(text)

        embeddings = self._encode_with_retry(input_list)
        return embeddings

    def _encode_with_retry(self, input_list: list[str]):
        max_attempts = max(1, self.config.inference_max_retries)
        attempt = 0
        delay_ms = self.config.inference_retry_base_ms

        while True:
            try:
                return self.model.encode(input_list, use_multiprocessing=True)
            except Exception as exc:
                attempt += 1
                if attempt >= max_attempts:
                    logger.exception(
                        "Failed to encode after %s attempts", attempt
                    )
                    raise

                jitter = random.uniform(0, delay_ms * 0.1)
                wait_ms = min(delay_ms + jitter, self.config.inference_retry_max_ms)
                logger.warning(
                    "Encoding attempt %s failed, retrying in %.2fs: %s",
                    attempt,
                    wait_ms / 1000.0,
                    exc,
                )
                time.sleep(wait_ms / 1000.0)
                delay_ms = min(delay_ms * 2, self.config.inference_retry_max_ms)

    def vectorize(self, text: str | list[str], config: Optional[VectorInputConfig]):
        return self._vectorize_cached(text, config)


class Vectorizer:
    executor: ThreadPoolExecutor

    def __init__(
        self,
        model_path: str,
        config: Config,
    ):
        max_workers = max(1, config.concurrency_limit)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.vectorizer = Model2VecVectorizer(model_path, config)
        self.config = config

    async def vectorize(self, input_data: str | list[str], config: Optional[VectorInputConfig]):
        future = self.executor.submit(self.vectorizer.vectorize, input_data, config)
        try:
            if self.config.request_timeout_secs > 0:
                return await asyncio.wait_for(
                    asyncio.wrap_future(future),
                    timeout=self.config.request_timeout_secs,
                )
            return await asyncio.wrap_future(future)
        except TimeoutError:
            future.cancel()
            logger.error("Inference timed out after %ss", self.config.request_timeout_secs)
            raise

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False)
