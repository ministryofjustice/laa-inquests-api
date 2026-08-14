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
- Domain stays log-free.
- Routers, use cases, and adapters emit structured outcome events.
- Error boundary logs once for unhandled request failures.

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

Bad:

```python
logger.info(f"failed callback auth={authorization} payload={payload}")
```

