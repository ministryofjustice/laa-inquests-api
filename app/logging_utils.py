import logging
import time
from typing import Any

from app.contexts.request import get_correlation_id, get_request_id


def build_log_extra(event: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event": event,
        "request_id": get_request_id(),
        "correlation_id": get_correlation_id(),
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
