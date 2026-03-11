# Implementation Roadmap & Task Checklist

## Overview

This document provides a prioritized list of features needed to align the Python API server with the Rust implementation. Features are grouped by priority and complexity.

---

## ✅ PHASE 1: CRITICAL FOUNDATIONS (Week 1-2)

These are foundational features that enable all other enhancements.

### Task 1.1: Implement Structured Config System
**Priority**: 🔴 CRITICAL
**Effort**: 4-6 hours
**Files to Create**: `src/config.py`
**Files to Modify**: `app.py`

**Checklist**:
- [ ] Create `Config` dataclass with all 20+ parameters
- [ ] Implement `Config.from_env()` classmethod
- [ ] Add type hints for all fields
- [ ] Add default values matching Rust implementation
- [ ] Add validation methods: `is_valid_token()`, `is_auth_enabled()`
- [ ] Add docstrings for all parameters
- [ ] Create `.env.example` with all config variables
- [ ] Update app.py to use Config instance
- [ ] Remove global variables (allowed_tokens, model_alias)

**Expected Changes**:
- Before: Scattered `os.getenv()` calls (~20 places)
- After: Single `Config.from_env()` call in lifespan

**Tests Needed**:
- [ ] Test default values
- [ ] Test environment variable parsing
- [ ] Test token validation
- [ ] Test auth enable/disable logic

---

### Task 1.2: Implement Standardized Error Responses
**Priority**: 🔴 CRITICAL
**Effort**: 2-3 hours
**Files to Create**: `src/errors.py`
**Files to Modify**: `app.py`

**Checklist**:
- [ ] Create `ErrorDetail` Pydantic model
- [ ] Create `ErrorResponse` Pydantic model with static methods
- [ ] Implement `ErrorResponse.invalid_request()`
- [ ] Implement `ErrorResponse.unauthorized()`
- [ ] Implement `ErrorResponse.not_found()`
- [ ] Implement `ErrorResponse.server_error()`
- [ ] Implement `ErrorResponse.rate_limit()`
- [ ] Update all error responses in routes to use ErrorResponse
- [ ] Add WWW-Authenticate header to auth errors
- [ ] Update test files to validate error format

**Expected Changes**:
- Before: `{"error": "Unauthorized"}`
- After: `{"error": {"message": "...", "error_type": "...", "param": "..."}}`

**Tests Needed**:
- [ ] Test each error type format
- [ ] Test WWW-Authenticate header presence

---

### Task 1.3: Add Comprehensive Input Validation
**Priority**: 🔴 CRITICAL
**Effort**: 3-4 hours
**Files to Modify**: `vectorizer.py`

**Checklist**:
- [ ] Add `@validator` for input field in VectorInput
- [ ] Add `@validator` for model field
- [ ] Add `@validator` for encoding_format field
- [ ] Add `@validator` for dimensions field
- [ ] Add `@root_validator` for input limit validation
- [ ] Check max_input_items against config
- [ ] Check max_input_chars against config
- [ ] Check max_total_chars against config
- [ ] Provide clear error messages for each validation
- [ ] Test all validation paths

**Expected Changes**:
- Before: `{"error": "..."}`
- After: `{"error": {"message": "input array contains 1000 items, maximum is 512", "param": "input"}}`

**Tests Needed**:
- [ ] Test max items validation
- [ ] Test max chars per item validation
- [ ] Test max total chars validation
- [ ] Test empty input validation
- [ ] Test dimensions validation

---

## 🟠 PHASE 2: PRODUCTION RELIABILITY (Week 2-3)

These features improve reliability and error recovery.

### Task 2.1: Add Inference Retry Logic with Backoff
**Priority**: 🟠 HIGH
**Effort**: 4-5 hours
**Files to Modify**: `vectorizer.py`

**Checklist**:
- [ ] Refactor `Model2VecVectorizer.vectorize()` to separate cache checking
- [ ] Create `_encode_with_retry()` method with retry loop
- [ ] Implement exponential backoff calculation
- [ ] Add jitter to backoff delays
- [ ] Use `loop.run_in_executor()` for non-blocking execution
- [ ] Log retry attempts with details
- [ ] Respect `config.inference_max_retries`
- [ ] Respect `config.inference_retry_base_ms` and `inference_retry_max_ms`
- [ ] Raise exception after max retries exceeded
- [ ] Test retry behavior with mock failures

**Expected Behavior**:
- Attempt 1 fails → wait 50ms
- Attempt 2 fails → wait 100ms (exponential)
- Attempt 3 fails → raise exception

**Tests Needed**:
- [ ] Test successful encode on first attempt
- [ ] Test successful encode on retry
- [ ] Test failure after max retries
- [ ] Test backoff delays increase exponentially
- [ ] Test jitter is applied

---

### Task 2.2: Add Request Timeout Enforcement
**Priority**: 🟠 HIGH
**Effort**: 2-3 hours
**Files to Create**: `src/middleware.py`
**Files to Modify**: `app.py`

**Checklist**:
- [ ] Create `TimeoutMiddleware` class
- [ ] Use `asyncio.timeout()` context manager
- [ ] Wrap request handling with timeout
- [ ] Return appropriate error response on timeout
- [ ] Log timeout events
- [ ] Use `config.request_timeout_secs` for timeout value
- [ ] Apply middleware to FastAPI app
- [ ] Test timeout behavior

**Expected Behavior**:
- Request takes 35 seconds with timeout=30 → 408 Request Timeout

**Tests Needed**:
- [ ] Test normal request completes within timeout
- [ ] Test timeout is enforced
- [ ] Test error response format on timeout

---

### Task 2.3: Refactor Auth to Middleware Pattern
**Priority**: 🟠 HIGH
**Effort**: 3-4 hours
**Files to Modify**: `middleware.py`, `app.py`

**Checklist**:
- [ ] Create `AuthMiddleware` class extending BaseHTTPMiddleware
- [ ] Extract bearer token parsing logic
- [ ] Move auth validation to middleware
- [ ] Skip auth for health check endpoints (live, ready)
- [ ] Add WWW-Authenticate header to 401 responses
- [ ] Add logging for auth failures
- [ ] Apply middleware to FastAPI app
- [ ] Remove per-endpoint auth dependencies
- [ ] Test middleware with various token scenarios

**Expected Benefit**:
- Before: 6 endpoints with `Depends(get_bearer_token)` checks
- After: Centralized middleware, cleaner endpoints

**Tests Needed**:
- [ ] Test valid token passes through
- [ ] Test invalid token rejected with 401
- [ ] Test missing token rejected with 401
- [ ] Test health endpoints skip auth
- [ ] Test WWW-Authenticate header presence

---

### Task 2.4: Improve Health Check Implementation
**Priority**: 🟠 HIGH
**Effort**: 2-3 hours
**Files to Create**: `src/app_state.py`
**Files to Modify**: `app.py`

**Checklist**:
- [ ] Create `AppState` class to track initialization state
- [ ] Add `is_model_loaded` flag
- [ ] Add async lock for model loading
- [ ] Implement `is_ready()` async method
- [ ] Update `/.well-known/live` to always return 204
- [ ] Update `/.well-known/ready` to check model state
- [ ] Return 503 if model not loaded in ready check
- [ ] Add root endpoint `/` with service metadata
- [ ] Add status field showing "ready" or "starting"
- [ ] List all endpoints in response
- [ ] Test ready state transitions

**Expected Behavior**:
- Live: Always 204 (liveness)
- Ready: 204 when model loaded, 503 when loading (readiness)
- Root: 200 with metadata

**Tests Needed**:
- [ ] Test live always returns 204
- [ ] Test ready returns 204 when model loaded
- [ ] Test ready returns 503 when model loading
- [ ] Test root endpoint returns metadata
- [ ] Test endpoint listing

---

## 🟡 PHASE 3: TESTING & QUALITY (Week 3-4)

These features ensure code quality and prevent regressions.

### Task 3.1: Create Mock Vectorizer for Testing
**Priority**: 🟡 MEDIUM
**Effort**: 2-3 hours
**Files to Create**: `tests/conftest.py`, `tests/fixtures.py`

**Checklist**:
- [ ] Create pytest fixtures directory structure
- [ ] Create `MockVectorizer` class
- [ ] Implement async vectorize method on mock
- [ ] Return predictable embeddings [1.0, 2.0, 3.0, ...]
- [ ] Create `mock_config` fixture
- [ ] Create `mock_vectorizer` fixture
- [ ] Create test client fixture
- [ ] Inject mock vectorizer into app for tests
- [ ] Test mock behavior

**Expected Structure**:
```
tests/
├── conftest.py
├── fixtures.py
├── test_api.py
├── test_auth.py
├── test_validation.py
└── test_health.py
```

---

### Task 3.2: Write Unit Tests for API Endpoints
**Priority**: 🟡 MEDIUM
**Effort**: 5-6 hours
**Files to Create**: `tests/test_api.py`

**Test Cases**:
- [ ] test_embeddings_float_format
- [ ] test_embeddings_base64_format
- [ ] test_embeddings_single_string
- [ ] test_embeddings_array_of_strings
- [ ] test_embeddings_invalid_model
- [ ] test_embeddings_invalid_encoding_format
- [ ] test_embeddings_with_dimensions
- [ ] test_embeddings_too_many_items
- [ ] test_embeddings_item_too_long
- [ ] test_embeddings_total_chars_exceeded
- [ ] test_embeddings_empty_input
- [ ] test_list_models
- [ ] test_list_models_with_alias
- [ ] test_meta_endpoint

**Expected Coverage**: >80% of route logic

---

### Task 3.3: Write Tests for Authentication
**Priority**: 🟡 MEDIUM
**Effort**: 2-3 hours
**Files to Create**: `tests/test_auth.py`

**Test Cases**:
- [ ] test_auth_valid_token
- [ ] test_auth_invalid_token
- [ ] test_auth_missing_token
- [ ] test_auth_malformed_header
- [ ] test_auth_disabled_allows_all
- [ ] test_health_check_skips_auth
- [ ] test_www_authenticate_header_on_401

---

### Task 3.4: Write Tests for Input Validation
**Priority**: 🟡 MEDIUM
**Effort**: 3-4 hours
**Files to Create**: `tests/test_validation.py`

**Test Cases**:
- [ ] test_max_input_items_validation
- [ ] test_max_input_chars_validation
- [ ] test_max_total_chars_validation
- [ ] test_dimensions_must_be_positive
- [ ] test_encoding_format_validation
- [ ] test_empty_input_rejected
- [ ] test_empty_model_rejected
- [ ] test_non_string_array_items_rejected
- [ ] test_valid_inputs_accepted

---

### Task 3.5: Write Tests for Health Checks
**Priority**: 🟡 MEDIUM
**Effort**: 2-3 hours
**Files to Create**: `tests/test_health.py`

**Test Cases**:
- [ ] test_live_always_204
- [ ] test_ready_returns_204_when_ready
- [ ] test_ready_returns_503_when_loading
- [ ] test_root_endpoint_metadata
- [ ] test_root_endpoint_lists_all_endpoints
- [ ] test_root_endpoint_shows_status

---

## 🟢 PHASE 4: ADVANCED FEATURES (Week 4-5)

These features optimize memory and add advanced capabilities.

### Task 4.1: Implement Lazy Model Loading
**Priority**: 🟢 MEDIUM-LOW
**Effort**: 3-4 hours
**Files to Modify**: `app_state.py`, `app.py`, `config.py`

**Checklist**:
- [ ] Add `lazy_load_model` flag to Config
- [ ] Update AppState to support deferred loading
- [ ] Load model on first embedding request if not loaded
- [ ] Handle concurrent load requests with lock
- [ ] Update ready check to wait if lazy loading
- [ ] Add logging for lazy load events
- [ ] Test lazy loading behavior

**Benefit**: Faster server startup for large models (128M+)

---

### Task 4.2: Implement Model Unloading
**Priority**: 🟢 MEDIUM-LOW
**Effort**: 4-5 hours
**Files to Modify**: `vectorizer.py`, `app_state.py`

**Checklist**:
- [ ] Add `model_unload_enabled` flag to Config
- [ ] Add `model_unload_idle_timeout` to Config
- [ ] Track last model access time
- [ ] Implement unload background task
- [ ] Unload model after idle timeout
- [ ] Automatically reload on next request
- [ ] Add logging for unload/reload events
- [ ] Test unload behavior

**Benefit**: Save 92% RAM when idle (useful for serverless)

---

### Task 4.3: Add Request Body Size Limiting
**Priority**: 🟢 MEDIUM-LOW
**Effort**: 2-3 hours
**Files to Create**: `middleware.py` (extend)
**Files to Modify**: `app.py`

**Checklist**:
- [ ] Create `MaxContentLengthMiddleware`
- [ ] Check Content-Length header
- [ ] Return 413 Payload Too Large if exceeded
- [ ] Use `config.request_body_limit_bytes`
- [ ] Apply middleware to app
- [ ] Test with oversized requests

---

### Task 4.4: Add Concurrency Limiting
**Priority**: 🟢 MEDIUM-LOW
**Effort**: 2-3 hours
**Files to Create**: `middleware.py` (extend)
**Files to Modify**: `app.py`

**Checklist**:
- [ ] Create semaphore for concurrency control
- [ ] Track active requests
- [ ] Reject requests exceeding limit with 503
- [ ] Use `config.concurrency_limit`
- [ ] Add logging for rejected requests
- [ ] Test with concurrent requests

---

## 🔵 PHASE 5: DEVOPS & DOCUMENTATION (Week 5-6)

These features improve deployment and documentation.

### Task 5.1: Enhance CI/CD Workflows
**Priority**: 🔵 LOW
**Effort**: 4-5 hours
**Files to Create/Modify**: `.github/workflows/`

**Checklist**:
- [ ] Add linting/format checks (flake8, black)
- [ ] Add mypy type checking
- [ ] Add pytest with coverage reporting
- [ ] Add Docker build to workflow
- [ ] Add multi-registry publishing (GHCR + Docker Hub)
- [ ] Add semantic versioning from git tags
- [ ] Add security scanning (Trivy)
- [ ] Create release notes automation

---

### Task 5.2: Optimize Docker Build
**Priority**: 🔵 LOW
**Effort**: 2-3 hours
**Files to Modify**: `Dockerfile`

**Checklist**:
- [ ] Create multi-stage build
- [ ] Use python:3.13-slim base
- [ ] Add non-root user for runtime
- [ ] Cache pip dependencies better
- [ ] Use .dockerignore to exclude unnecessary files
- [ ] Add healthcheck instruction
- [ ] Test Docker build and image size

---

### Task 5.3: Create Comprehensive Documentation
**Priority**: 🔵 LOW
**Effort**: 3-4 hours
**Files to Create**: `DEPLOY.md`, `ARCHITECTURE.md`

**Checklist**:
- [ ] Create DEPLOY.md with deployment guide
- [ ] Document all configuration parameters
- [ ] Add architecture overview
- [ ] Document API endpoints with examples
- [ ] Add troubleshooting section
- [ ] Document testing approach
- [ ] Update README with new features

---

### Task 5.4: Add Structured Logging
**Priority**: 🔵 LOW
**Effort**: 2-3 hours
**Files to Create**: `src/logging_config.py`
**Files to Modify**: `app.py`

**Checklist**:
- [ ] Configure structured JSON logging
- [ ] Add request ID tracking
- [ ] Log all errors with context
- [ ] Log startup/shutdown events
- [ ] Log model loading events
- [ ] Format logs for log aggregation
- [ ] Test log output

---

## Summary Table

| Phase | Tasks | Duration | Impact |
|-------|-------|----------|--------|
| 1: Foundations | 3 tasks | 1-2 weeks | Enables all others |
| 2: Reliability | 4 tasks | 1-2 weeks | Production-ready |
| 3: Testing | 5 tasks | 1-2 weeks | Quality assurance |
| 4: Advanced | 4 tasks | 1-2 weeks | Optimization |
| 5: DevOps | 4 tasks | 1-2 weeks | Operations |
| **TOTAL** | **20 tasks** | **~5-6 weeks** | **Full parity** |

---

## Success Criteria

### By End of Phase 1
- ✅ Config system in place
- ✅ Error responses standardized
- ✅ Input validation comprehensive
- ✅ Can boot server with all params

### By End of Phase 2
- ✅ Handles inference failures gracefully
- ✅ Enforces request timeouts
- ✅ Auth centralized in middleware
- ✅ Ready state properly tracked

### By End of Phase 3
- ✅ >80% test coverage
- ✅ All endpoints tested
- ✅ Auth tested
- ✅ Validation tested

### By End of Phase 4
- ✅ Lazy loading working
- ✅ Model unloading working
- ✅ Resource limits enforced
- ✅ Concurrency managed

### By End of Phase 5
- ✅ CI/CD pipeline running
- ✅ Docker optimized
- ✅ Full documentation
- ✅ Structured logging

---

## Quick Reference: File Changes Summary

### New Files to Create
- `src/config.py` - Structured configuration
- `src/errors.py` - Error response models
- `src/middleware.py` - Middleware implementations
- `src/app_state.py` - Application state management
- `tests/conftest.py` - Test fixtures
- `tests/test_api.py` - API tests
- `tests/test_auth.py` - Auth tests
- `tests/test_validation.py` - Validation tests
- `tests/test_health.py` - Health check tests
- `DEPLOY.md` - Deployment guide
- `ARCHITECTURE.md` - Architecture overview

### Files to Modify
- `app.py` - Integrate config, middleware, error handling
- `vectorizer.py` - Add validation, retry logic, async improvements
- `Dockerfile` - Multi-stage optimization
- `.github/workflows/` - Enhanced CI/CD
- `requirements.txt` - Add test dependencies
- `README.md` - Update with new features

### Files to Remove
- None (maintain backward compatibility)

