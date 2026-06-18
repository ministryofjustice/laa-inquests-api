"""Use case for sending application refusal emails."""

from app.models.application.index import Application, ApplicationProceeding
from app.adapters.gov_notify import GovNotifyAdapter
from app.use_cases.notify.populate_application_refusal_template import (
    populate_application_refusal_template,
)
from app.config import Config


def send_application_refusal(
    notify_adapter: GovNotifyAdapter,
    application: Application,
    proceeding: ApplicationProceeding,
    provider_email: str,
) -> None:
    """Send refusal decision email for an application via Gov Notify."""
    personalisation = populate_application_refusal_template(application, proceeding)

    notify_adapter.send_email(
        email_address=provider_email,
        template_id=Config.GOV_NOTIFY_APPLICATION_REFUSE_TEMPLATE_ID,
        personalisation=personalisation,
    )
