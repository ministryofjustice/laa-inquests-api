"""Router for notification-related endpoints."""

import logging
from typing import Annotated
from fastapi import APIRouter, Header, HTTPException, Response, status
from app.models.notifications import GovNotifyCallbackPayload
from app.config import Config

router = APIRouter(prefix="/notifications", tags=["notifications"])

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

    # Extract environment and LAA reference from reference field if present
    environment = "unknown"
    laa_reference = "unknown"

    if payload.reference:
        parts = payload.reference.split("-", 1)
        if len(parts) == 2:
            environment = parts[0]
            laa_reference = parts[1]

    # Log the delivery status
    logger.info(
        f"GovNotify callback received: "
        f"notification_id={payload.id}, "
        f"status={payload.status.value}, "
        f"type={payload.notification_type.value}, "
        f"environment={environment}, "
        f"laa_reference={laa_reference}, "
        f"to={payload.to}, "
        f"created_at={payload.created_at}, "
        f"sent_at={payload.sent_at}, "
        f"completed_at={payload.completed_at}"
    )

    return Response(status_code=200)
