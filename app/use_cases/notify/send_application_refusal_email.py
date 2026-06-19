"""Use case for sending application refusal emails."""

from app.models.application.index import Application, ApplicationProceeding
from app.adapters.gov_notify import GovNotifyAdapter
from app.use_cases.notify.create_application_refusal_email_personalisation import (
    create_application_refusal_email_personalisation,
)
from app.config import Config


def send_application_refusal_email(
    notify_adapter: GovNotifyAdapter,
    application: Application,
    proceeding: ApplicationProceeding,
    provider_email: str,
) -> None:
    """Send refusal decision email for an application via Gov Notify."""
    personalisation = create_application_refusal_email_personalisation(
        application, proceeding
    )

    notify_adapter.send_email(
        email_address=provider_email,
        template_id=Config.GOV_NOTIFY_APPLICATION_REFUSE_TEMPLATE_ID,
        personalisation=personalisation,
    )
