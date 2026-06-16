"""Use case for sending application confirmation emails."""

from app.models.application.index import Application
from app.adapters.govnotify import GovNotifyAdapter
from app.use_cases.build_email_personalisation import build_email_personalisation
from app.config import Config


def send_application_confirmation(
    application: Application, adapter: GovNotifyAdapter
) -> None:
    """
    Send a confirmation email for an application via GovNotify.

    This use case orchestrates the email sending process:
    1. Builds personalisation data from the application
    2. Sends email to the configured provider email address
    3. Propagates any exceptions to trigger transaction rollback

    Args:
        application: Application object with all relationships loaded
        adapter: GovNotify adapter implementation

    Raises:
        Exception: If email sending fails (triggers transaction rollback)
    """
    # Build personalisation dict from application data
    personalisation = build_email_personalisation(application)

    # Send email via adapter
    adapter.send_email(
        email_address=Config.GOVNOTIFY_PROVIDER_EMAIL,
        template_id=Config.GOV_NOTIFY_APPLICATION_SUBMIT_TEMPLATE_ID,
        personalisation=personalisation,
    )
