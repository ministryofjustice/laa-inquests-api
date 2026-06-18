"""Use case for sending application confirmation emails."""

from app.models.application.index import Application
from app.adapters.gov_notify import GovNotifyAdapter
from app.use_cases.populate_application_submission_template import (
    populate_application_submission_template,
)
from app.config import Config


def send_application_confirmation(
    notifyAdapter: GovNotifyAdapter, application: Application, provider_email=str
) -> None:
    """
    Send a confirmation email for an application via GovNotify.

    This use case orchestrates the email sending process:
    1. Builds personalisation data from the application
    2. Sends email to the specified provider email address

    Args:
        adapter: GovNotify adapter implementation
        application: Application object with all relationships loaded
        provider_email: Email address of the provider we want to send the email to

    """
    personalisation = populate_application_submission_template(application)

    notifyAdapter.send_email(
        email_address=provider_email,
        template_id=Config.GOV_NOTIFY_APPLICATION_SUBMIT_TEMPLATE_ID,
        personalisation=personalisation,
    )
