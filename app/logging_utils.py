import logging
import time
from contextvars import ContextVar, Token
from typing import Any

_REQUEST_ID: ContextVar[str | None] = ContextVar("request_id", default=None)
_CORRELATION_ID: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def set_request_context(request_id: str, correlation_id: str) -> tuple[Token, Token]:
    return (_REQUEST_ID.set(request_id), _CORRELATION_ID.set(correlation_id))


def clear_request_context(tokens: tuple[Token, Token]) -> None:
    request_token, correlation_token = tokens
    _REQUEST_ID.reset(request_token)
    _CORRELATION_ID.reset(correlation_token)


def build_log_extra(event: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event": event,
        "request_id": _REQUEST_ID.get(),
        "correlation_id": _CORRELATION_ID.get(),
    }
    payload.update(extra)
    # Stash this in extra to make it accessible later
    return {"extra": payload}


def duration_ms(started_at: float) -> int:
    return int((time.perf_counter() - started_at) * 1000)


def mask_recipient(recipient: str) -> str:
    if not recipient:
        return "***"

    if "@" not in recipient:
        return "***"

    local, domain = recipient.split("@", 1)
    if not local:
        return f"***@{domain}"

    return f"{local[0]}***@{domain}"


def log_level_from_name(log_level_name: str | None) -> int:
    levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warn": logging.WARNING,
        "error": logging.ERROR,
        "fatal": logging.CRITICAL,
    }

    if log_level_name:
        configured_level = levels.get(log_level_name.strip().lower())
        if configured_level is not None:
            return configured_level
        return logging.INFO

    return logging.INFO
