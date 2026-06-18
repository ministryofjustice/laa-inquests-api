"""Pydantic models for GovNotify callback payloads."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class NotificationStatus(str, Enum):
    """GovNotify notification delivery statuses."""

    CREATED = "created"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    PERMANENT_FAILURE = "permanent-failure"
    TEMPORARY_FAILURE = "temporary-failure"
    TECHNICAL_FAILURE = "technical-failure"


class NotificationType(str, Enum):
    """GovNotify notification types."""

    EMAIL = "email"
    SMS = "sms"
    LETTER = "letter"


class GovNotifyCallbackPayload(BaseModel):
    """
    Pydantic model for GovNotify delivery receipt callback payload.

    GovNotify sends this payload to the configured callback URL when
    notification delivery status changes.

    Attributes:
        id: Unique notification ID from GovNotify
        reference: Custom reference set when sending (e.g., "uat-APP-123456")
        to: Recipient email address or phone number
        status: Current delivery status
        created_at: ISO timestamp when notification was created
        completed_at: ISO timestamp when delivery completed (if applicable)
        sent_at: ISO timestamp when notification was sent (if applicable)
        notification_type: Type of notification (email, sms, letter)
    """

    id: str = Field(description="GovNotify notification UUID")
    reference: Optional[str] = Field(
        None, description="Custom reference (e.g., environment-LAA_REF)"
    )
    to: str = Field(description="Recipient email or phone number")
    status: NotificationStatus = Field(description="Delivery status")
    created_at: str = Field(description="ISO timestamp of creation")
    completed_at: Optional[str] = Field(None, description="ISO timestamp of completion")
    sent_at: Optional[str] = Field(None, description="ISO timestamp when sent")
    notification_type: NotificationType = Field(description="Notification type")
