"""Abstraction for Gov Notify integration (email notifications)."""

from typing import Protocol

from app.models.application.index import Application, ApplicationProceeding


class GovNotifyPort(Protocol):
    """Port for sending notifications via Gov Notify.

    Implementers handle:
    - Building personalisation payloads (template variables)
    - Calling the Gov Notify API
    - Handling errors and retries
    """

    def send_application_refused_decision_email(
        self,
        application: Application,
        proceeding: ApplicationProceeding,
        recipient_email: str,
    ) -> None:
        """Send application refusal notification to recipient.

        Args:
            application: The application being refused
            proceeding: The proceeding with refusal details (reason, justification)
            recipient_email: Email address of the recipient

        Raises:
            Exception: If the notification fails to send
        """
        ...

    def send_application_submit_confirmation_email(
        self, application: Application, recipient_email: str
    ) -> None:
        """Send application confirmation notification to recipient.

        Args:
            application: The application being confirmed
            recipient_email: Email address of the recipient

        Raises:
            Exception: If the notification fails to send
        """
        ...
