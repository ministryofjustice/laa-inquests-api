# Logging Implementation Plan - laa-inquests-api

Last updated: 2026-08-14

## Goal

Implement a consistent, structured, safe logging model in `laa-inquests-api` that matches the cross-repo strategy and can be executed by an implementation agent without additional design decisions.

## Non-negotiable decisions

- Output structured JSON logs in non-local environments.
- Use shared envelope keys: `timestamp`, `level`, `service`, `environment`, `event`, `message`, `request_id`, `correlation_id`, `route`, `method`, `status_code`, `duration_ms`.
- Configure level via `LOG_LEVEL` env var (Helm-managed in deployed environments).
- Keep `app/domain/*` log-free.
- Never log PII, tokens, cookies, auth headers, or full request/response payloads.

## Log level policy

- Allowed values: `debug`, `info`, `warn`, `error`, `fatal`.
- Default by environment:
  - Local: `debug`
  - Dev: `info`
  - Staging: `info`
  - Prod: `warn`
- Use levels as follows:
  - `debug`: temporary local diagnostics.
  - `info`: normal request lifecycle + business milestones.
  - `warn`: recoverable failure/retry/degraded dependency.
  - `error`: operation failed and needs investigation.
  - `fatal`: unrecoverable process condition.

## Environment configuration contract

- Read `LOG_LEVEL` once at startup.
- Validate and fallback to `info` if missing/invalid.
- For Kubernetes deployments, set via Helm values and map into deployment env.

Example config pattern:

```python
# laa-inquests-api/app/config/logging.py
import logging
import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
```

## Shared envelope key ownership (where keys come from and where they go)

All keys end up on the final emitted JSON log event. In Python, application code should place dynamic fields in `extra={...}` and let the formatter/output layer render the final envelope.

| Envelope key | Source of truth in API | Set by | Written into |
|---|---|---|---|
| `timestamp` | current time at emit | logger/formatter | final JSON log object |
| `level` | logger call level (`info`, `warn`, `error`, etc.) | logger method | final JSON log object |
| `service` | `SERVICE_NAME` env/config | startup config | final JSON log object |
| `environment` | `NODE_ENV`/app env config | startup config | final JSON log object |
| `event` | stable event name constant in calling layer | router/use case/adapter/error boundary | `extra` -> final JSON log object |
| `message` | human-readable summary string | calling code | logger message -> final JSON log object |
| `request_id` | `x-request-id` header or generated UUID | request-context middleware | `request.state` then `extra` |
| `correlation_id` | `x-correlation-id` header or `request_id` fallback | request-context middleware | `request.state` then `extra` |
| `route` | route template/path | router/middleware | `extra` -> final JSON log object |
| `method` | request method | router/middleware | `extra` -> final JSON log object |
| `status_code` | response/dependency status | router/adapter/error boundary | `extra` -> final JSON log object |
| `duration_ms` | elapsed timer using `started_at` or local timer | middleware/adapter | `extra` -> final JSON log object |

## Envelope placement rule for examples

- `timestamp` and `level` come from the logger emission time and method (`logger.info`, `logger.error`, `logger.exception`).
- `service` and `environment` should be included in `extra` in emitted examples for clarity and consistency.
- `request_id`, `correlation_id`, and timers are created in middleware and then propagated into emitted logs.
- `route`, `method`, `status_code`, and `duration_ms` should be present on request/adapter/error events.

## Layer-by-layer approach with canonical examples

Use these examples as the target implementation shape.

### 1) Entrypoint / App

Source anchor: `laa-inquests-api/app/main.py`

```python
# Initialize request context once for all routes.
@app.middleware("http")
async def request_context(request, call_next):
    request.state.request_id = request.headers.get("x-request-id") or str(uuid4())
    request.state.correlation_id = (
        request.headers.get("x-correlation-id") or request.state.request_id
    )
    request.state.started_at = time.perf_counter()
    response = await call_next(request)
    duration_ms = int((time.perf_counter() - request.state.started_at) * 1000)

    logger.debug(
        "Request completed",
        extra={
            "service": settings.service_name,
            "environment": settings.environment,
            "event": "http_request_completed",
            "request_id": request.state.request_id,
            "correlation_id": request.state.correlation_id,
            "route": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )

    response.headers["x-request-id"] = request.state.request_id
    response.headers["x-correlation-id"] = request.state.correlation_id
    return response
```

Events: `request_context_initialized`, `http_request_completed`.

### 2) Router

Source anchor: `laa-inquests-api/app/routers/notifications.py`

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
        "duration_ms": int((time.perf_counter() - request.state.started_at) * 1000),
        "notification_id": str(payload.id),
        "status": payload.status.value,
        "recipient_masked": mask_recipient(payload.to),
    },
)
```

Events: `govnotify_callback_received`, `route_validation_failed`.

### 3) Use Cases

Source anchor: `laa-inquests-api/app/use_cases/create_claim.py`

```python
logger.info(
    "Claim submitted",
    extra={
        "service": settings.service_name,
        "environment": settings.environment,
        "event": "claim_submitted",
        "request_id": request_context.request_id,
        "correlation_id": request_context.correlation_id,
        "laa_reference": command.laa_reference,
        "claim_id": claim.claim_id,
        "decision_status": claim.status_id.value,
    },
)
```

Events: `claim_submitted`, `notification_requested`, `claim_validation_failed`.

### 4) Domain

Source anchor: `laa-inquests-api/app/domain/claim.py`

```python
# Domain stays log-free; expose business outcome.
rejection = validated_claim.should_auto_reject(application, existing_summaries)
if rejection.is_rejected:
    return ClaimRejection(reasons=rejection.reasons)
```

Event policy: no direct domain logs.

### 5) Outbound Adapters

Source anchor: `laa-inquests-api/app/adapters/gov_notify.py`

```python
started = time.perf_counter()
try:
    self.client.send_email_notification(...)
    logger.info(
        "GovNotify send success",
        extra={
            "service": settings.service_name,
            "environment": settings.environment,
            "event": "govnotify_send",
            "request_id": request_context.request_id,
            "correlation_id": request_context.correlation_id,
            "route": "govnotify:send_email_notification",
            "method": "POST",
            "status_code": 200,
            "duration_ms": int((time.perf_counter() - started) * 1000),
        },
    )
except Exception as exc:
    logger.error(
        "GovNotify send failed",
        extra={
            "service": settings.service_name,
            "environment": settings.environment,
            "event": "govnotify_send_failed",
            "request_id": request_context.request_id,
            "correlation_id": request_context.correlation_id,
            "route": "govnotify:send_email_notification",
            "method": "POST",
            "status_code": 502,
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "exception_type": type(exc).__name__,
        },
    )
    raise
```

Events: `outbound_api_call`, `govnotify_send`, `outbound_retry_scheduled`, `outbound_call_failed`.

### 6) Error Boundary

Source anchor: `laa-inquests-api/app/main.py`

```python
@app.exception_handler(Exception)
async def internal_server_exception_handler(request, exc):
    logger.exception(
        "Unhandled exception",
        extra={
            "service": settings.service_name,
            "environment": settings.environment,
            "event": "http_request_failed",
            "request_id": getattr(request.state, "request_id", None),
            "correlation_id": getattr(request.state, "correlation_id", None),
            "route": request.url.path,
            "method": request.method,
            "status_code": 500,
            "duration_ms": int((time.perf_counter() - request.state.started_at) * 1000)
            if hasattr(request.state, "started_at")
            else None,
            "exception_type": type(exc).__name__,
        },
    )
    return JSONResponse(
        status_code=500, content={"detail": "An internal server error occurred"}
    )
```

Events: `http_request_failed`, `unhandled_exception`.

## Event list policy (not exhaustive)

- Event examples in this plan are baseline requirements, not a closed list.
- Keep baseline events stable for dashboards/alerts, and add new events for new journeys and failure modes.
- Use `snake_case` names and keep them outcome-focused (`what happened`), not code-structure-focused (`where in code`).
- Do not rename existing event names without a migration note and downstream consumer review.

## Add a logging skill for future changes

Create a short repo-specific logging skill document (for example in your skills location) so future agents follow the same rules by default.

Front matter to include at the top of the skill file:

```yaml
---
name: api-logging
description: Rules for adding and updating logs in laa-inquests-api. Use this when creating or changing API middleware, routers, use cases, adapters, or error handlers that emit logs.
---
```

Skill content should briefly cover:

1. Required envelope keys and ownership in API (`request.state` vs `extra` vs formatter).
2. Required layer behavior:
   - middleware creates request context
   - domain remains log-free
   - routers/use cases/adapters emit structured events
   - error boundary logs once per failure
3. Approved levels (`debug`, `info`, `warn`, `error`, `fatal`) and environment defaults.
4. Banned log content (PII, tokens, cookies, auth headers, raw payloads).
5. A minimal code template for new log statements using `logger.<level>(..., extra={...})`.

Definition of done for the skill:

- It is short enough to be read quickly (around one page).
- It includes one good and one bad logging example.
- It points to this plan as source of truth for API logging strategy.

## Delivery sequence

1. Add startup logging config with `LOG_LEVEL` validation/fallback.
2. Add/standardize request context middleware and response headers.
3. Refactor router logs to structured event payloads and masking.
4. Refactor use case logs to stable event names.
5. Refactor outbound adapter logs for status + latency + failure metadata.
6. Ensure one boundary error event per failed request.
7. Add tests for level gating and sensitive-field omission.

## Done criteria

- `LOG_LEVEL` gates emitted logs correctly.
- Request logs always include `request_id` and `correlation_id`.
- Domain layer remains log-free.
- No sensitive fields are emitted.
- Core journeys produce stable, queryable event names.





