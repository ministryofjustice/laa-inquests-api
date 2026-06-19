from enum import Enum


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
