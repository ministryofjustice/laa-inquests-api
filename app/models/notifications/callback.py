"""Pydantic models for GovNotify callback payloads."""

from pydantic import BaseModel, Field

from app.models.notifications.enums import NotificationStatus, NotificationType
from app.models.validated_types import SingleLineText

# Notify sends a UUID for the id, an ISO timestamp, and an email or phone number. The
# strings are only logged, so these are generous bounds rather than exact formats.
MAX_ID_LENGTH = 64
MAX_REFERENCE_LENGTH = 100
MAX_RECIPIENT_LENGTH = 254
MAX_TIMESTAMP_LENGTH = 40


class GovNotifyCallbackPayload(BaseModel):
    """
    Pydantic model for GovNotify delivery receipt callback payload.

    GovNotify sends this payload to the configured callback URL when
    notification delivery status changes.

    Attributes:
        id: Unique notification ID from GovNotify
        reference: Custom reference set when sending (e.g., "dev-APP-123456")
        to: Recipient email address or phone number
        status: Current delivery status
        created_at: ISO timestamp when notification was created
        completed_at: ISO timestamp when delivery completed (if applicable)
        sent_at: ISO timestamp when notification was sent (if applicable)
        notification_type: Type of notification (email, sms, letter)
    """

    id: SingleLineText = Field(
        max_length=MAX_ID_LENGTH, description="GovNotify notification UUID"
    )
    reference: SingleLineText | None = Field(
        None,
        max_length=MAX_REFERENCE_LENGTH,
        description="Custom reference (e.g., environment-LAA_REF)",
    )
    to: SingleLineText = Field(
        max_length=MAX_RECIPIENT_LENGTH, description="Recipient email or phone number"
    )
    status: NotificationStatus = Field(description="Delivery status")
    created_at: SingleLineText = Field(
        max_length=MAX_TIMESTAMP_LENGTH, description="ISO timestamp of creation"
    )
    completed_at: SingleLineText | None = Field(
        None,
        max_length=MAX_TIMESTAMP_LENGTH,
        description="ISO timestamp of completion",
    )
    sent_at: SingleLineText | None = Field(
        None,
        max_length=MAX_TIMESTAMP_LENGTH,
        description="ISO timestamp when sent",
    )
    notification_type: NotificationType = Field(description="Notification type")
