# Rust-Inspired Code Patterns for Python Implementation

## Quick Reference for Feature Implementation

This document provides code pattern recommendations based on Rust's approach that can be applied to the Python codebase.

---

## Pattern 1: Config Management System

### ❌ Current Python Approach (Scattered)
```python
# app.py
allowed_tokens: List[str] = None
model_alias: str = None

def get_allowed_tokens() -> List[str] | None:
    if (tokens := os.getenv("AUTHENTICATION_ALLOWED_TOKENS", "").strip()):
        return tokens.strip().split(",")
```

### ✅ Recommended Rust-Inspired Pattern
```python
# config.py - New structured config module
from dataclasses import dataclass
from typing import Optional, List
import os

@dataclass
class Config:
    """Centralized configuration from environment variables"""

    # Core settings
    model_name: str = "minishlab/potion-base-8M"
    alias_model_name: Optional[str] = None
    allowed_tokens: List[str] = None
    port: int = 8080

    # Memory management
    lazy_load_model: bool = False
    model_unload_enabled: bool = False
    model_unload_idle_timeout: int = 1800

    # Request handling
    request_timeout_secs: int = 30
    request_body_limit_bytes: int = 2_000_000

    # Input validation
    max_input_items: int = 512
    max_input_chars: int = 8192
    max_total_chars: int = 200_000

    # Concurrency & performance
    concurrency_limit: int = 64

    # Model loading resilience
    model_load_max_retries: int = 5
    model_load_retry_base_ms: int = 200
    model_load_retry_max_ms: int = 5000
    model_load_timeout_secs: int = 120

    # Inference resilience
    inference_max_retries: int = 2
    inference_retry_base_ms: int = 50
    inference_retry_max_ms: int = 500

    # Caching
    embedding_cache_max_entries: int = 1024
    embedding_cache_ttl_secs: int = 600

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables"""
        return cls(
            model_name=os.getenv("MODEL_NAME", cls.model_name),
            alias_model_name=os.getenv("ALIAS_MODEL_NAME"),
            allowed_tokens=(
                os.getenv("AUTHENTICATION_ALLOWED_TOKENS", "")
                .strip()
                .split(",") if os.getenv("AUTHENTICATION_ALLOWED_TOKENS", "").strip() else None
            ),
            port=int(os.getenv("PORT", cls.port)),
            lazy_load_model=os.getenv("LAZY_LOAD_MODEL", "false").lower() == "true",
            model_unload_enabled=os.getenv("MODEL_UNLOAD_ENABLED", "false").lower() == "true",
            model_unload_idle_timeout=int(os.getenv("MODEL_UNLOAD_IDLE_TIMEOUT", cls.model_unload_idle_timeout)),
            request_timeout_secs=int(os.getenv("REQUEST_TIMEOUT_SECS", cls.request_timeout_secs)),
            request_body_limit_bytes=int(os.getenv("REQUEST_BODY_LIMIT_BYTES", cls.request_body_limit_bytes)),
            max_input_items=int(os.getenv("MAX_INPUT_ITEMS", cls.max_input_items)),
            max_input_chars=int(os.getenv("MAX_INPUT_CHARS", cls.max_input_chars)),
            max_total_chars=int(os.getenv("MAX_TOTAL_CHARS", cls.max_total_chars)),
            concurrency_limit=int(os.getenv("CONCURRENCY_LIMIT", cls.concurrency_limit)),
            model_load_max_retries=int(os.getenv("MODEL_LOAD_MAX_RETRIES", cls.model_load_max_retries)),
            model_load_retry_base_ms=int(os.getenv("MODEL_LOAD_RETRY_BASE_MS", cls.model_load_retry_base_ms)),
            model_load_retry_max_ms=int(os.getenv("MODEL_LOAD_RETRY_MAX_MS", cls.model_load_retry_max_ms)),
            model_load_timeout_secs=int(os.getenv("MODEL_LOAD_TIMEOUT_SECS", cls.model_load_timeout_secs)),
            inference_max_retries=int(os.getenv("INFERENCE_MAX_RETRIES", cls.inference_max_retries)),
            inference_retry_base_ms=int(os.getenv("INFERENCE_RETRY_BASE_MS", cls.inference_retry_base_ms)),
            inference_retry_max_ms=int(os.getenv("INFERENCE_RETRY_MAX_MS", cls.inference_retry_max_ms)),
            embedding_cache_max_entries=int(os.getenv("EMBEDDING_CACHE_MAX_ENTRIES", cls.embedding_cache_max_entries)),
            embedding_cache_ttl_secs=int(os.getenv("EMBEDDING_CACHE_TTL_SECS", cls.embedding_cache_ttl_secs)),
        )

    def is_valid_token(self, token: str) -> bool:
        """Check if a token is in the allowed list"""
        if not self.allowed_tokens:
            return True  # No auth required
        return token in self.allowed_tokens

    def is_auth_enabled(self) -> bool:
        """Check if authentication is enabled"""
        return self.allowed_tokens is not None and len(self.allowed_tokens) > 0
```

### Usage in app.py
```python
from config import Config
from fastapi import FastAPI

# In lifespan
async def lifespan(app: FastAPI):
    global config
    config = Config.from_env()
    vec = Vectorizer(model_path="./models", config=config)
    yield
```

---

## Pattern 2: Structured Error Responses

### ❌ Current Python Approach
```python
return {"error": "Unauthorized"}
return {"error": str(e)}
```

### ✅ Recommended Pattern (OpenAI-Compatible)
```python
# errors.py
from typing import Optional
from pydantic import BaseModel

class ErrorDetail(BaseModel):
    message: str
    error_type: str = "invalid_request_error"
    param: Optional[str] = None
    code: Optional[str] = None

class ErrorResponse(BaseModel):
    error: ErrorDetail

    @staticmethod
    def invalid_request(message: str, param: Optional[str] = None) -> "ErrorResponse":
        return ErrorResponse(
            error=ErrorDetail(
                message=message,
                error_type="invalid_request_error",
                param=param,
            )
        )

    @staticmethod
    def unauthorized(message: str) -> "ErrorResponse":
        return ErrorResponse(
            error=ErrorDetail(
                message=message,
                error_type="authentication_error",
            )
        )

    @staticmethod
    def not_found(message: str) -> "ErrorResponse":
        return ErrorResponse(
            error=ErrorDetail(
                message=message,
                error_type="not_found_error",
            )
        )

    @staticmethod
    def server_error(message: str) -> "ErrorResponse":
        return ErrorResponse(
            error=ErrorDetail(
                message=message,
                error_type="server_error",
            )
        )

    @staticmethod
    def rate_limit() -> "ErrorResponse":
        return ErrorResponse(
            error=ErrorDetail(
                message="Rate limit exceeded",
                error_type="rate_limit_error",
            )
        )

# Usage
@app.post("/v1/embeddings")
async def embed(item: VectorInput):
    if item.model not in available_models:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse.invalid_request(
                f"Model '{item.model}' not found",
                param="model"
            ).dict()
        )
```

---

## Pattern 3: Input Validation with Limits

### ❌ Current Python Approach
```python
class VectorInput(BaseModel):
    input: str | list
    # No validation!
```

### ✅ Recommended Pattern
```python
from pydantic import BaseModel, validator, root_validator
from typing import Union, List

class VectorInput(BaseModel):
    input: Union[str, List[str]]
    model: str
    encoding_format: str = "float"
    dimensions: Optional[int] = None

    @validator("input")
    def validate_input(cls, v):
        """Validate input format and content"""
        if isinstance(v, str):
            if not v:
                raise ValueError("input string cannot be empty")
            return v
        elif isinstance(v, list):
            if not v:
                raise ValueError("input array cannot be empty")
            if not all(isinstance(item, str) for item in v):
                raise ValueError("all input items must be strings")
            return v
        raise ValueError("input must be a string or array of strings")

    @validator("model")
    def validate_model(cls, v):
        """Validate model name is not empty"""
        if not v or not v.strip():
            raise ValueError("model must not be empty")
        return v

    @validator("encoding_format")
    def validate_encoding_format(cls, v):
        """Validate encoding format"""
        if v not in ["float", "base64"]:
            raise ValueError("encoding_format must be 'float' or 'base64'")
        return v

    @validator("dimensions")
    def validate_dimensions(cls, v):
        """Validate dimensions if provided"""
        if v is not None and v <= 0:
            raise ValueError("dimensions must be positive")
        return v

    @root_validator
    def validate_input_limits(cls, values):
        """Validate input against configured limits"""
        from config import config  # Get global config

        input_data = values.get("input")

        if isinstance(input_data, str):
            items = [input_data]
        else:
            items = input_data

        # Check item count limit
        if len(items) > config.max_input_items:
            raise ValueError(
                f"input array contains {len(items)} items, "
                f"maximum is {config.max_input_items}"
            )

        # Check character limits
        total_chars = sum(len(item) for item in items)

        for i, item in enumerate(items):
            if len(item) > config.max_input_chars:
                raise ValueError(
                    f"input item {i} contains {len(item)} characters, "
                    f"maximum per item is {config.max_input_chars}"
                )

        if total_chars > config.max_total_chars:
            raise ValueError(
                f"total characters {total_chars} exceeds "
                f"maximum of {config.max_total_chars}"
            )

        return values
```

---

## Pattern 4: Vectorizer with Retry Logic

### ❌ Current Python Approach
```python
@cached(cache=TTLCache(maxsize=1024, ttl=600))
def vectorize(self, text: str | list[str], config: VectorInputConfig):
    embeddings = self.model.encode(input_list, use_multiprocessing=True)
    return embeddings
```

### ✅ Recommended Pattern with Retries
```python
import asyncio
import random
from typing import List, Optional
from functools import lru_cache
from cachetools import cached, TTLCache

class Model2VecVectorizer:
    def __init__(self, model_path: str, config: Config):
        self.model = StaticModel.load_local(model_path)
        self.config = config
        self.cache = TTLCache(
            maxsize=config.embedding_cache_max_entries,
            ttl=config.embedding_cache_ttl_secs
        )

    async def vectorize(self, texts: List[str]) -> List[List[float]]:
        """Vectorize texts with smart caching and retry logic"""

        # Check cache for each input
        results = {}
        missing_texts = []
        missing_indices = []

        for idx, text in enumerate(texts):
            if text in self.cache:
                results[idx] = self.cache[text]
            else:
                missing_texts.append(text)
                missing_indices.append(idx)

        # Batch process missing texts with retry logic
        if missing_texts:
            embeddings = await self._encode_with_retry(missing_texts)

            # Cache and store results
            for idx, embedding in zip(missing_indices, embeddings):
                self.cache[texts[idx]] = embedding
                results[idx] = embedding

        # Return results in original order
        return [results[i] for i in range(len(texts))]

    async def _encode_with_retry(self, texts: List[str]) -> List[List[float]]:
        """Encode texts with exponential backoff retry logic"""

        attempt = 0
        delay = self.config.inference_retry_base_ms

        while attempt < self.config.inference_max_retries:
            try:
                # Run inference in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                embeddings = await loop.run_in_executor(
                    None,
                    lambda: self.model.encode(texts, use_multiprocessing=True)
                )
                return embeddings.tolist()

            except Exception as e:
                attempt += 1
                if attempt >= self.config.inference_max_retries:
                    logger.error(f"Failed to encode after {attempt} attempts: {e}")
                    raise

                # Exponential backoff with jitter
                jitter = random.uniform(0, delay * 0.1)
                wait_time = min(
                    (delay + jitter) / 1000.0,
                    self.config.inference_retry_max_ms / 1000.0
                )
                logger.warning(
                    f"Encoding attempt {attempt} failed, "
                    f"retrying in {wait_time:.2f}s: {e}"
                )
                await asyncio.sleep(wait_time)
                delay *= 2

        raise RuntimeError(f"Failed to encode after {attempt} attempts")
```

---

## Pattern 5: Auth Middleware (Centralized)

### ❌ Current Python Approach
```python
@app.post("/v1/embeddings")
async def embed(item: VectorInput,
                response: Response,
                auth: Optional[HTTPAuthorizationCredentials] = Depends(get_bearer_token)):
    if is_authorized(auth):
        # route logic
    else:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"error": "Unauthorized"}
```

### ✅ Recommended Middleware Pattern
```python
# middleware.py
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from config import config
from errors import ErrorResponse
import logging

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    """Centralized authentication middleware"""

    async def dispatch(self, request: Request, call_next):
        # Skip auth for health checks
        if request.url.path in ["/.well-known/live", "/.well-known/ready"]:
            return await call_next(request)

        # Check if auth is enabled
        if not config.is_auth_enabled():
            return await call_next(request)

        # Extract bearer token
        auth_header = request.headers.get("Authorization")
        token = self._extract_bearer_token(auth_header)

        # Validate token
        if not token or not config.is_valid_token(token):
            logger.warning(f"Authentication failed for {request.method} {request.url.path}")

            # Return standardized error with WWW-Authenticate header
            from fastapi.responses import JSONResponse
            response = JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=ErrorResponse.unauthorized(
                    "Invalid or missing authentication token"
                ).dict()
            )
            response.headers["WWW-Authenticate"] = "Bearer"
            return response

        return await call_next(request)

    @staticmethod
    def _extract_bearer_token(auth_header: Optional[str]) -> Optional[str]:
        """Extract bearer token from Authorization header"""
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        token = parts[1].strip()
        return token if token else None

# In app.py
app.add_middleware(AuthMiddleware)
```

---

## Pattern 6: Request Timeout & Size Limits

### ❌ Current Python Approach
```python
# No timeout enforcement
# No body size limiting
```

### ✅ Recommended Pattern
```python
# middleware.py or app initialization
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio
import logging

logger = logging.getLogger(__name__)

class TimeoutMiddleware(BaseHTTPMiddleware):
    """Enforce request timeout"""

    async def dispatch(self, request: Request, call_next):
        try:
            timeout = asyncio.TimeoutError
            async with asyncio.timeout(config.request_timeout_secs):
                return await call_next(request)
        except asyncio.TimeoutError:
            logger.error(f"Request timeout for {request.method} {request.url.path}")
            return JSONResponse(
                status_code=408,
                content=ErrorResponse.server_error("Request timeout").dict()
            )

# In FastAPI initialization
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    global config, vec

    config = Config.from_env()

    # Configure request limits
    app.add_middleware(
        MaxContentLengthMiddleware,
        max_content_length=config.request_body_limit_bytes
    )

    vec = Vectorizer(model_path="./models", config=config)

    yield

app = FastAPI(lifespan=lifespan)

# Body size validation middleware
class MaxContentLengthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_content_length):
        super().__init__(app)
        self.max_content_length = max_content_length

    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_content_length:
                return JSONResponse(
                    status_code=413,
                    content=ErrorResponse.invalid_request(
                        f"Request body too large. Maximum is "
                        f"{self.max_content_length} bytes"
                    ).dict()
                )
        return await call_next(request)
```

---

## Pattern 7: Health Checks with State Tracking

### ❌ Current Python Approach
```python
@app.get("/.well-known/live", response_class=Response)
@app.get("/.well-known/ready", response_class=Response)
async def live_and_ready(response: Response):
    response.status_code = status.HTTP_204_NO_CONTENT
    # Both return same status!
```

### ✅ Recommended Pattern
```python
# app_state.py
import asyncio
from typing import Optional
from model2vec import StaticModel

class AppState:
    """Manage application state"""

    def __init__(self):
        self.model: Optional[StaticModel] = None
        self.model_loading: asyncio.Lock = asyncio.Lock()
        self.is_model_loaded = False

    async def load_model(self, config: Config) -> None:
        """Load model with proper state tracking"""
        async with self.model_loading:
            if self.is_model_loaded:
                return

            try:
                loop = asyncio.get_event_loop()
                self.model = await loop.run_in_executor(
                    None,
                    lambda: StaticModel.load_local(config.model_name)
                )
                self.is_model_loaded = True
                logger.info("Model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                self.is_model_loaded = False
                raise

    async def is_ready(self) -> bool:
        """Check if model is ready"""
        return self.is_model_loaded

# In app.py
app_state = AppState()

@app.get("/.well-known/live")
async def live():
    """Liveness check - always returns 204"""
    return Response(status_code=204)

@app.get("/.well-known/ready")
async def ready():
    """Readiness check - returns 204 if ready, 503 if loading"""
    is_ready = await app_state.is_ready()
    if is_ready:
        return Response(status_code=204)
    else:
        return JSONResponse(
            status_code=503,
            content=ErrorResponse.server_error("Model not loaded").dict()
        )

@app.get("/")
async def root():
    """Root endpoint with service info"""
    is_ready = await app_state.is_ready()
    return {
        "service": "model2vec-api",
        "status": "ready" if is_ready else "starting",
        "endpoints": {
            "live": "/.well-known/live",
            "ready": "/.well-known/ready",
            "meta": "/meta",
            "models": "/v1/models",
            "embeddings": "/v1/embeddings"
        }
    }
```

---

## Pattern 8: Testing with Mocks

### ❌ Current Python Approach
```python
# smoke_test.py - Manual testing only
# No unit tests
# No mocking
```

### ✅ Recommended Pattern
```python
# tests/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app import app, app_state
from config import Config
from vectorizer import Vectorizer

@pytest.fixture
def mock_config():
    """Fixture for test configuration"""
    return Config(
        model_name="test-model",
        max_input_items=10,
        max_input_chars=1000,
        max_total_chars=10_000,
        embedding_cache_max_entries=10,
        embedding_cache_ttl_secs=60,
    )

@pytest.fixture
def mock_vectorizer():
    """Fixture for mock vectorizer"""
    vectorizer = AsyncMock(spec=Vectorizer)

    async def mock_vectorize(texts):
        # Return mock embeddings
        return [[1.0, 2.0, 3.0] for _ in texts]

    vectorizer.vectorize.side_effect = mock_vectorize
    return vectorizer

@pytest.fixture
async def client(mock_vectorizer, mock_config):
    """Fixture for test client"""
    from fastapi.testclient import TestClient

    app_state.vectorizer = mock_vectorizer
    return TestClient(app)

# tests/test_api.py
import pytest

@pytest.mark.asyncio
async def test_embeddings_float_format(client):
    """Test embeddings endpoint with float format"""
    response = client.post(
        "/v1/embeddings",
        json={
            "input": "hello world",
            "model": "test-model",
            "encoding_format": "float"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert len(data["data"]) == 1
    assert data["data"][0]["embedding"] == [1.0, 2.0, 3.0]

@pytest.mark.asyncio
async def test_embeddings_invalid_model(client):
    """Test embeddings with invalid model"""
    response = client.post(
        "/v1/embeddings",
        json={
            "input": "hello",
            "model": "unknown-model"
        }
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["error_type"] == "invalid_request_error"

@pytest.mark.asyncio
async def test_input_validation_too_many_items(client, mock_config):
    """Test validation for too many input items"""
    response = client.post(
        "/v1/embeddings",
        json={
            "input": ["text"] * (mock_config.max_input_items + 1),
            "model": "test-model"
        }
    )

    assert response.status_code == 422  # Validation error

@pytest.mark.asyncio
async def test_health_check_live(client):
    """Test liveness endpoint"""
    response = client.get("/.well-known/live")
    assert response.status_code == 204

@pytest.mark.asyncio
async def test_health_check_ready(client):
    """Test readiness endpoint"""
    response = client.get("/.well-known/ready")
    assert response.status_code == 204
```

---

## Summary of Patterns

| Pattern | Impact | Effort |
|---------|--------|--------|
| Structured Config | Foundation for all features | High |
| Standardized Errors | API consistency | Medium |
| Input Validation | Security & reliability | Medium |
| Retry Logic | Production resilience | High |
| Auth Middleware | Clean architecture | Medium |
| Timeout/Limits | Operational safety | Low-Medium |
| Health Checks | Observability | Low-Medium |
| Testing Framework | Quality assurance | High |

**Recommended Implementation Order**:
1. Config Management (enables everything else)
2. Error Responses (consistency)
3. Input Validation (security)
4. Testing Framework (verify each feature)
5. Retry Logic (reliability)
6. Auth Middleware (architecture)
7. Health Checks (observability)
8. Timeout/Limits (safety)

