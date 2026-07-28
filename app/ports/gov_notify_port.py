"""Abstraction for Gov Notify integration (email notifications)."""

from abc import ABC, abstractmethod

from app.models.application.index import Application, ApplicationProceeding
from app.models.claim.index import Claim


class GovNotifyPort(ABC):
    """Port for sending notifications via Gov Notify.

    Implementers handle:
    - Building personalisation payloads (template variables)
    - Calling the Gov Notify API
    - Handling errors and retries
    """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def send_application_granted_decision_email(
        self,
        application: Application,
        proceeding: ApplicationProceeding,
        recipient_email: str,
        certificate_pdf: bytes,
    ) -> None:
        """Send application grant notification to recipient.

        Args:
            application: The application being granted
            proceeding: The proceeding with grant details (certificate issue date)
            recipient_email: Email address of the recipient
            certificate_pdf: PDF bytes to be attached to the notification

        Raises:
            Exception: If the notification fails to send
        """
        ...

    @abstractmethod
    def send_claim_submit_confirmation_email(
        self,
        claim: Claim,
        application: Application,
        recipient_email: str,
    ) -> None:
        """Send claim submission notification to recipient.

        Args:
            claim: The claim being submitted
            application: The associated application for the claim
            recipient_email: Email address of the recipient

        Raises:
            Exception: If the notification fails to send
        """
        ...

    @abstractmethod
    def send_precompiled_letter(self, reference: str, pdf: bytes) -> None: ...
