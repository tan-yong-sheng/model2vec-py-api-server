import asyncio
from starlette.requests import Request
from starlette.responses import Response

from src.config import Config, set_config
from src.middleware import (
    AuthMiddleware,
    ConcurrencyLimitMiddleware,
    MaxContentLengthMiddleware,
    TimeoutMiddleware,
)


def _make_request(path: str = "/", headers=None, method: str = "GET") -> Request:
    if headers is None:
        headers = []
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": headers,
        "query_string": b"",
    }
    return Request(scope)


def test_auth_middleware_rejects_missing_token():
    config = Config(allowed_tokens=["token1"])
    set_config(config)

    async def call_next(request):
        return Response("ok")

    middleware = AuthMiddleware(lambda scope, receive, send: None)
    req = _make_request(path="/meta")

    res = asyncio.run(middleware.dispatch(req, call_next))
    assert res.status_code == 401
    payload = res.body.decode("utf-8")
    assert "authentication_error" in payload


def test_auth_middleware_allows_valid_token():
    config = Config(allowed_tokens=["token1"])
    set_config(config)

    async def call_next(request):
        return Response("ok")

    middleware = AuthMiddleware(lambda scope, receive, send: None)
    req = _make_request(
        path="/meta",
        headers=[(b"authorization", b"Bearer token1")],
    )

    res = asyncio.run(middleware.dispatch(req, call_next))
    assert res.status_code == 200


def test_auth_middleware_skips_health_endpoints():
    config = Config(allowed_tokens=["token1"])
    set_config(config)

    async def call_next(request):
        return Response("ok")

    middleware = AuthMiddleware(lambda scope, receive, send: None)
    req = _make_request(path="/.well-known/live")

    res = asyncio.run(middleware.dispatch(req, call_next))
    assert res.status_code == 200


def test_timeout_middleware():
    config = Config(request_timeout_secs=0.01)
    set_config(config)

    async def call_next(request):
        await asyncio.sleep(0.05)
        return Response("ok")

    middleware = TimeoutMiddleware(lambda scope, receive, send: None)
    req = _make_request(path="/slow")

    res = asyncio.run(middleware.dispatch(req, call_next))
    assert res.status_code == 504
    payload = res.body.decode("utf-8")
    assert "Request timed out" in payload


def test_max_content_length_rejects_large_body():
    config = Config(request_body_limit_bytes=5)
    set_config(config)

    async def call_next(request):
        return Response("ok")

    middleware = MaxContentLengthMiddleware(
        lambda scope, receive, send: None, max_content_length=5
    )
    req = _make_request(
        path="/v1/embeddings",
        method="POST",
        headers=[(b"content-length", b"10")],
    )

    res = asyncio.run(middleware.dispatch(req, call_next))
    assert res.status_code == 413
    payload = res.body.decode("utf-8")
    assert "Request body too large" in payload


def test_concurrency_limit_rejects_when_saturated():
    config = Config(concurrency_limit=1)
    set_config(config)

    async def call_next(request):
        return Response("ok")

    middleware = ConcurrencyLimitMiddleware(
        lambda scope, receive, send: None, concurrency_limit=1
    )

    async def run():
        await middleware._semaphore.acquire()
        req = _make_request(path="/meta")
        res = await middleware.dispatch(req, call_next)
        middleware._semaphore.release()
        return res

    res = asyncio.run(run())
    assert res.status_code == 429
    payload = res.body.decode("utf-8")
    assert "rate_limit_error" in payload
