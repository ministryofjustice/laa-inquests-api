import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config.docs import docs_config
from app.config.logging import configure_logging
from app.contexts.request import clear_request_context, set_request_context
from app.contexts.user import clear_entra_user_context
from app.logging_utils import build_log_extra, duration_ms
from app.rate_limit import (
    RATE_LIMIT_EXEMPT_PATHS,
    create_rate_limiter,
)
from app.routers import applications, claims, monitoring, notifications, reports

logger = logging.getLogger(__name__)


def create_app():
    configure_logging()
    rate_limiter = create_rate_limiter()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            rate_limiter.close()

    app = FastAPI(**docs_config, lifespan=lifespan)
    app.state.rate_limiter = rate_limiter

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request.state.request_id = request.headers.get("x-request-id") or str(uuid4())
        request.state.correlation_id = (
            request.headers.get("x-correlation-id") or request.state.request_id
        )
        request.state.started_at = time.perf_counter()
        context_tokens = set_request_context(
            request.state.request_id,
            request.state.correlation_id,
        )

        try:
            if request.url.path in RATE_LIMIT_EXEMPT_PATHS:
                response = await call_next(request)
            else:
                client_ip = request.client.host if request.client else "unknown"
                allowed = await request.app.state.rate_limiter.try_acquire_async(
                    client_ip,
                    blocking=False,
                )
                if allowed:
                    response = await call_next(request)
                else:
                    response = JSONResponse(
                        status_code=429,
                        content={"detail": "Rate limit exceeded"},
                    )
                    logger.warning("Rate limit exceeded for client %s", client_ip)
            response.headers["x-request-id"] = request.state.request_id
            response.headers["x-correlation-id"] = request.state.correlation_id
            logger.info(
                "Request completed",
                extra=build_log_extra(
                    event="http_request_completed",
                    route=request.url.path,
                    method=request.method,
                    status_code=response.status_code,
                    duration_ms=duration_ms(request.state.started_at),
                ),
            )
            return response
        finally:
            clear_request_context(context_tokens)
            clear_entra_user_context()

    @app.exception_handler(Exception)
    async def internal_server_exception_handler(request: Request, exc: Exception):
        """Handle uncaught exceptions and return 500 response."""
        logger.exception(
            "Unhandled exception",
            extra=build_log_extra(
                event="http_request_failed",
                request_id=getattr(request.state, "request_id", None),
                correlation_id=getattr(request.state, "correlation_id", None),
                route=request.url.path,
                method=request.method,
                status_code=500,
                duration_ms=duration_ms(request.state.started_at)
                if hasattr(request.state, "started_at")
                else None,
                exception_type=type(exc).__name__,
            ),
        )
        headers = {
            "x-request-id": getattr(request.state, "request_id", ""),
            "x-correlation-id": getattr(request.state, "correlation_id", ""),
        }
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred"},
            headers=headers,
        )

    app.include_router(applications)
    app.include_router(claims)
    app.include_router(notifications)
    app.include_router(reports)
    app.include_router(monitoring)

    return app
