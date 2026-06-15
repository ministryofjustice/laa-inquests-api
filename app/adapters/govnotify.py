"""Adapter for GovNotify email service."""

from typing import Protocol
from notifications_python_client.notifications import NotificationsAPIClient
from app.config import Config
from app.models.notifications.personalisation import EmailPersonalisation


class GovNotifyAdapter(Protocol):
    """Protocol defining the interface for GovNotify email adapter."""

    def send_email(
        self,
        email_address: str,
        template_id: str,
        personalisation: EmailPersonalisation,
    ) -> None:
        """
        Send an email via GovNotify.

        Args:
            email_address: Recipient email address
            template_id: GovNotify template ID
            personalisation: Dict of template variables

        Raises:
            Exception: If email sending fails
        """
        ...


class GovNotifyClient:
    """
    Concrete implementation of GovNotify adapter using notifications-python-client.

    This adapter wraps the official GOV.UK Notify Python client and provides
    a simplified interface for sending emails with template personalisation.
    """

    def __init__(self):
        """Initialize the GovNotify client with API key from config."""
        self.client = NotificationsAPIClient(Config.GOVNOTIFY_API_KEY)

    def send_email(
        self,
        email_address: str,
        template_id: str,
        personalisation: EmailPersonalisation,
    ) -> None:
        """
        Send an email via GovNotify.

        Args:
            email_address: Recipient email address
            template_id: GovNotify template ID
            personalisation: Dict of template variables

        Raises:
            Exception: If GovNotify API returns an error
        """
        self.client.send_email_notification(
            email_address=email_address,
            template_id=template_id,
            personalisation=personalisation.model_dump(),  # Convert Pydantic model to dict
        )
