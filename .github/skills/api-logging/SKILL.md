---
name: api-logging
description: Rules for adding and updating logs in laa-inquests-api. Use this when creating or changing API middleware, routers, use cases, adapters, or error handlers that emit logs.
---

# API Logging

Use `logging` with `extra={...}` and keep events structured and stable.

## Envelope keys and ownership

- Formatter provides: `timestamp`, `level`.
- Startup config provides defaults: `service`, `environment`.
- Middleware sets `request.state.request_id`, `request.state.correlation_id`, `request.state.started_at`.
- Call sites populate `event` and dynamic fields in `extra`.

Required shared keys for request and outbound events:
`timestamp`, `level`, `service`, `environment`, `event`, `message`, `request_id`, `correlation_id`, `route`, `method`, `status_code`, `duration_ms`.

## Layer behavior

- Middleware creates request context and response headers (`x-request-id`, `x-correlation-id`).
- Middleware logs request completion (`http_request_completed`) at `info` with `route`, `method`, `status_code`, and `duration_ms`.
- Domain stays log-free.
- Routers should avoid duplicate success logs for normal HTTP completion; keep router logs for failure paths and business-specific context only.
- Use cases and adapters emit structured outcome events.
- Error boundary logs once for unhandled request failures.

## Router policy

- Do not add router-level `info` logs that only restate HTTP success status for endpoints.
- Prefer middleware request-completion logs for success observability.
- Keep router logs where they add diagnostic value not present in middleware, such as:
  - mapped exception outcomes (for example 404/422/500 from domain/use-case errors)
  - operation-specific identifiers needed to diagnose failures
  - business milestones that are not equivalent to simple request completion

## Levels

Allowed: `debug`, `info`, `warn`, `error`, `fatal`.

Environment defaults:
- `local`: `debug`
- `dev`: `info`
- `staging`: `info`
- `prod`: `warn`

If `LOG_LEVEL` is invalid, fallback to `info`.

## Never log

- PII
- Tokens, cookies, authorization headers
- Raw request or response payloads
- File names, they are likely to have sensitive data in the names

## Template

```python
logger.info(
    "GovNotify callback received",
    extra={
        "service": settings.service_name,
        "environment": settings.environment,
        "event": "govnotify_callback_received",
        "request_id": request.state.request_id,
        "correlation_id": request.state.correlation_id,
        "route": request.url.path,
        "method": request.method,
        "status_code": 200,
        "duration_ms": duration_ms,
    },
)
```

Good:

```python
logger.error(
    "GovNotify send failed",
    extra={"event": "govnotify_send_failed", "status_code": 502},
)
```

Good (router):

```python
logger.warning(
    "Claim evidence upload failed virus check",
    extra=build_log_extra(
        event="claim_evidence_uploaded_failed",
        route=request.url.path,
        method=request.method,
        status_code=422,
    ),
)
```

Bad:

```python
logger.info(f"failed callback auth={authorization} payload={payload}")
```

