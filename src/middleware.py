from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import get_config
from src.errors import ErrorResponse

logger = logging.getLogger("uvicorn")


class AuthMiddleware(BaseHTTPMiddleware):
    """Centralized authentication middleware."""

    _WELL_KNOWN_PREFIXES = ("/.well-known/", "/.well_known/")
    _WELL_KNOWN_EXACT = {"/.well-known", "/.well_known"}

    async def dispatch(self, request: Request, call_next):
        if self._is_well_known_path(request.url.path):
            return await call_next(request)

        config = get_config()
        if not config.is_auth_enabled():
            return await call_next(request)

        token = self._extract_bearer_token(request.headers.get("Authorization"))
        if not token or not config.is_valid_token(token):
            logger.warning(
                "Authentication failed for %s %s", request.method, request.url.path
            )
            response = JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=ErrorResponse.unauthorized(
                    "Invalid or missing authentication token"
                ).to_dict(),
            )
            response.headers["WWW-Authenticate"] = "Bearer"
            return response

        return await call_next(request)

    @classmethod
    def _is_well_known_path(cls, path: str) -> bool:
        if path in cls._WELL_KNOWN_EXACT:
            return True
        return path.startswith(cls._WELL_KNOWN_PREFIXES)

    @staticmethod
    def _extract_bearer_token(auth_header: Optional[str]) -> Optional[str]:
        if not auth_header:
            return None
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        token = parts[1].strip()
        return token if token else None


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Enforce per-request timeout."""

    async def dispatch(self, request: Request, call_next):
        config = get_config()
        try:
            async with asyncio.timeout(config.request_timeout_secs):
                return await call_next(request)
        except TimeoutError:
            logger.error("Request timeout for %s %s", request.method, request.url.path)
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content=ErrorResponse.server_error("Request timed out").to_dict(),
            )


class ConcurrencyLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests when concurrency limit is exceeded."""

    def __init__(self, app, concurrency_limit: int):
        super().__init__(app)
        self.concurrency_limit = max(1, concurrency_limit)
        self._semaphore = asyncio.Semaphore(self.concurrency_limit)

    async def dispatch(self, request: Request, call_next):
        acquired = False
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=0.001)
            acquired = True
        except TimeoutError:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=ErrorResponse.rate_limit(
                    "Service overloaded, try again later"
                ).to_dict(),
            )

        try:
            return await call_next(request)
        finally:
            if acquired:
                self._semaphore.release()


class MaxContentLengthMiddleware(BaseHTTPMiddleware):
    """Reject requests with body larger than configured limit."""

    def __init__(self, app, max_content_length: int):
        super().__init__(app)
        self.max_content_length = max_content_length

    async def dispatch(self, request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH"}:
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    size = int(content_length)
                except ValueError:
                    size = None
                if size is not None and size > self.max_content_length:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content=ErrorResponse.invalid_request(
                            f"Request body too large. Maximum is {self.max_content_length} bytes",
                            param="body",
                        ).to_dict(),
                    )
        return await call_next(request)
