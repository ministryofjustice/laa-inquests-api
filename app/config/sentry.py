import logging
from typing import Any
from urllib.parse import urlsplit

from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration, ignore_logger

from app.config import Config

# The SDK's default only treats 500-599 as failed requests, so an explicit
# `HTTPException(422, ...)` (e.g. virus detected on upload) is never sent.
# FastAPI's own request validation errors have no `status_code` attribute, so
# widening this does not also start reporting routine payload validation 422s.
_FAILED_REQUEST_STATUS_CODES = {*range(400, 600)}

# Their messages contain client IPs, full request URLs and query strings.
for noisy_logger in ("uvicorn.access", "httpx"):
    ignore_logger(noisy_logger)

# Exceptions from these libraries embed SQL parameters, DB error details
# (e.g. "Key (national_insurance_number)=(...)"), the rejected input value, or
# request URLs (httpx), which include SDS file keys and pre-signed file URLs.
_SENSITIVE_EXCEPTION_MODULES = ("sqlalchemy", "psycopg2", "pydantic", "httpx")

# File-handling errors; their messages may contain the uploaded file name or SDS file
# key. They can carry a `safe_message` (see SentryRedactableError) with that removed;
# `_is_sensitive_exception` still exists as a fallback, redacting the whole message
# when no `safe_message` was provided.
_FILE_EXCEPTION_MODULE = "app.use_cases.exceptions"
_FILE_EXCEPTION_PREFIXES = (
    "CoronersLetter",
    "InvalidCoronersLetter",
    "SDSLetter",
    "ClaimEvidence",
    "InvalidClaimEvidence",
    "SDSClaimEvidence",
)


def _is_sensitive_exception(exception: dict[str, Any]) -> bool:
    module = exception.get("module") or ""
    if module.startswith(_SENSITIVE_EXCEPTION_MODULES):
        return True
    return module == _FILE_EXCEPTION_MODULE and (
        exception.get("type") or ""
    ).startswith(_FILE_EXCEPTION_PREFIXES)


# ERROR logs send their `extra` (built by build_log_extra) with the event. Only
# non-identifying keys are kept; case/claim references and record IDs are not
# personally identifying, so they are allowed through.
_SAFE_LOG_EXTRA_KEYS = frozenset(
    {
        "event",
        "request_id",
        "correlation_id",
        "status_code",
        "method",
        "duration_ms",
        "error_type",
        "exception_type",
        "route",
        "laa_reference",
        "claim_reference",
        "firm_code",
        "application_id",
        "claim_evidence_id",
        "coroners_letter_id",
        "public_body_id",
        "provider_id",
    }
)


def _scrub_extra(extra: dict[str, Any]) -> dict[str, Any]:
    log_extra = extra.get("extra")
    if not isinstance(log_extra, dict):
        return {}
    return {k: v for k, v in log_extra.items() if k in _SAFE_LOG_EXTRA_KEYS}


def _host_only(url: str) -> str:
    """Drop credentials, path, query and fragment; outbound URLs carry file names and signatures."""
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc.rpartition('@')[2]}"


def _scrub_http_data(data: dict[str, Any]) -> None:
    if "url" in data:
        data["url"] = _host_only(data["url"])
    data.pop("http.query", None)
    data.pop("http.fragment", None)


def scrub_breadcrumb(
    breadcrumb: dict[str, Any], hint: dict[str, Any]
) -> dict[str, Any]:
    _scrub_http_data(breadcrumb.get("data") or {})
    return breadcrumb


def scrub_transaction(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
    for span in event.get("spans", []):
        data = span.get("data") or {}
        if span.get("op") == "http.client" and "url" in data:
            _scrub_http_data(data)
            span["description"] = f"{data.get('http.method', 'GET')} {data['url']}"
    return event


def _exception_chain(value: BaseException | None) -> list[BaseException]:
    chain: list[BaseException] = []
    while value is not None:
        chain.append(value)
        value = value.__cause__ or (
            None if value.__suppress_context__ else value.__context__
        )
    chain.reverse()
    return chain


def scrub_event(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
    if "extra" in event:
        event["extra"] = _scrub_extra(event["extra"])
    exc_info = hint.get("exc_info")
    real_chain = _exception_chain(exc_info[1]) if exc_info else []
    for index, exception in enumerate(event.get("exception", {}).get("values", [])):
        if not _is_sensitive_exception(exception):
            continue
        source = real_chain[index] if index < len(real_chain) else None
        exception["value"] = getattr(source, "safe_message", None) or "[Filtered]"
    return event


sentry_config = {
    "dsn": Config.SENTRY_DSN,
    # Logs are already written to stdout as JSON; do not duplicate them in Sentry.
    "enable_logs": False,
    # No log breadcrumbs (they carry the log's extra fields); ERROR logs still raise events.
    "integrations": [
        LoggingIntegration(level=None, event_level=logging.ERROR),
        FastApiIntegration(failed_request_status_codes=_FAILED_REQUEST_STATUS_CODES),
    ],
    "before_send": scrub_event,
    "before_send_transaction": scrub_transaction,
    "before_breadcrumb": scrub_breadcrumb,
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for tracing.
    "traces_sample_rate": 0.02,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    "profile_session_sample_rate": 0.2,
    "profile_lifecycle": "trace",
    # This can either be dev, staging, or production.
    # It is set from the ENVIRONMENT env var, passed in by deploy.sh.
    "environment": Config.ENVIRONMENT,
    "data_collection": {
        "user_info": False,
        "cookies": {"mode": "off"},
        "http_headers": {"request": {"mode": "off"}},
        "http_bodies": [],
        "url_query_params": {"mode": "off"},
        "gen_ai": {"inputs": False, "outputs": False},
        "database_query_data": False,
        "graphql": {"document": False, "variables": False},
        "queues": False,
        # Locals include the raw ASGI scope (Authorization header, client IP, query string).
        "stack_frame_variables": False,
        "frame_context_lines": 0,
    },
}
