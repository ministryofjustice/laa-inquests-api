"""Gov Notify adapter for application emails."""

from notifications_python_client.notifications import NotificationsAPIClient

from app.config import Config
from app.models.application.index import Application, ApplicationProceeding

from app.ports.gov_notify_port import GovNotifyPort
from app.use_cases.notify.create_application_refusal_email_personalisation import (
    create_application_refusal_email_personalisation,
)
from app.use_cases.notify.create_application_submission_email_personalisation import (
    create_application_submission_email_personalisation,
)
from app.use_cases.notify.create_application_grant_email_personalisation import (
    create_application_grant_email_personalisation,
)


class GovNotifyAdapter(GovNotifyPort):
    """Gov Notify adapter for application email notifications."""

    def __init__(self) -> None:
        self.client = NotificationsAPIClient(Config.GOV_NOTIFY_API_KEY)

    def send_application_refused_decision_email(
        self,
        application: Application,
        proceeding: ApplicationProceeding,
        recipient_email: str,
    ) -> None:
        personalisation = create_application_refusal_email_personalisation(
            application, proceeding
        )
        self.client.send_email_notification(
            email_address=recipient_email,
            template_id=Config.GOV_NOTIFY_APPLICATION_REFUSE_TEMPLATE_ID,
            personalisation=personalisation.model_dump(),
        )

    def send_application_submit_confirmation_email(
        self, application: Application, recipient_email: str
    ) -> None:
        personalisation = create_application_submission_email_personalisation(
            application
        )
        self.client.send_email_notification(
            email_address=recipient_email,
            template_id=Config.GOV_NOTIFY_APPLICATION_SUBMIT_TEMPLATE_ID,
            personalisation=personalisation.model_dump(),
        )

    def send_application_granted_decision_email(
        self,
        application: Application,
        proceeding: ApplicationProceeding,
        recipient_email: str,
    ) -> None:
        personalisation = create_application_grant_email_personalisation(
            application, proceeding
        )
        self.client.send_email_notification(
            email_address=recipient_email,
            template_id=Config.GOV_NOTIFY_APPLICATION_GRANT_TEMPLATE_ID,
            personalisation=personalisation.model_dump(),
        )
