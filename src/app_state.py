from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Optional

from src.config import Config
from src.vectorizer import Vectorizer

logger = logging.getLogger("uvicorn")


class AppState:
    def __init__(self, config: Config, model_path: str):
        self.config = config
        self.model_path = model_path
        self._vectorizer: Optional[Vectorizer] = None
        self._lock = asyncio.Lock()
        self._idle_task: Optional[asyncio.Task] = None
        self._last_request_time = 0 if config.lazy_load_model else self._now()

    @classmethod
    async def create(cls, config: Config, model_path: str) -> "AppState":
        state = cls(config, model_path)

        if config.lazy_load_model:
            logger.info("Lazy loading enabled - model will load on first request")
        else:
            logger.info("Eager loading model at startup: %s", config.model_name)
            start = time.time()
            state._vectorizer = await state._load_vectorizer_with_retry()
            elapsed = time.time() - start
            logger.info("Model loaded in %.2fs", elapsed)
            state._last_request_time = state._now()

        if config.model_unload_enabled:
            logger.info(
                "Model unloading enabled - idle timeout: %ss",
                config.model_unload_idle_timeout,
            )

        return state

    @staticmethod
    def _now() -> int:
        return int(time.time())

    async def get_vectorizer(self) -> Vectorizer:
        self._last_request_time = self._now()
        if self._vectorizer is not None:
            return self._vectorizer

        async with self._lock:
            if self._vectorizer is not None:
                return self._vectorizer

            logger.info("Loading model on demand: %s", self.config.model_name)
            start = time.time()
            self._vectorizer = await self._load_vectorizer_with_retry()
            elapsed = time.time() - start
            logger.info("Model loaded on demand in %.2fs", elapsed)
            return self._vectorizer

    async def unload_vectorizer(self) -> bool:
        async with self._lock:
            if self._vectorizer is None:
                return False
            logger.info("Unloading model to free memory")
            self._vectorizer.shutdown()
            self._vectorizer = None
        return True

    async def _load_vectorizer_with_retry(self) -> Vectorizer:
        max_attempts = max(1, self.config.model_load_max_retries)
        attempt = 0
        delay_ms = self.config.model_load_retry_base_ms

        while True:
            try:
                timeout = self.config.model_load_timeout_secs
                if timeout > 0:
                    return await asyncio.wait_for(
                        asyncio.to_thread(
                            Vectorizer, self.model_path, config=self.config
                        ),
                        timeout=timeout,
                    )
                return await asyncio.to_thread(
                    Vectorizer, self.model_path, config=self.config
                )
            except Exception as exc:
                attempt += 1
                if attempt >= max_attempts:
                    logger.exception(
                        "Failed to load model after %s attempts", attempt
                    )
                    raise

                jitter = random.uniform(0, delay_ms * 0.1)
                wait_ms = min(delay_ms + jitter, self.config.model_load_retry_max_ms)
                logger.warning(
                    "Model load attempt %s failed, retrying in %.2fs: %s",
                    attempt,
                    wait_ms / 1000.0,
                    exc,
                )
                await asyncio.sleep(wait_ms / 1000.0)
                delay_ms = min(delay_ms * 2, self.config.model_load_retry_max_ms)

    def start_idle_monitor(self) -> None:
        if not self.config.model_unload_enabled:
            return
        if self._idle_task is None or self._idle_task.done():
            self._idle_task = asyncio.create_task(self._idle_monitor())

    async def _idle_monitor(self) -> None:
        check_interval = max(self.config.model_unload_idle_timeout // 10, 10)
        while True:
            await asyncio.sleep(check_interval)
            last_request = self._last_request_time
            if last_request == 0:
                continue
            idle_duration = self._now() - last_request
            if idle_duration >= self.config.model_unload_idle_timeout:
                was_unloaded = await self.unload_vectorizer()
                if was_unloaded:
                    logger.info(
                        "Model was idle for %ss (threshold: %ss)",
                        idle_duration,
                        self.config.model_unload_idle_timeout,
                    )

    async def is_ready(self) -> bool:
        return self._vectorizer is not None
