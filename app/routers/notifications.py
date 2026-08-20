"""Router for notification-related endpoints."""

import logging
import time
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request, Response, status

from app.config import Config
from app.logging_utils import build_log_extra, mask_recipient
from app.models.notifications import GovNotifyCallbackPayload

router = APIRouter(prefix="/notifications", tags=["Notifications"])

logger = logging.getLogger(__name__)


def verify_bearer_token(authorization: str) -> None:
    """
    Verify the bearer token sent by GovNotify.

    Args:
        authorization: The Authorization header value

    Raises:
        HTTPException: If the token is invalid or missing
    """
    expected_token = Config.GOV_NOTIFY_CALLBACK_BEARER_TOKEN

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
        )

    token = authorization.replace("Bearer ", "", 1)

    if token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
        )


@router.post("/callback", status_code=status.HTTP_200_OK)
async def gov_notify_callback(
    request: Request,
    payload: GovNotifyCallbackPayload,
    authorization: Annotated[str | None, Header()] = None,
) -> Response:
    """
    Receive and process GovNotify delivery status callbacks.

    This endpoint is called by GovNotify when notification delivery status changes.
    It validates the bearer token and logs the delivery status for monitoring.

    Args:
        payload: The GovNotify callback payload (validated by Pydantic)
        authorization: Bearer token sent by GovNotify in the Authorization header

    Returns:
        A simple acknowledgment response

    Raises:
        HTTPException: If bearer token is invalid or missing (401)
        HTTPException: If payload validation fails (422, raised by Pydantic)
    """
    verify_bearer_token(authorization)

    environment = "unknown"
    laa_reference = "unknown"

    if payload.reference:
        parts = payload.reference.split("-", 1)
        if len(parts) == 2:
            environment = parts[0]
            laa_reference = parts[1]

    started_at = getattr(request.state, "started_at", None)
    duration_ms = (
        int((time.perf_counter() - started_at) * 1000)
        if started_at is not None
        else None
    )

    logger.info(
        "GovNotify callback received",
        extra=build_log_extra(
            event="govnotify_callback_received",
            route=request.url.path,
            method=request.method,
            status_code=200,
            duration_ms=duration_ms,
            notification_id=str(payload.id),
            status=payload.status.value,
            notification_type=payload.notification_type.value,
            environment_from_reference=environment,
            laa_reference=laa_reference,
            recipient_masked=mask_recipient(payload.to),
        ),
    )

    return Response(status_code=200)
